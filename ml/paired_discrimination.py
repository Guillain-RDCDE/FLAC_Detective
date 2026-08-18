#!/usr/bin/env python3
"""Does a transcode beat the genuine file IT CAME FROM, or just easier material?

The gap this closes. Every AUC in this project pools all fakes against all
genuine files. That measures "can the engine tell this population from that
population", which is not the question a user has. A statistic that tracked
*material* rather than *processing* — loud versus quiet, dense versus sparse —
could score a fine pooled AUC while being unable to tell one recording from its
own transcode. Nothing here had ever checked.

The idea comes from Jamie Dodd of Provir, arriving sideways. He used the corpus's
cluster structure — exactly one file in ten is genuine — to derive bounds on his
own accuracy without an answer key: a cluster cannot hold two genuine files, so
two "clear" verdicts in one cluster means a transcode was called clean. The audit
corpus has the identical structure, 80 sources times 10 arms, so the same
grouping supports a stricter test than the bounds he needed it for.

Paired comparison, per arm: for every source, does its transcode score higher
than the genuine file it was made from? Wins, ties and losses are reported
separately because they mean different things — a loss is a ranking failure, a
tie is usually the engine saying nothing at all about either file, and only the
first is alarming.

Usage::

    python ml/paired_discrimination.py --scores ml/audit_v110.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

GENUINE_ARM = "authentic"


def load(path: Path) -> Dict[str, Dict[str, int]]:
    """Return ``{source_file: {arm: score}}`` from a scored audit CSV."""
    by_source: Dict[str, Dict[str, int]] = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("verdict") == "ERROR" or not row.get("score"):
                continue
            by_source[row["file"]][row["arm"]] = int(row["score"])
    return by_source


def main(argv: Optional[List[str]] = None) -> int:
    """Report paired discrimination per arm."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", type=Path, default=Path("ml/audit_v110.csv"))
    args = parser.parse_args(argv)

    by_source = load(args.scores)
    complete = {f: d for f, d in by_source.items() if GENUINE_ARM in d}
    if not complete:
        raise SystemExit(f"no rows with a '{GENUINE_ARM}' arm in {args.scores}")

    arms = sorted({a for d in complete.values() for a in d} - {GENUINE_ARM})
    print(f"{len(complete)} sources with a genuine arm\n")
    print(f"{'arm':14} {'beats own':>10} {'tied':>6} {'loses':>6}   {'win rate':>9}")

    for arm in arms:
        wins = ties = losses = 0
        for scores in complete.values():
            if arm not in scores:
                continue
            genuine, fake = scores[GENUINE_ARM], scores[arm]
            if fake > genuine:
                wins += 1
            elif fake == genuine:
                ties += 1
            else:
                losses += 1
        total = wins + ties + losses
        if not total:
            continue
        print(f"{arm:14} {wins:>10} {ties:>6} {losses:>6}   {wins / total:>8.1%}")

    print(
        "\nA LOSS is a ranking failure: the engine scored a real recording above its\n"
        "own transcode. A TIE is usually silence on both, which is a blind spot\n"
        "rather than an error. Pooled AUC hides the difference; this does not."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
