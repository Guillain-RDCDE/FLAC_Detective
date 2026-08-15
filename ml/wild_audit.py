#!/usr/bin/env python3
"""False-positive validation at scale — the check the audit corpus cannot give.

The audit corpus has 80 genuine files. A clean run on 80 files carries a Wilson-95
upper bound around 4.5 %, which is not enough to ship a new rule on: a detector
that flags 3 % of a real library would be unusable and would still look perfect
at n=80. Jamie Dodd quotes ~1,700 lawful files for Provir's equivalent number,
and that is the right order of magnitude.

Two modes, because "wild" means two different things:

``sample``
    Draw N files from the certified-authentic library (EAC/XLD/Audiochecker
    ripper logs — see ml/authentic_files.json) that were NOT used to build the
    audit corpus, and measure how often Rule 13's statistic crosses its
    thresholds. Large n, same-library material.

``scan``
    Run the FULL pipeline over a directory of genuine files from outside the
    library entirely (e.g. ml/fetch_wild_authentic.py's Internet Archive pull)
    and report the verdict distribution. Smaller n, genuinely foreign material,
    including deliberately hostile audience recordings.

Neither is a sensitivity test. Both answer only: *how often do we accuse someone
who did nothing wrong?*

Usage::

    python ml/wild_audit.py sample --n 400 --exclude-manifest C:/…/audit_corpus/manifest.json
    python ml/wild_audit.py scan --dir C:/Users/loutr/wild_authentic
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import multiprocessing as mp
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SEED = 20260814


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval — the honest reading of a clean run."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _mdct_one(path: str) -> Optional[Dict[str, object]]:
    """Compute Rule 13's statistic on one genuine file."""
    try:
        import numpy as np
        import soundfile as sf

        from flac_detective.analysis.new_scoring.mdct import alignment_stat

        info = sf.info(path)
        if info.duration < 20:
            return None
        start = max(0, int((info.duration - 30) / 2 * info.samplerate))
        data, sr = sf.read(path, start=start, frames=int(30 * info.samplerate), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        ratio, offset = alignment_stat(np.ascontiguousarray(data), sr)
    except Exception as exc:
        log.warning("failed on %s: %s", path, exc)
        return None
    # A stable anonymous id rather than the path: these files are someone's
    # private music library, and the committed CSV only needs to identify rows
    # well enough to be re-joined against a local re-run.
    file_id = hashlib.sha1(path.encode("utf-8", "replace")).hexdigest()[:12]
    return {"file_id": file_id, "peak_ratio": round(float(ratio), 4), "best_offset": int(offset)}


def _scan_one(path: str) -> Optional[Dict[str, object]]:
    """Run the full pipeline on one file."""
    try:
        from flac_detective.analysis.analyzer import FLACAnalyzer

        r = FLACAnalyzer(sample_duration=30.0, deep=True).analyze_file(path)
    except Exception as exc:
        log.warning("failed on %s: %s", path, exc)
        return None
    if r.get("verdict") == "ERROR":
        return None
    breakdown = r.get("score_breakdown") or {}
    return {
        "file_id": hashlib.sha1(path.encode("utf-8", "replace")).hexdigest()[:12],
        "score": r["score"],
        "verdict": r["verdict"],
        "cutoff_freq": round(float(r.get("cutoff_freq") or 0.0), 1),
        "Rule13MDCTAlignment": breakdown.get("Rule13MDCTAlignment", ""),
    }


def cmd_sample(args: argparse.Namespace) -> int:
    """Measure Rule 13's statistic over a large certified-genuine sample."""
    data = json.loads(args.authentic_json.read_text(encoding="utf-8"))
    files = [e["path"] for e in data["files"]]

    excluded = set()
    if args.exclude_manifest and args.exclude_manifest.exists():
        manifest = json.loads(args.exclude_manifest.read_text(encoding="utf-8"))
        excluded = {s["origin"] for s in manifest.get("sources", [])}
        log.info("Excluding %d files already used to build the audit corpus", len(excluded))

    pool = [f for f in files if f not in excluded]
    rng = random.Random(SEED)
    rng.shuffle(pool)
    chosen = [f for f in pool if Path(f).exists()][: args.n]
    log.info("Measuring %d certified-genuine files with %d workers…", len(chosen), args.workers)

    rows: List[Dict[str, object]] = []
    with mp.Pool(args.workers) as p:
        for i, row in enumerate(p.imap_unordered(_mdct_one, chosen, chunksize=2), 1):
            if row:
                rows.append(row)
            if i % 25 == 0:
                log.info("  %d/%d", i, len(chosen))

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file_id", "peak_ratio", "best_offset"])
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote %d rows to %s", len(rows), args.out)
    _report_sample(rows)
    return 0


def _report_sample(rows: List[Dict[str, object]]) -> None:
    """Print the false-positive rate at each Rule 13 threshold."""
    from flac_detective.analysis.new_scoring.rules.mdct_alignment import (
        RATIO_HARD,
        RATIO_REVIEW,
    )

    vals = sorted(
        float(r["peak_ratio"]) for r in rows if float(r["peak_ratio"]) == float(r["peak_ratio"])
    )
    n = len(vals)
    if n == 0:
        print("no usable measurements")
        return
    print(f"\nRULE 13 ON {n} CERTIFIED-GENUINE FILES")
    print(
        f"  median {vals[n // 2]:.2f}   p95 {vals[int(n * 0.95)]:.2f}   "
        f"p99 {vals[min(n - 1, int(n * 0.99))]:.2f}   max {vals[-1]:.2f}"
    )
    for name, thr in (("review (+22)", RATIO_REVIEW), ("hard (+45)", RATIO_HARD)):
        k = sum(1 for v in vals if v >= thr)
        lo, hi = wilson(k, n)
        print(
            f"  crosses {name:<13} ratio ≥ {thr:<5}: {k}/{n} = {k/n:.2%}  "
            f"(Wilson-95 {lo:.2%}–{hi:.2%})"
        )


def cmd_scan(args: argparse.Namespace) -> int:
    """Run the full pipeline over a directory of genuine files."""
    files = [str(f) for f in sorted(args.dir.rglob("*.flac"))]
    if not files:
        log.error("no FLACs under %s", args.dir)
        return 1
    log.info("Scanning %d wild files with %d workers…", len(files), args.workers)

    rows: List[Dict[str, object]] = []
    with mp.Pool(args.workers) as p:
        for i, row in enumerate(p.imap_unordered(_scan_one, files, chunksize=1), 1):
            if row:
                rows.append(row)
            if i % 10 == 0:
                log.info("  %d/%d", i, len(files))

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["file_id", "score", "verdict", "cutoff_freq", "Rule13MDCTAlignment"]
        )
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    print(f"\nFULL PIPELINE ON {n} WILD GENUINE FILES (every one should read AUTHENTIC)")
    counts: Dict[str, int] = {}
    for r in rows:
        counts[str(r["verdict"])] = counts.get(str(r["verdict"]), 0) + 1
    for verdict, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {verdict:<14} {count:>4}  {count/n:.1%}")
    flagged = n - counts.get("AUTHENTIC", 0)
    lo, hi = wilson(flagged, n)
    print(f"  FALSE POSITIVE RATE: {flagged}/{n} = {flagged/n:.1%} (Wilson-95 {lo:.1%}–{hi:.1%})")
    # "" means the rule never ran on that file; 0 means it ran and abstained.
    # Conflating the two once made a clean 0/178 read as "Rule 13 contributed to
    # 162 files", which is the opposite of what happened.
    ran = [r for r in rows if str(r["Rule13MDCTAlignment"]) != ""]
    scored = [r for r in ran if float(r["Rule13MDCTAlignment"] or 0) != 0]
    lo, hi = wilson(len(scored), len(ran)) if ran else (float("nan"), float("nan"))
    print(f"  Rule 13 ran on {len(ran)}, scored on {len(scored)} "
          f"({len(scored)}/{len(ran)}, Wilson-95 up to {hi:.1%})")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sample", help="Rule 13 statistic over a large certified sample")
    s.add_argument("--n", type=int, default=400)
    s.add_argument("--authentic-json", type=Path, default=Path("ml/authentic_files.json"))
    s.add_argument("--exclude-manifest", type=Path, default=None)
    s.add_argument("--out", type=Path, default=Path("ml/wild_rule13_genuine.csv"))
    s.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 1))
    s.set_defaults(func=cmd_sample)

    c = sub.add_parser("scan", help="full pipeline over a directory of wild genuine files")
    c.add_argument("--dir", required=True, type=Path)
    c.add_argument("--out", type=Path, default=Path("ml/wild_scan.csv"))
    c.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 1))
    c.set_defaults(func=cmd_scan)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
