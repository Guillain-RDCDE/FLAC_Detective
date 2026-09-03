"""Does the verdict depend on WHICH part of a track you read?

The excerpt-length tests answered a narrower question than Provir's. His defect
was that two different EXCERPTS of one lawful file disagreed by more than his
margin — a position problem, not a length one. Varying our excerpt length moves
the window a little, but the spectral path anchors its samples at fixed fractions
of the file, so length alone cannot separate the two effects.

This does: each track is cut into its first and second half, and both halves are
scored as independent files. If a verdict differs between them, the verdict
describes the half rather than the track, and every rate we have published is
partly a statement about where our windows happen to land.

Deliberately built on transcodes as well as clean files: a verdict that nothing
is pulling on cannot move, so measuring only lawful material would produce a
reassuring number about nothing.

Usage::

    python ml/read_position_halves.py --corpus <folder of full tracks> \
        --out ml/read_position_halves.csv
"""

import argparse
import csv
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

MIN_DURATION_S = 90.0


def halves(path: Path, work: Path) -> tuple:
    """Write the first and second half of ``path`` as two FLAC files."""
    import soundfile as sf

    duration = sf.info(str(path)).duration
    mid = duration / 2.0
    first = work / f"{path.stem}__A.flac"
    second = work / f"{path.stem}__B.flac"
    for out, start, length in ((first, 0.0, mid), (second, mid, duration - mid)):
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}",
             "-t", f"{length:.3f}", "-i", str(path), "-c:a", "flac", str(out)],
            check=True,
            capture_output=True,
        )
    return first, second


def main() -> int:
    """Score both halves of every track and report the verdicts that disagree."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    logging.disable(logging.CRITICAL)
    import soundfile as sf

    from flac_detective.analysis.analyzer import FLACAnalyzer

    tracks = []
    for path in sorted(args.corpus.rglob("*.flac")):
        try:
            if sf.info(str(path)).duration >= MIN_DURATION_S:
                tracks.append(path)
        except Exception:
            continue
        if len(tracks) >= args.n:
            break
    if not tracks:
        raise SystemExit(f"aucune piste de plus de {MIN_DURATION_S:g} s sous {args.corpus}")
    print(f"{len(tracks)} pistes, deux moities chacune", flush=True)

    analyzer = FLACAnalyzer(deep=True)
    rows, disagreeing = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for index, path in enumerate(tracks, 1):
            first, second = halves(path, work)
            verdicts = []
            for part in (first, second):
                try:
                    result = analyzer.analyze_file(str(part))
                    verdicts.append((result.get("verdict", "?"), result.get("score", "")))
                except Exception as exc:
                    verdicts.append((f"ECHEC:{type(exc).__name__}", ""))
            differs = verdicts[0][0] != verdicts[1][0]
            disagreeing += differs
            if differs:
                print(f"  DIFFERE {path.name}: {verdicts[0][0]} / {verdicts[1][0]}", flush=True)
            rows.append(
                {
                    "track": path.name,
                    "verdict_first_half": verdicts[0][0],
                    "score_first_half": verdicts[0][1],
                    "verdict_second_half": verdicts[1][0],
                    "score_second_half": verdicts[1][1],
                    "differs": "yes" if differs else "no",
                }
            )
            print(f"  {index}/{len(tracks)}", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"ecrit {args.out}", flush=True)
    print(f"verdicts qui different entre les deux moities: {disagreeing}/{len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
