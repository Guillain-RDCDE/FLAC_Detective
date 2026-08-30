#!/usr/bin/env python3
"""Before/after pass for the R11D typed-absence repair.

Criteria were registered first, in
``ml/exchange/R11D_ABSENCE_REGISTRATION_2026-08-30.md``, before this script ran
and before the repair was made. This file only produces the numbers that
document scores them.

Two corpora, same files and same order in both passes:

    fd-exchange-v2   590 files, the adjudicated key of 2026-08-23
    audit_corpus     80 genuine + 80 mp3_320, labelled by construction

Usage::

    python ml/r11d_absence_pass.py --out ml/r11d_before.csv          # shipped code
    python ml/r11d_absence_pass.py --out ml/r11d_after.csv           # after repair
    python ml/r11d_absence_pass.py --compare ml/r11d_before.csv ml/r11d_after.csv

Both passes are resumable and sharded (``--shard i/n``) because the engine costs
about ten seconds a file and the machine has four cores.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

EXCHANGE = Path(r"C:\Users\loutr\fd-exchange-v2-2026-08\audio")
CORPUS = Path(r"C:\Users\loutr\audit_corpus")

FIELDS = [
    "file",
    "corpus",
    "label",
    "score",
    "verdict",
    "cutoff_hz",
    "cutoff_std_hz",
    "cassette_reasons",
    "rule11",
    "rule1",
    "evidence_families",
]


def corpus_files() -> List[tuple]:
    """(path, corpus, label) for every file of both corpora, deterministic order."""
    out: List[tuple] = []
    for p in sorted(EXCHANGE.glob("*.flac")):
        out.append((p, "fd-exchange-v2", ""))  # the key lives outside this file
    for p in sorted((CORPUS / "authentic").glob("*.flac")):
        out.append((p, "audit_corpus", "genuine"))
    for p in sorted((CORPUS / "fake" / "mp3_320").glob("*.flac")):
        out.append((p, "audit_corpus", "mp3_320"))
    return out


def read_one(path: Path, corpus: str, label: str, analyzer) -> Optional[Dict[str, object]]:
    from flac_detective.analysis.spectrum import analyze_spectrum

    try:
        result = analyzer.analyze_file(str(path))
    except Exception as exc:  # a failure is data, not a reason to stop the pass
        print(f"  ENGINE FAILED {path.name}: {exc}", flush=True)
        return None
    if result.get("verdict") == "ERROR":
        return None
    try:
        cutoff, _energy, std, _resid = analyze_spectrum(path)
    except Exception:
        cutoff, std = float("nan"), float("nan")

    # The engine exposes no cassette_score of its own; the decisive column is
    # Rule11's own contribution in the breakdown (-40 when the protection fires,
    # 0 otherwise), and `reason` carries the sentence that names it.
    breakdown = result.get("score_breakdown", {}) or {}
    reason = str(result.get("reason", "") or "")
    reasons = [seg for seg in reason.split(";") if "R11" in seg or "cassette" in seg.lower()]
    return {
        "file": path.name,
        "corpus": corpus,
        "label": label,
        "score": result.get("score"),
        "verdict": result.get("verdict"),
        "cutoff_hz": f"{cutoff:.1f}",
        "cutoff_std_hz": f"{std:.1f}",
        "cassette_reasons": " | ".join(reasons),
        "rule11": breakdown.get("Rule11CassetteDetection", ""),
        "rule1": breakdown.get("Rule1MP3Bitrate", ""),
        "evidence_families": "+".join(result.get("evidence_families", []) or []),
    }


def run(out_path: Path, shard: str, limit: int, only: str = "") -> int:
    from flac_detective.analysis.analyzer import FLACAnalyzer

    files = corpus_files()
    if only:
        wanted = {
            line.strip()
            for line in Path(only).read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        files = [f for f in files if f[0].name in wanted]
        missing = wanted - {f[0].name for f in files}
        if missing:
            raise SystemExit(
                f"{len(missing)} fichiers de la liste introuvables: {sorted(missing)[:3]}"
            )
        print(f"liste explicite: {len(files)} fichiers", flush=True)
    if shard:
        i, n = (int(x) for x in shard.split("/"))
        files = [f for k, f in enumerate(files) if k % n == i]
    if limit:
        files = files[:limit]

    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {r["file"] for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    analyzer = FLACAnalyzer(deep=True)
    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for k, (path, corpus, label) in enumerate(files, 1):
            if path.name in done:
                continue
            row = read_one(path, corpus, label, analyzer)
            if row is None:
                continue
            writer.writerow(row)
            fh.flush()
            if k % 25 == 0:
                print(f"  {k}/{len(files)}", flush=True)
    print(f"ecrit {out_path}", flush=True)
    return 0


def compare(before_path: Path, after_path: Path) -> int:
    def load(p: Path) -> Dict[str, Dict[str, str]]:
        # Keyed by (corpus, label, file), never by file alone: the transcode arms
        # keep their parent's basename, so audit_corpus/authentic/x.flac and
        # audit_corpus/fake/mp3_320/x.flac are two different files with one name.
        # Keying on the name silently dropped one of each pair.
        with open(p, newline="", encoding="utf-8") as fh:
            return {f"{r['corpus']}/{r['label']}/{r['file']}": r for r in csv.DictReader(fh)}

    before, after = load(before_path), load(after_path)
    common = sorted(set(before) & set(after))
    print(f"{len(before)} avant, {len(after)} apres, {len(common)} communs\n")

    movers = [f for f in common if before[f]["verdict"] != after[f]["verdict"]]
    rescored = [f for f in common if before[f]["score"] != after[f]["score"]]
    print(f"verdicts changes : {len(movers)}")
    print(f"scores changes   : {len(rescored)}")

    def is_conv(r):
        return r["verdict"] == "FAKE_CERTAIN"

    def is_sig(r):
        return r["verdict"] in ("FAKE_CERTAIN", "SUSPICIOUS", "WARNING")

    genuine = [f for f in common if before[f]["label"] == "genuine"]
    a1 = [f for f in genuine if not is_conv(before[f]) and is_conv(after[f])]
    a2 = [f for f in genuine if not is_sig(before[f]) and is_sig(after[f])]
    a3 = [f for f in common if is_conv(before[f]) and not is_conv(after[f])]
    e1 = [f for f in genuine if is_sig(before[f]) and not is_sig(after[f])]
    outside = [
        f
        for f in rescored
        if not (before[f]["cutoff_hz"] not in ("nan",) and float(before[f]["cutoff_hz"]) < 19000)
    ]

    print(f"\nA1 genuine nouvellement convicted : {len(a1)}  (borne 0) {a1[:10]}")
    print(f"A2 genuine nouvellement signaled  : {len(a2)}  (borne 0) {a2[:10]}")
    print(f"A3 transcodes qui perdent la conviction : {len(a3)}  (borne 5)")
    print(f"A4 fichiers bouges hors cutoff<19000 : {len(outside)}  (borne 0) {outside[:10]}")
    print(f"E1 genuine qui perdent le signalement : {len(e1)}  {e1[:10]}")

    for f in movers[:40]:
        b, a = before[f], after[f]
        print(
            f"  {f} [{b['label'] or b['corpus']}] {b['verdict']}({b['score']}) -> "
            f"{a['verdict']}({a['score']}) | cutoff {b['cutoff_hz']} std {b['cutoff_std_hz']} -> "
            f"{a['cutoff_std_hz']} | R11 {b['rule11']}->{a['rule11']} R1 {b['rule1']}->{a['rule1']}"
        )
    if len(movers) > 40:
        print(f"  ... et {len(movers) - 40} autres")

    verdict = "TENUS" if not a1 and not a2 and len(a3) <= 5 and not outside else "ECHEC"
    print(f"\ncriteres A1/A2/A3/A4 : {verdict}")
    return 0 if verdict == "TENUS" else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    ap.add_argument("--shard", default="", help="i/n")
    ap.add_argument(
        "--files",
        default="",
        help="text file of basenames: run only those (the movers the scope pass found)",
    )
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = ap.parse_args(argv)

    if args.compare:
        return compare(Path(args.compare[0]), Path(args.compare[1]))
    if not args.out:
        ap.error("--out ou --compare")
    return run(Path(args.out), args.shard, args.limit, args.files)


if __name__ == "__main__":
    sys.exit(main())
