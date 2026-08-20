#!/usr/bin/env python3
"""Can a cutoff-relative residual separate a near-Nyquist wall from an open spectrum?

RETRACTED 2026-08-20. The frequency below came from Provir and Jamie Dodd withdrew
it himself: it is one reading of one file by one edge-finder, early 3.9x LAME at
-b 320 applies no lowpass at all (so it measured the SOURCE, not the encoder), and
503 of his 1,180 lawful files already read an edge at or above it. He also disclosed
fusing two different 8 Hz figures — 8.1 Hz store-vs-recreation and ~8 Hz
build-to-build — so "five builds within 8 Hz of a frequency" is unsupported.

The conclusion survives and is stronger: 11 of his 17 real 2009 MP3s wall below
21,479 Hz while 6 have no wall to 22,023, and 28 of his 75 lawful masters sit above
21,570. No edge POSITION separates the populations. See ml/edge_width_probe.py for
what replaced it.

Kept below as written, because a probe's stated premise is part of its result.

The hole this is trying to fill
-------------------------------
Rule 1 awards +50 and every false conviction this project has ever shipped came
from Rule 1 + Rule 3 at +50 each. It is therefore guarded, and the guards are:

    1. cutoff >= 0.95 * Nyquist (20,947.5 Hz)                    -> return
    2. cutoff >  21,500 Hz                                        -> return  (dead)
    3. MP3_SIGNATURES tops out at 21,500                          -> estimate 0
    4. for a 320 estimate, cutoff >= 0.94 * Nyquist (20,727 Hz)   -> return

and the instrument meant to settle the ambiguous zone — `compute_residual_floor_db`,
calibrated at ROC AUC 0.95 — is only COMPUTED when the cutoff lands in
[0.90, 0.95) * Nyquist = [19,845, 20,947.5). Guard 4 then rejects everything from
20,727 up. So the calibrated instrument can only ever act across 882 Hz, and the
top 220 Hz of the window it computes is thrown away unused.

Above 20,947.5 Hz nothing looks at anything. Measured on our own corpus, that
region holds 29 of 40 mp3_V0 and 34 of 40 aac_ff320 — and Jamie Dodd's strongest
exhibit, a store download walling at 21,562.8 Hz whose own CD runs clean to
Nyquist, and whose wall his LAME 3.92 recreation reproduces to 8.1 Hz. The comment
in the rule says "MP3s never have cutoffs above 21.5 kHz". His five era builds say
otherwise and he re-measured them rather than assuming.

Why the existing instrument cannot simply be extended
------------------------------------------------------
`compute_residual_floor_db` reads a FIXED top band, 0.961-0.993 * Nyquist =
21,190-21,896 Hz. That is designed for a wall at ~20.5 kHz, comfortably below the
band. For a wall at 21,570 Hz the band straddles it: half live signal, half digital
silence, and the median comes out mid-way. The instrument would read an era-LAME
brickwall as an authentic rolloff.

So the band has to follow the wall.

What is measured here
---------------------
A cutoff-RELATIVE residual: the floor in a band just above the detected cutoff,
against the same in-band reference.

    ref  = median dB over [0.45, 0.65] * Nyquist      (unchanged)
    top  = median dB over [cutoff + GUARD_HZ, min(cutoff + SPAN_HZ, 0.999 * Nyq)]
    stat = top - ref

and NaN — abstain — whenever that band is too thin to mean anything, which is
exactly what happens for a genuine file whose spectrum runs to Nyquist. Abstaining
there is not a limitation; it is the correct answer, because such a file has no
wall to characterise.

The question this probe answers, and the only one that licenses a code change:
does the statistic separate genuine from transcode among files whose cutoff sits
ABOVE 20,947.5 Hz — the region no guard currently lets any instrument see?

Nothing ships on the argument. The genuine arm decides.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.spectrum import (  # noqa: E402
    _welch_magnitude_db,
    detect_cutoff,
)

EXCERPT_SEC = 30.0

# Skip the first bins above the detected cutoff. A brickwall is not a step
# function after Welch smoothing, and the transition region belongs to neither
# side; including it would read the slope rather than the floor.
GUARD_HZ = 250.0

# How far above the cutoff to measure the floor.
SPAN_HZ = 1400.0

# Below this many usable bins the band cannot carry a median worth acting on, and
# the statistic abstains. This is what makes a spectrum that runs to Nyquist return
# NaN instead of a fabricated reading.
MIN_BINS = 6


def relative_residual(
    magnitude_db: np.ndarray, freq: np.ndarray, cutoff: float, rate: int
) -> float:
    """Floor just above ``cutoff``, relative to the in-band reference. NaN = abstain."""
    nyquist = rate / 2.0
    lo = cutoff + GUARD_HZ
    hi = min(cutoff + SPAN_HZ, 0.999 * nyquist)
    if hi <= lo:
        return float("nan")
    ref_mask = (freq >= 0.45 * nyquist) & (freq <= 0.65 * nyquist)
    top_mask = (freq >= lo) & (freq <= hi)
    if int(top_mask.sum()) < MIN_BINS or not np.any(ref_mask):
        return float("nan")
    return float(np.median(magnitude_db[top_mask]) - np.median(magnitude_db[ref_mask]))


def measure(path: str) -> Optional[dict]:
    """Cutoff, the shipped fixed-band residual, and the cutoff-relative one."""
    try:
        info = sf.info(path)
        data, rate = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if data.size == 0:
        return None
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    mono = np.asarray(mono, dtype=np.float64)
    try:
        freq, magnitude_db = _welch_magnitude_db(mono, rate)
        if freq is None or magnitude_db is None:
            return None
        cutoff = float(detect_cutoff(freq, magnitude_db, rate))
    except Exception:
        return None

    nyquist = rate / 2.0
    # The shipped statistic, for comparison: fixed band, computed unconditionally
    # here so the two can be compared on the same files.
    fixed_ref = (freq >= 0.45 * nyquist) & (freq <= 0.65 * nyquist)
    fixed_top = (freq >= 0.961 * nyquist) & (freq <= 0.993 * nyquist)
    fixed = (
        float(np.median(magnitude_db[fixed_top]) - np.median(magnitude_db[fixed_ref]))
        if np.any(fixed_top) and np.any(fixed_ref)
        else float("nan")
    )

    return {
        "path": Path(path).name,
        "rate": rate,
        "cutoff": cutoff,
        "fixed_residual": fixed,
        "rel_residual": relative_residual(magnitude_db, freq, cutoff, rate),
    }


def auc(fake: np.ndarray, genuine: np.ndarray) -> float:
    """Mann-Whitney AUC on the DISCRIMINATING direction (lower residual = faker)."""
    fake = fake[np.isfinite(fake)]
    genuine = genuine[np.isfinite(genuine)]
    if not len(fake) or not len(genuine):
        return float("nan")
    # A transcode's floor is MORE negative, so negate to keep "higher = faker".
    fake, genuine = -fake, -genuine
    values = np.concatenate([fake, genuine])
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.arange(1, len(order) + 1)
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    rank_sum = ranks[: len(fake)].sum()
    return float((rank_sum - len(fake) * (len(fake) + 1) / 2) / (len(fake) * len(genuine)))


ARMS = {
    "genuine": ["C:/Users/loutr/audit_corpus/authentic/*.flac",
                "C:/Users/loutr/wild_authentic/**/*.flac"],
    "mp3_320": ["C:/Users/loutr/audit_corpus/fake/mp3_320/*.flac"],
    "mp3_V0": ["C:/Users/loutr/audit_corpus/fake/mp3_V0/*.flac"],
    "aac_ff320": ["C:/Users/loutr/audit_corpus/fake/aac_ff320/*.flac"],
    "aacmf_256": ["C:/Users/loutr/audit_corpus/fake/aacmf_256/*.flac"],
}

GUARD1 = 0.95


def collect(limit_genuine: int, limit_arm: int) -> List[dict]:
    rows: List[dict] = []
    for arm, patterns in ARMS.items():
        limit = limit_genuine if arm == "genuine" else limit_arm
        paths: List[str] = []
        for pattern in patterns:
            found = sorted(glob.glob(pattern, recursive="**" in pattern))
            paths.extend(found[: limit // len(patterns) + 1])
        seen = 0
        for path in paths:
            if seen >= limit:
                break
            row = measure(path)
            if row is None:
                continue
            row["arm"] = arm
            rows.append(row)
            seen += 1
        print(f"{arm}: {seen} mesures", flush=True)
    return rows


def report(rows: List[dict]) -> None:
    """Separation in the region the guards currently own outright."""
    print("\n" + "=" * 74)
    print("LA ZONE QUE PERSONNE NE REGARDE : cutoff >= 0.95 * Nyquist")
    print("=" * 74)

    def zone(arm: str) -> List[dict]:
        return [r for r in rows if r["arm"] == arm and r["cutoff"] >= GUARD1 * r["rate"] / 2]

    print(f"\n{'arm':12}{'n zone':>8}{'rel fini':>10}{'rel med':>10}"
          f"{'rel p05':>10}{'rel p95':>10}{'cut med':>10}")
    stats = {}
    for arm in ARMS:
        rowset = zone(arm)
        if not rowset:
            print(f"{arm:12}{0:>8}")
            continue
        rel = np.array([r["rel_residual"] for r in rowset], dtype=float)
        finite = rel[np.isfinite(rel)]
        cut = np.array([r["cutoff"] for r in rowset], dtype=float)
        stats[arm] = finite
        if finite.size:
            print(f"{arm:12}{len(rowset):>8}{finite.size:>10}"
                  f"{np.median(finite):>10.1f}{np.percentile(finite, 5):>10.1f}"
                  f"{np.percentile(finite, 95):>10.1f}{np.median(cut):>10.0f}")
        else:
            print(f"{arm:12}{len(rowset):>8}{0:>10}   (toutes abstentions)")

    if "genuine" in stats and stats["genuine"].size:
        print(f"\n{'arm':12}{'AUC vs genuine (zone)':>26}")
        for arm in ARMS:
            if arm == "genuine" or arm not in stats or not stats[arm].size:
                continue
            print(f"{arm:12}{auc(stats[arm], stats['genuine']):>26.2f}")

    print("\n--- taux d'abstention, tous fichiers ---")
    for arm in ARMS:
        rowset = [r for r in rows if r["arm"] == arm]
        if not rowset:
            continue
        rel = np.array([r["rel_residual"] for r in rowset], dtype=float)
        fixed = np.array([r["fixed_residual"] for r in rowset], dtype=float)
        print(f"{arm:12} n={len(rowset):3d}  relatif fini {int(np.isfinite(rel).sum()):3d}"
              f"   fixe fini {int(np.isfinite(fixed).sum()):3d}")

    print("\nLecture : une AUC elevee ET un plancher authentique nettement au-dessus du")
    print("plancher transcode autorisent a remplacer le garde-fou par l'instrument.")
    print("Une AUC proche de 0,5 dit que la zone doit rester fermee.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genuine", type=int, default=120)
    parser.add_argument("--arm", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("ml/nearnyq_residual.csv"))
    args = parser.parse_args(argv)

    rows = collect(args.genuine, args.arm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["arm", "path", "rate", "cutoff", "fixed_residual", "rel_residual"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} lignes -> {args.out}", flush=True)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
