#!/usr/bin/env python3
"""DEAD_STRUCTURE on the wild53: does the dead-run family survive MASTERING?

The question, and why it reopens a closed negative
---------------------------------------------------
``ml/dead_run_probe.py`` measured max_run on our lab corpus in August and read a
clean negative: median 0.000, AUC 0.49–0.60 on DIRECT transcodes. Provir's
``DEAD_STRUCTURE_MAXRUN`` reads 100–233 on his wild files and carries most of
his 12 SUSPECT verdicts on the Nu Breed 53 — the population our engine signals
at 8.8 %. The lab-to-wild gap cuts both ways: a family dead on direct
transcodes may be alive on re-mastered ones, because a run of abandoned bins is
an absence, and an absence survives EQ, limiting and re-encoding in a way that
alignment does not.

Registered before the run:

    D1  On the 34 owner-attested wilds, median max_run exceeds the genuine
        control's p90. (Direction: the family reads re-mastered transcodes.)
    D2  At a bar set at the genuine control's p95, at least 30 % of the 34
        fire. (His flag reads the tier at ~35 % SUSPECT-carrying; we register
        a lower bound, not parity, since his statistic is not ours.)
    D3  CD3 (eye tier) is reported separately and never averaged in.

Being wrong on D1 closes the reopened question for good: the family would be
dead on both populations and the difference would be his instrument, not the
mastering. Being right on D1+D2 hands the re-mastered arm its first candidate
family.

Control: 40 wild genuine (archive.org etree) — same provenance class as the
probe's earlier genuine baseline, disjoint from the Nu Breed material.
"""

from __future__ import annotations

import argparse
import csv
import sys
from glob import glob
from pathlib import Path
from typing import List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dead_run_probe import dead_run_stats, read_excerpt  # noqa: E402
from edge_width_probe import auc  # noqa: E402

WILD53 = Path(r"C:\Users\loutr\wild53\21-08-26\Original Hardcore The Nu Breed (2004)")
TIERS = {
    "owner-knowledge": ["CD1 Darren Styles", "CD2 Dougal"],
    "eye": ["CD3 Bonus (Mixed by Styles and Dougal)"],
}
GENUINE_GLOB = r"C:\Users\loutr\wild_authentic\*.flac"


def measure(path: Path) -> Optional[dict]:
    try:
        mono, rate = read_excerpt(path)
    except Exception:
        return None
    max_run, mean_run, dead_frac = dead_run_stats(mono, rate)
    if not np.isfinite(max_run):
        return None
    return {"track": path.name, "max_run": max_run, "mean_run": mean_run, "dead_frac": dead_frac}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genuine", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("ml/wild53_deadrun.csv"))
    args = parser.parse_args(argv)

    rows: List[dict] = []
    for tier, dirs in TIERS.items():
        n = 0
        for d in dirs:
            for path in sorted((WILD53 / d).glob("*.wav")):
                row = measure(path)
                if row:
                    row["tier"] = tier
                    rows.append(row)
                    n += 1
        print(f"{tier}: {n} mesures", flush=True)

    n = 0
    for raw in sorted(glob(GENUINE_GLOB))[: args.genuine * 2]:
        if n >= args.genuine:
            break
        row = measure(Path(raw))
        if row:
            row["tier"] = "genuine"
            rows.append(row)
            n += 1
    print(f"genuine: {n} mesures", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["tier", "track", "max_run", "mean_run", "dead_frac"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} lignes -> {args.out}\n", flush=True)

    gen = np.array([r["max_run"] for r in rows if r["tier"] == "genuine"])
    print(f"{'tier':16}{'n':>4}{'med max_run':>13}{'p90':>8}{'AUC vs gen':>12}")
    for tier in ("genuine", "owner-knowledge", "eye"):
        vals = np.array([r["max_run"] for r in rows if r["tier"] == tier])
        if not vals.size:
            continue
        a = auc(vals, gen) if tier != "genuine" else float("nan")
        print(
            f"{tier:16}{vals.size:>4}{np.median(vals):>13.1f}"
            f"{np.percentile(vals, 90):>8.1f}{a:>12.2f}"
        )

    owner = np.array([r["max_run"] for r in rows if r["tier"] == "owner-knowledge"])
    eye = np.array([r["max_run"] for r in rows if r["tier"] == "eye"])
    if gen.size and owner.size:
        d1 = np.median(owner) > np.percentile(gen, 90)
        bar = float(np.percentile(gen, 95))
        k = int((owner > bar).sum())
        d2 = k >= 0.30 * owner.size
        print(
            f"\nD1  owner median > genuine p90:   {'HELD' if d1 else 'FAILED'}"
            f"   ({np.median(owner):.1f} vs {np.percentile(gen, 90):.1f})"
        )
        print(
            f"D2  >=30 % of 34 over genuine p95: {'HELD' if d2 else 'FAILED'}"
            f"   ({k}/{owner.size} over bar {bar:.1f})"
        )
        if eye.size:
            ke = int((eye > bar).sum())
            print(f"D3  eye tier, separately:          {ke}/{eye.size} over the same bar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
