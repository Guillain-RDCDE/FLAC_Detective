#!/usr/bin/env python3
"""Max-over-frames vs median-over-frames, re-priced on the population that matters.

The one-choice difference
--------------------------
Provir's DEAD_STRUCTURE_MAXRUN reads 12 of the wild 34; our shipped Rule 15
witness reads 3. His domain answer (2026-08-21) showed the instruments differ in
many ways, but the load-bearing one is a single choice: he MAXIMISES the longest
interior run over frames, we take the MEDIAN of per-frame mean runs. We rejected
the max variant in v1.11.2, on measurement — **measured on direct lab
transcodes** (it lost 5 arms of 6). After the W-series, that rejection carries a
population label it did not have: the median wins on DIRECT transcodes, but on
re-mastered wilds the press noise refills the side channel in *most* frames, and
only a max can catch the one quiet frame where it dips back out.

Not convergence — his instrument keeps its absolute 1e-3 side-only threshold and
its 21.5 Hz bins; this probe keeps OUR mask (union, 3e-4, our 2048 grid) and
varies ONLY the aggregation. He asked that the two engines map the domains side
by side rather than converge, and this is exactly that map.

Registered before the run:

    M1  The max variant, at a bar set at the genuine control's p95, reads at
        least 25 % of the owner-attested 34. (His instrument reads ~35 % of the
        tier; ours differs, so a lower bound, not parity.)
    M2  The shipped median statistic stays at or below 10 % of the 34 over
        RUN_BAR — consistent with the 3/34 the engine actually signaled.
    M3  The eye tier (19) is reported separately, never averaged.

Being wrong on M1 means the aggregation was NOT the load-bearing difference and
the absolute-threshold/side-only geometry is; either answer sharpens the map.
The shipped rule does not move either way — a re-pricing of median vs max on
BOTH populations (direct + wild) is v1.12 material, priced like everything else.

MEASURED 2026-08-21 — BOTH predictions failed, and the failure collapses the
whole wild anatomy into one layer:

    tier               n   med(shipped)  med(max)   AUC shp   AUC max
    genuine           40         1.00        3.0        —        —
    owner-knowledge   34         3.38       37.0     0.97      0.93
    eye               19         3.44       34.0     0.97      0.92

    M1 FAILED (1/34 over the max bar — the genuine max tail is huge, p95 55.5;
    max adds nothing at our geometry). M2 FAILED in the best possible way: the
    SHIPPED median reads 34/34 over RUN_BAR at AUC 0.97.

M2's registration confused "signaled by the engine" with "witness over the
bar". The truth: **the witness roster SEES the wild population almost
perfectly** — the shipped Rule 15 statistic separates owner-attested wilds
from genuine at 0.97 on the same excerpts the engine cleared. What is missing
is not detection, it is POINTS: a zero-point witness may only complete a
corroboration, never initiate one, and the Rule 1 admission gates
(ml/wild53_cliff.py, mechanisms a-c) suppress the very points it would
corroborate. So the wild anatomy reduces to ONE load-bearing layer: repair the
R1 gates on this population and the stereo witness corroborates 34/34
instantly — nothing else in the engine needs to learn anything. That is the
v1.12 campaign's shape, now fully measured. The aggregation question is
CLOSED at our geometry (max loses on both populations); his instrument reads
the tier through a different mechanism (absolute threshold on 16-bit-rounded
side magnitudes), and the two domains stay mapped side by side, un-converged,
as he asked.
"""

from __future__ import annotations

import argparse
import csv
import sys
from glob import glob
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.new_scoring.stereo_image import (  # noqa: E402
    MIN_FRAMES,
    MONO_GATE,
    UNION_DEAD,
    _interior_runs,
    _restore,
    _spectra,
)
from flac_detective.analysis.new_scoring.rules.stereo_seam import RUN_BAR  # noqa: E402
from edge_width_probe import auc  # noqa: E402

WILD = Path(r"C:\Users\loutr\wild53\21-08-26\Original Hardcore The Nu Breed (2004)")
TIERS = {
    "owner-knowledge": ["CD1 Darren Styles", "CD2 Dougal"],
    "eye": ["CD3 Bonus (Mixed by Styles and Dougal)"],
}
GENUINE_GLOB = r"C:\Users\loutr\wild_authentic\*.flac"
EXCERPT_SEC = 30.0


def both_variants(data: np.ndarray, rate: int) -> Tuple[float, float]:
    """(shipped_median, max_variant) from the SAME spectra and mask."""
    if data.ndim < 2 or data.shape[1] < 2:
        return float("nan"), float("nan")
    left = data[:, 0].astype(np.float64)
    right = data[:, 1].astype(np.float64)
    mid_raw = ((left + right) / 2.0).astype(np.float32)
    side_raw = (left - right).astype(np.float32)
    mid_energy = float(np.mean(mid_raw.astype(np.float64) ** 2))
    ratio = (
        0.0 if mid_energy <= 0 else float(np.mean(side_raw.astype(np.float64) ** 2) / mid_energy)
    )
    if ratio < MONO_GATE:
        return float("nan"), float("nan")
    side_spec = _spectra(_restore(side_raw), rate)
    mid_spec = _spectra(_restore(mid_raw), rate)
    if side_spec.shape != mid_spec.shape or len(side_spec) < MIN_FRAMES:
        return float("nan"), float("nan")
    dead = (mid_spec < UNION_DEAD) | (side_spec < UNION_DEAD)
    per_frame_mean: List[float] = []
    per_frame_max: List[float] = []
    for row in dead:
        runs = _interior_runs(row)
        per_frame_mean.append(float(runs.mean()) if runs.size else 0.0)
        per_frame_max.append(float(runs.max()) if runs.size else 0.0)
    shipped = float(np.median(per_frame_mean)) if per_frame_mean else 0.0
    max_var = float(np.max(per_frame_max)) if per_frame_max else 0.0
    return shipped, max_var


def measure(path: Path) -> Optional[dict]:
    try:
        info = sf.info(str(path))
        data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    shipped, max_var = both_variants(data, int(rate))
    if not np.isfinite(shipped):
        return None
    return {"track": path.name, "shipped_median": f"{shipped:.2f}", "max_variant": f"{max_var:.1f}"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genuine", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("ml/wild53_r15max.csv"))
    args = parser.parse_args(argv)

    rows: List[dict] = []
    for tier, dirs in TIERS.items():
        n = 0
        for d in dirs:
            for path in sorted((WILD / d).glob("*.wav")):
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
        writer = csv.DictWriter(fh, fieldnames=["tier", "track", "shipped_median", "max_variant"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} lignes -> {args.out}\n")

    def vals(tier: str, key: str) -> np.ndarray:
        return np.array([float(r[key]) for r in rows if r["tier"] == tier])

    gen_max = vals("genuine", "max_variant")
    gen_med = vals("genuine", "shipped_median")
    print(
        f"{'tier':16}{'n':>4}{'med(shipped)':>14}{'med(max)':>10}" f"{'AUC shp':>9}{'AUC max':>9}"
    )
    for tier in ("genuine", "owner-knowledge", "eye"):
        med = vals(tier, "shipped_median")
        mx = vals(tier, "max_variant")
        if not med.size:
            continue
        a_s = auc(med, gen_med) if tier != "genuine" else float("nan")
        a_m = auc(mx, gen_max) if tier != "genuine" else float("nan")
        print(
            f"{tier:16}{med.size:>4}{np.median(med):>14.2f}{np.median(mx):>10.1f}"
            f"{a_s:>9.2f}{a_m:>9.2f}"
        )

    owner_max = vals("owner-knowledge", "max_variant")
    owner_med = vals("owner-knowledge", "shipped_median")
    eye_max = vals("eye", "max_variant")
    if gen_max.size and owner_max.size:
        bar = float(np.percentile(gen_max, 95))
        k1 = int((owner_max > bar).sum())
        m1 = k1 >= 0.25 * owner_max.size
        k2 = int((owner_med >= RUN_BAR).sum())
        m2 = k2 <= 0.10 * owner_med.size
        print(
            f"\nM1  max variant reads >=25 % of the 34 (bar p95 gen = {bar:.1f}): "
            f"{'HELD' if m1 else 'FAILED'} ({k1}/{owner_max.size})"
        )
        print(
            f"M2  shipped median stays <=10 % over RUN_BAR ({RUN_BAR}): "
            f"{'HELD' if m2 else 'FAILED'} ({k2}/{owner_med.size})"
        )
        if eye_max.size:
            ke = int((eye_max > bar).sum())
            print(f"M3  eye tier, separately: {ke}/{eye_max.size} over the same bar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
