#!/usr/bin/env python3
"""Choose REL_FLOOR for Rule 15's relative dead test — the sweep, procedure first.

The rule for picking the value was written before this ran, in
``ml/exchange/R15_RELATIVE_DEAD_REGISTRATION_2026-08-31.md``: the **largest**
``REL_FLOOR`` whose arm-vs-genuine AUC stays within 0.03 of the absolute test's,
on the same files. If none clears it, the relative test is refused.

Three populations, none of which is set A:

    audit_corpus/authentic              the null
    audit_corpus/fake/{4 arms}          the signal, and the witness's domain
    44 parked sources + 14 kHz roll-off the artefact this exists to remove

Spectra are computed once per file and every candidate floor is evaluated on
them, so the comparison is between constants and not between runs.
"""

from __future__ import annotations

import glob
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flac_detective.analysis.new_scoring import stereo_image as si  # noqa: E402
from v3_build_set_a import BAND_LIMIT_FILTER  # noqa: E402

FLOORS = [0.02, 0.05, 0.10, 0.20, 0.30]
ARMS = ("mp3_320", "aac_ff256", "opus_256", "vorbis_q8")
N_PER_POP = 40


def spectra(path: Path) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """(side, mid) magnitude spectra above 10 kHz, or None if the witness abstains."""
    data, rate = sf.read(str(path), dtype="float32")
    if data.ndim < 2 or data.shape[1] < 2:
        return None
    left = data[:, 0].astype(np.float64)
    right = data[:, 1].astype(np.float64)
    mid = ((left + right) / 2.0).astype(np.float32)
    side = (left - right).astype(np.float32)
    mid_energy = float(np.mean(mid.astype(np.float64) ** 2))
    ratio = 0.0 if mid_energy <= 0 else float(np.mean(side.astype(np.float64) ** 2) / mid_energy)
    if ratio < si.MONO_GATE:
        return None
    side_spec = si._spectra(si._restore(side), int(rate))
    mid_spec = si._spectra(si._restore(mid), int(rate))
    if side_spec.shape != mid_spec.shape or len(side_spec) < si.MIN_FRAMES:
        return None
    return side_spec, mid_spec


def stat_absolute(side_spec: np.ndarray, mid_spec: np.ndarray) -> float:
    """The shipped statistic, recomputed here so both are read off the same spectra."""
    dead = (mid_spec < si.UNION_DEAD) | (side_spec < si.UNION_DEAD)
    per_frame = []
    for row in dead:
        runs = si._interior_runs(row)
        per_frame.append(float(runs.mean()) if runs.size else 0.0)
    return float(np.median(per_frame)) if per_frame else 0.0


def stat_relative(side_spec: np.ndarray, floor: float) -> float:
    """Dead relative to the file's OWN side level in the same frame."""
    per_frame = []
    for row in side_spec:
        reference = float(np.median(row))
        if reference <= 0:
            continue
        runs = si._interior_runs(row < floor * reference)
        per_frame.append(float(runs.mean()) if runs.size else 0.0)
    return float(np.median(per_frame)) if per_frame else float("nan")


def auc(pos: List[float], neg: List[float]) -> float:
    """P(a random arm reads HIGHER than a random genuine), draws at half."""
    p = np.array([x for x in pos if np.isfinite(x)])[:, None]
    n = np.array([x for x in neg if np.isfinite(x)])[None, :]
    if p.size == 0 or n.size == 0:
        return float("nan")
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def main() -> int:
    pops: Dict[str, List[str]] = {
        "genuine": sorted(glob.glob(r"C:\Users\loutr\audit_corpus\authentic\*.flac"))[:N_PER_POP]
    }
    for arm in ARMS:
        pops[arm] = sorted(glob.glob(rf"C:\Users\loutr\audit_corpus\fake\{arm}\*.flac"))[:N_PER_POP]
    parked = sorted(Path(r"C:\Users\loutr\fd-v3-setA\corpus\_unused").glob("*.flac"))
    parked += sorted(Path(r"C:\Users\loutr\fd-v3-setA\corpus\_dup_series").glob("*.flac"))
    pops["bandlimited"] = [str(p) for p in parked]

    values: Dict[str, Dict[object, List[float]]] = {
        name: {"abs": [], **{f: [] for f in FLOORS}} for name in pops
    }

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for name, files in pops.items():
            for path_str in files:
                path = Path(path_str)
                if name == "bandlimited":  # the same roll-off the stratum uses
                    filtered = work / "bl.flac"
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-y",
                            "-i",
                            str(path),
                            "-map",
                            "0:a:0",
                            "-map_metadata",
                            "-1",
                            "-af",
                            BAND_LIMIT_FILTER,
                            "-ar",
                            "44100",
                            "-sample_fmt",
                            "s16",
                            "-c:a",
                            "flac",
                            str(filtered),
                        ],
                        check=True,
                        capture_output=True,
                    )
                    path = filtered
                got = spectra(path)
                if got is None:
                    continue
                side_spec, mid_spec = got
                values[name]["abs"].append(stat_absolute(side_spec, mid_spec))
                for floor in FLOORS:
                    values[name][floor].append(stat_relative(side_spec, floor))
            print(f"  {name}: {len(values[name]['abs'])} fichiers lus", flush=True)

    print()
    header = f"{'variante':>10s} {'AUC bras/genuine':>17s} {'med genuine':>12s} {'med bras':>9s}"
    print(header + f" {'med band-lim':>13s} {'band-lim > 2.0':>15s}")
    baseline = auc(sum((values[a]["abs"] for a in ARMS), []), values["genuine"]["abs"])
    rows = []
    for key in ["abs"] + FLOORS:
        arms_vals = sum((values[a][key] for a in ARMS), [])
        a = auc(arms_vals, values["genuine"][key])
        med_g = float(np.nanmedian(values["genuine"][key]))
        med_a = float(np.nanmedian(arms_vals))
        med_b = float(np.nanmedian(values["bandlimited"][key]))
        over = sum(1 for v in values["bandlimited"][key] if np.isfinite(v) and v > 2.0)
        label = "absolu" if key == "abs" else f"rel {key}"
        print(
            f"{label:>10s} {a:17.3f} {med_g:12.2f} {med_a:9.2f} {med_b:13.2f} "
            f"{over:>10d}/{len(values['bandlimited'][key])}"
        )
        if key != "abs":
            rows.append((key, a))

    print()
    eligible = [(f, a) for f, a in rows if np.isfinite(a) and a >= baseline - 0.03]
    if not eligible:
        print("AUCUN candidat ne passe la garde AUC (-0.03) : le test relatif est REFUSE")
        return 1
    chosen = max(eligible, key=lambda fa: fa[0])
    print(f"garde AUC: base {baseline:.3f}, plancher {baseline - 0.03:.3f}")
    print(f"candidats retenus: {[(f, round(a, 3)) for f, a in eligible]}")
    print(f"CHOISI (le plus grand): REL_FLOOR = {chosen[0]} (AUC {chosen[1]:.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
