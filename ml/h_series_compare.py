#!/usr/bin/env python3
"""H1/H3 are defined AGAINST SHIPPED v1.12, so they need a cross-CSV diff.

The --evaluate pass grades within one inputs file; H1 ("newly +50 vs shipped
v1.12") and H3 ("no decrease from 160") compare v1.13's measurements against
v1.12's. This script runs the same repaired-rule mirror over both CSVs and
reports, per population, who gained and who lost the +50 — with the measured
inputs of every mover, because a moved file is a claim and claims carry their
evidence. Results are appended to the H-series block in r1_gates_repricing.py.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r1_gates_repricing import adjudicated_fakes, new_r1_plus50  # noqa: E402

V112 = Path("ml/r1_gates_inputs.csv")
V113 = Path("ml/r1_gates_inputs_v113.csv")


def load(path: Path) -> dict:
    rows = {}
    relabeled = adjudicated_fakes()
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        pop = r["population"]
        if pop.startswith("genuine") and r["track"] in relabeled:
            pop = "adjudicated_fake"
        rows[(pop, r["track"])] = r
    return rows


def main() -> int:
    a, b = load(V112), load(V113)
    common = sorted(set(a) & set(b))
    print(f"v1.12 rows {len(a)}, v1.13 rows {len(b)}, common {len(common)}")

    per_pop = defaultdict(lambda: [0, 0, 0, 0])  # v112+, v113+, gained, lost
    movers = []
    for key in common:
        was, now = new_r1_plus50(a[key]), new_r1_plus50(b[key])
        s = per_pop[key[0]]
        s[0] += was
        s[1] += now
        if now and not was:
            s[2] += 1
            movers.append(("GAINED", key, a[key], b[key]))
        elif was and not now:
            s[3] += 1
            movers.append(("LOST", key, a[key], b[key]))

    print(f"\n{'population':16}{'v112 +50':>9}{'v113 +50':>9}{'gained':>8}{'lost':>6}")
    for pop in sorted(per_pop):
        s = per_pop[pop]
        print(f"{pop:16}{s[0]:>9}{s[1]:>9}{s[2]:>8}{s[3]:>6}")

    # H1-ter: the genuine corpora AS WAV. A WAV of the same audio measures the
    # same cutoff/variance/energy/residual — only the container reads ~1411
    # kbps — so the control is the v1.13 rows with the container overridden,
    # exactly what "converted to WAV, through the rule" means offline.
    as_wav_newly = []
    for key in sorted(b):
        pop = key[0]
        if not pop.startswith("genuine"):
            continue
        row = dict(b[key])
        as_flac = new_r1_plus50(row)
        row["container_kbps"] = "1411"
        if new_r1_plus50(row) and not as_flac:
            as_wav_newly.append(key)
    print(
        f"\nH1-ter genuine-as-WAV newly +50 vs FLAC selves: {len(as_wav_newly)}"
        f" (bound <= 2): {'HELD' if len(as_wav_newly) <= 2 else 'FAILED'}"
    )
    for key in as_wav_newly:
        print(f"  {key[0]} {key[1]}")

    print("\nmovers (measured inputs, v1.12 -> v1.13):")
    for direction, (pop, track), r0, r1 in movers:
        print(
            f"  {direction:6} {pop:14} {track[:52]:52} "
            f"cutoff {float(r0['cutoff']):.0f}->{float(r1['cutoff']):.0f} "
            f"resid {r0['residual_floor_db']}->{r1['residual_floor_db']} "
            f"std {float(r1['cutoff_std']):.0f} kbps {float(r1['container_kbps']):.0f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
