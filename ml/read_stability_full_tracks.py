"""Read stability on FULL tracks, the regime the exchange sets cannot reach.

The excerpt-length test on set A answered its question — no verdict moved at 15,
30 or 60 seconds — but every file in that set is a 60-second excerpt, so the
spectral path takes ONE sample from it. Real files are longer than 90 seconds,
which is where ``analyze_spectrum`` switches to three samples at start, middle
and end, and that is the regime a user is actually in. It had never been
measured.

This runs whole tracks from the audit corpus at three excerpt lengths and reports
any verdict that moves. Authentic and transcoded both, because a read-dependent
verdict is worth knowing about in either direction.

Usage::

    python ml/read_stability_full_tracks.py --n 20 --out ml/read_stability_full.csv
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DURATIONS = (15.0, 30.0, 60.0)
MIN_DURATION_S = 90.0


def pick(corpus: Path, n: int) -> List[tuple]:
    """Files longer than 90 s, which is where the spectral path takes three samples.

    The audit corpus cannot serve here: every file in it is a 60-second excerpt,
    so it sits in the same one-sample regime as the exchange sets and would answer
    the question already answered. Anything shorter is skipped and counted rather
    than silently included, because a sample that quietly falls back into the old
    regime would produce a reassuring number about nothing.
    """
    import soundfile as sf

    out, short = [], 0
    for path in sorted(corpus.rglob("*.flac")):
        try:
            if sf.info(str(path)).duration < MIN_DURATION_S:
                short += 1
                continue
        except Exception:
            continue
        out.append((path, corpus.name))
        if len(out) >= n:
            break
    if short:
        print(f"  ({short} fichiers ecartes, plus courts que {MIN_DURATION_S:g} s)", flush=True)
    return out


def main() -> int:
    """Score each file at each excerpt length and report the verdicts that move."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True, help="a folder of FULL tracks")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    logging.disable(logging.CRITICAL)
    from flac_detective.analysis.analyzer import FLACAnalyzer

    files = pick(args.corpus, args.n)
    if not files:
        raise SystemExit(f"aucune piste de plus de {MIN_DURATION_S:g} s sous {args.corpus}")
    print(f"{len(files)} fichiers, {len(DURATIONS)} lectures chacun", flush=True)

    analyzers = {d: FLACAnalyzer(sample_duration=d, deep=True) for d in DURATIONS}
    rows = []
    moved = 0
    for index, (path, population) in enumerate(files, 1):
        verdicts = {}
        for duration in DURATIONS:
            try:
                result = analyzers[duration].analyze_file(str(path))
                verdicts[duration] = (result.get("verdict", "?"), result.get("score", ""))
            except Exception as exc:  # a crash is data
                verdicts[duration] = (f"ECHEC:{type(exc).__name__}", "")
        distinct = {v[0] for v in verdicts.values()}
        if len(distinct) > 1:
            moved += 1
            print(f"  BOUGE {path.name}: " + ", ".join(f"{d:g}s={verdicts[d][0]}" for d in DURATIONS), flush=True)
        rows.append(
            {
                "file": path.name,
                "population": population,
                **{f"verdict_{d:g}s": verdicts[d][0] for d in DURATIONS},
                **{f"score_{d:g}s": verdicts[d][1] for d in DURATIONS},
                "moved": "yes" if len(distinct) > 1 else "no",
            }
        )
        print(f"  {index}/{len(files)}", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"ecrit {args.out}", flush=True)
    print(f"verdicts qui bougent avec la longueur de lecture: {moved}/{len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
