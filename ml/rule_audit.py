#!/usr/bin/env python3
"""Measure every scoring rule ALONE, on a frozen corpus, and report which are dead.

The gap this closes: FLAC Detective's verdict is a sum of twelve rules, and until
now only the *sum* was ever measured. A rule that fires at random adds its points
to genuine and fake alike — invisible in the total, but it moves innocent files
toward the WARNING threshold. Rule 9's pre-echo test was exactly that (AUC 0.51),
and it shipped for a year because nothing measured it on its own.

What this computes, per rule:

  auc        Mann-Whitney AUC of the rule's own point contribution, fake vs genuine.
             0.5 = the rule is a coin flip. This is the headline number.
  fire_gen   fraction of GENUINE files where the rule contributed a non-zero score
  fire_fake  same on fakes. fire_gen ≈ fire_fake with auc ≈ 0.5 is the dead-rule
             signature: it fires constantly and tells you nothing.
  mean_gen   mean points added to genuine files — the "free points" a rule hands
  mean_fake  out. A positive mean_gen with auc ≈ 0.5 is a threshold tax: it
             lowers the effective bar for every innocent file by that many points.
  n_gen/fake how many files the rule actually ran on (gated rules run on a subset)

AUC is computed on the pooled population. That is the right question here — "does
this rule's output separate fake from genuine?" — but it is NOT a cross-validated
generalisation estimate, and this file does not claim one. See ml/README.md for
the mp3_pattern incident: a pooled AUC of 0.99 on a near-constant feature. Any
rule that looks good here still has to survive ml/wild_audit.py.

Usage::

    # 1. score the corpus (slow; writes ml/rule_audit.csv)
    python ml/rule_audit.py score --corpus C:/Users/loutr/audit_corpus

    # 2. report (fast, re-runnable)
    python ml/rule_audit.py report
"""

from __future__ import annotations

import argparse
import csv
import logging
import multiprocessing as mp
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DEFAULT_CSV = Path("ml/rule_audit.csv")

# Every rule the calculator can credit, in pipeline order. Listed explicitly (not
# discovered) so a rule that silently stops running shows up as an empty column
# rather than vanishing from the report.
RULES: Tuple[str, ...] = (
    "Rule1MP3Bitrate",
    "Rule2Cutoff",
    "Rule3SourceVsContainer",
    "Rule424BitSuspect",
    "Rule5HighVariance",
    "Rule6HighQualityProtection",
    "Rule7SilenceAnalysis",
    "Rule8NyquistException",
    "Rule10Consistency",
    "Rule11CassetteDetection",
    "Rule12MLClassifier",
    "Rule13MDCTAlignment",
    "_calculator",
)


def auc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Mann-Whitney AUC of ``pos`` over ``neg`` (ties count as 0.5).

    Written out rather than pulled from sklearn: this file must stay runnable in
    the plain runtime venv, which has no sklearn.
    """
    if not pos or not neg:
        return float("nan")
    ordered = sorted([(v, 0) for v in neg] + [(v, 1) for v in pos])
    # Average ranks over ties, then use the rank-sum identity.
    ranks: List[float] = [0.0] * len(ordered)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_sum_pos = sum(r for r, (_, lab) in zip(ranks, ordered) if lab == 1)
    n_pos, n_neg = len(pos), len(neg)
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for ``k`` successes out of ``n``.

    Reported alongside every rate because the honest reading of "0 out of 29" is
    "up to 11.7 %", not "zero" — the point Provir's benchmark makes about both
    tools' false-positive rows.
    """
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _score_one(job: Tuple[str, int, str, str]) -> Optional[Dict[str, object]]:
    """Score one file and return its row (label, codec, verdict, per-rule points)."""
    path, label, codec, slug = job
    try:
        from flac_detective.analysis.analyzer import FLACAnalyzer

        result = FLACAnalyzer(sample_duration=30.0, deep=True).analyze_file(path)
    except Exception as exc:  # a corpus file must never abort the sweep
        log.warning("scoring failed for %s: %s", path, exc)
        return None
    if result.get("verdict") == "ERROR":
        log.warning("analyzer returned ERROR for %s", path)
        return None

    # No absolute path in the row. This CSV is committed (the CI guard reads it),
    # and the repo deliberately keeps the personal library's paths out of a public
    # repository — ml/authentic_files.json is gitignored for the same reason.
    # ``slug`` identifies the source uniquely within the corpus, which is all the
    # analysis needs.
    row: Dict[str, object] = {
        "slug": slug,
        "label": label,
        "codec": codec,
        "score": result["score"],
        "verdict": result["verdict"],
        "cutoff_freq": round(float(result.get("cutoff_freq") or 0.0), 1),
    }
    breakdown = result.get("score_breakdown") or {}
    for rule in RULES:
        row[rule] = breakdown.get(rule, "")  # "" = rule did not run on this file
    return row


def _jobs(corpus: Path) -> List[Tuple[str, int, str, str]]:
    """Enumerate (path, label, codec, slug) over the corpus."""
    jobs: List[Tuple[str, int, str, str]] = []
    for f in sorted((corpus / "authentic").glob("*.flac")):
        jobs.append((str(f), 0, "authentic", f.stem))
    for codec_dir in sorted((corpus / "fake").glob("*")):
        if codec_dir.is_dir():
            for f in sorted(codec_dir.glob("*.flac")):
                jobs.append((str(f), 1, codec_dir.name, f.stem))
    return jobs


def cmd_score(args: argparse.Namespace) -> int:
    """Score every file in the corpus and write the per-rule CSV."""
    jobs = _jobs(args.corpus)
    if not jobs:
        log.error("no files under %s", args.corpus)
        return 1
    log.info("Scoring %d files with %d workers…", len(jobs), args.workers)

    rows: List[Dict[str, object]] = []
    if args.workers == 1:
        for n, job in enumerate(jobs, 1):
            row = _score_one(job)
            if row:
                rows.append(row)
            if n % 25 == 0:
                log.info("  %d/%d", n, len(jobs))
    else:
        with mp.Pool(args.workers) as pool:
            for n, row in enumerate(pool.imap_unordered(_score_one, jobs, chunksize=2), 1):
                if row:
                    rows.append(row)
                if n % 25 == 0:
                    log.info("  %d/%d", n, len(jobs))

    fields = ["slug", "label", "codec", "score", "verdict", "cutoff_freq", *RULES]
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), args.csv)
    return 0


def load(csv_path: Path) -> List[Dict[str, str]]:
    """Read the audit CSV."""
    with open(csv_path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cmd_report(args: argparse.Namespace) -> int:
    """Print the per-rule verdict table and the per-codec detection table."""
    rows = load(args.csv)
    if not rows:
        log.error("empty csv: %s", args.csv)
        return 1

    gen = [r for r in rows if r["label"] == "0"]
    fake = [r for r in rows if r["label"] == "1"]
    print(
        f"\nCorpus: {len(gen)} genuine, {len(fake)} fakes across "
        f"{len(set(r['codec'] for r in fake))} codecs\n"
    )

    print("PER-RULE DISCRIMINATION (a rule at AUC 0.50 is a coin flip)")
    print(
        f"{'rule':<28} {'auc':>6} {'n_gen':>6} {'n_fake':>7} "
        f"{'fire_gen':>9} {'fire_fake':>10} {'mean_gen':>9} {'mean_fake':>10}  verdict"
    )
    print("-" * 118)

    dead: List[str] = []
    for rule in RULES:
        g = [float(r[rule]) for r in gen if r[rule] != ""]
        f = [float(r[rule]) for r in fake if r[rule] != ""]
        if not g and not f:
            print(f"{rule:<28} {'—':>6} {0:>6} {0:>7}   never ran on this corpus")
            continue
        a = auc(f, g)
        fire_g = sum(1 for v in g if v != 0) / len(g) if g else float("nan")
        fire_f = sum(1 for v in f if v != 0) / len(f) if f else float("nan")
        mean_g = sum(g) / len(g) if g else float("nan")
        mean_f = sum(f) / len(f) if f else float("nan")

        # A rule earns its place by separating. "Dead" = near-chance AUC while
        # actually firing; a rule that simply never fires is inert, not harmful.
        is_dead = (a == a) and abs(a - 0.5) < 0.05 and (fire_g > 0.10 or fire_f > 0.10)
        note = "DEAD — fires without separating" if is_dead else ""
        if not note and (a == a) and abs(a - 0.5) < 0.05:
            note = "inert (never fires)"
        if is_dead:
            dead.append(rule)

        print(
            f"{rule:<28} {a:>6.3f} {len(g):>6} {len(f):>7} "
            f"{fire_g:>9.3f} {fire_f:>10.3f} {mean_g:>9.2f} {mean_f:>10.2f}  {note}"
        )

    print()
    if dead:
        print(f"DEAD RULES: {', '.join(dead)}")
        for rule in dead:
            g = [float(r[rule]) for r in gen if r[rule] != ""]
            tax = sum(g) / len(g) if g else 0.0
            if tax > 0:
                print(
                    f"  {rule}: hands genuine files {tax:.1f} points on average — "
                    f"the WARNING bar (31) is effectively {31 - tax:.0f} for them"
                )
    else:
        print("No dead rule detected at the |AUC-0.5| < 0.05 threshold.")

    _codec_table(gen, fake)
    return 0


def _codec_table(gen: List[Dict[str, str]], fake: List[Dict[str, str]]) -> None:
    """Print detection rates per codec, split by verdict tier."""
    hard = {"FAKE_CERTAIN"}
    review = {"SUSPICIOUS", "WARNING"}

    print("\nPER-CODEC DETECTION")
    print(f"{'codec':<14} {'n':>4} {'any flag':>9} {'conviction':>11}")
    print("-" * 42)
    k = sum(1 for r in gen if r["verdict"] in hard | review)
    lo, hi = wilson(k, len(gen))
    print(
        f"{'GENUINE (FP)':<14} {len(gen):>4} {k/len(gen):>8.1%} "
        f"{sum(1 for r in gen if r['verdict'] in hard)/len(gen):>10.1%}   "
        f"(any-flag Wilson-95: {lo:.1%}–{hi:.1%})"
    )
    for codec in sorted(set(r["codec"] for r in fake)):
        sub = [r for r in fake if r["codec"] == codec]
        anyf = sum(1 for r in sub if r["verdict"] in hard | review) / len(sub)
        conv = sum(1 for r in sub if r["verdict"] in hard) / len(sub)
        print(f"{codec:<14} {len(sub):>4} {anyf:>8.1%} {conv:>10.1%}")
    total_any = sum(1 for r in fake if r["verdict"] in hard | review) / len(fake)
    total_conv = sum(1 for r in fake if r["verdict"] in hard) / len(fake)
    print("-" * 42)
    print(f"{'ALL FAKES':<14} {len(fake):>4} {total_any:>8.1%} {total_conv:>10.1%}")


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="score the corpus into a per-rule CSV")
    s.add_argument("--corpus", required=True, type=Path)
    s.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    s.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 1))
    s.set_defaults(func=cmd_score)

    r = sub.add_parser("report", help="print the per-rule and per-codec tables")
    r.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    r.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
