"""Trace Rule 1, gate by gate, with counterfactuals for gate A (ml/rule1_gate_trace.py).

Written for ml/exchange/GATE_A_DEPTH_REGISTRATION_2026-09-26.md. Usage:
    python ml/rule1_gate_trace.py out.csv label=folder [label=list.txt ...]


Same readings the engine takes (analyze_spectrum at 30 s; the FLAC-equivalent
size of the audio, taken only when a cell is reached), then the gates of
apply_rule_1_mp3_bitrate in their order. Three versions of the order:
  now     the shipped gates
  noA     gate A (cutoff wander > CUTOFF_VARIANCE_THRESHOLD) removed
  Adepth  gate A yields to depth (skipped when the floor above the edge is
          digital silence, as gate D and the container window already do)
Offline, read-only. `now` is checked against apply_rule_1_mp3_bitrate itself.
"""
from __future__ import annotations

import csv
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import soundfile as sf

import flac_detective
from flac_detective.analysis.audio_formats import flac_equivalent_size
from flac_detective.analysis.new_scoring.bitrate import estimate_mp3_bitrate
from flac_detective.analysis.new_scoring.constants import CUTOFF_VARIANCE_THRESHOLD
from flac_detective.analysis.new_scoring.rules.spectral import (
    HIGH_QUALITY_CUTOFF_THRESHOLD,
    NEARNYQ_FLOOR_DB,
    apply_rule_1_mp3_bitrate,
    edge_is_a_slope,
    floor_is_digital_silence,
)
from flac_detective.analysis.spectrum import analyze_spectrum, is_low_wall_reading

STEP_BAR = float(__import__("os").environ.get("FD_STEP_BAR", "15"))

WINDOWS = {128: (400, 550), 160: (450, 650), 192: (500, 750), 224: (550, 800),
           256: (600, 850), 320: (700, 1050)}


def gates(v, variant):
    cutoff, std, step, floor, resid, sr, kbps_fn = v
    nyq = sr / 2.0
    if is_low_wall_reading(cutoff):
        return "low_wall"
    if cutoff >= 0.95 * nyq:
        return "nyquist"
    if cutoff == 20000.0 and not ((not math.isnan(resid)) and resid <= NEARNYQ_FLOOR_DB):
        return "gate_B_20k"
    if cutoff > HIGH_QUALITY_CUTOFF_THRESHOLD:
        return "hq"
    silent_above = floor_is_digital_silence(floor, cutoff)
    if std > CUTOFF_VARIANCE_THRESHOLD:
        hard = (not math.isnan(step)) and step >= STEP_BAR
        if (
            variant == "now"
            or (variant == "Adepth" and silent_above is False)
            or (variant == "Astep" and silent_above is False and hard is False)
        ):
            return "gate_A_wander"
    if edge_is_a_slope(step, cutoff, floor):
        return "gate_D_slope"
    cell = estimate_mp3_bitrate(cutoff)
    if cell == 0:
        return "no_cell"
    if cell == 320 and cutoff >= 0.94 * nyq:
        return "320_near_nyq"
    kbps = kbps_fn()
    lo, hi = WINDOWS[cell]
    pcm = kbps >= 0.90 * (sr * 32.0 / 1000.0) and (not math.isnan(resid)) and resid <= NEARNYQ_FLOOR_DB
    inwin = lo <= kbps <= hi
    if not (pcm or silent_above or inwin):
        return "window_low" if kbps < lo else "window_high"
    if cell == 320 and not math.isnan(resid) and resid > NEARNYQ_FLOOR_DB:
        return "320_residual"
    return "FIRES"


def trace(job):
    path, label = job
    try:
        info = sf.info(str(path))
        sr, dur = info.samplerate, info.duration
        cutoff, energy, std, resid, step, floor = analyze_spectrum(path, 30.0)
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "label": label, "now": f"ERROR {e}"}
    memo = {}

    def kbps_fn():
        if "k" not in memo:
            size = flac_equivalent_size(path)
            memo["k"] = (size * 8) / (dur * 1000) if size and dur > 0 else float("nan")
        return memo["k"]

    v = (cutoff, std, step, floor, resid, sr, kbps_fn)
    row = {"file": path.name, "path": str(path), "label": label, "seconds": round(dur, 1),
           "cutoff": cutoff, "std": round(std, 1), "step": round(step, 1),
           "floor": round(floor, 1), "resid": round(resid, 1)}
    for variant in ("now", "noA", "Adepth", "Astep"):
        row[variant] = gates(v, variant)
    row["kbps"] = round(memo["k"], 1) if "k" in memo else ""
    if row["now"] in ("FIRES", "window_low", "window_high", "320_residual"):
        (score, _r), _b = apply_rule_1_mp3_bitrate(cutoff, kbps_fn(), std, sr, energy, resid, step, floor)
        if (score == 50) != (row["now"] == "FIRES"):
            row["now"] += "_MISMATCH"
    return row


def main():
    print("engine", flac_detective.__version__, flac_detective.__file__, flush=True)
    out = Path(sys.argv[1])
    jobs = []
    for spec in sys.argv[2:]:
        label, src = spec.split("=", 1)
        p = Path(src)
        if p.suffix == ".txt":
            files = [Path(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            files = sorted(p.rglob("*.flac"))
        jobs += [(f, label) for f in files]
    keys = ["file", "path", "label", "seconds", "cutoff", "std", "step", "floor", "resid",
            "now", "noA", "Adepth", "Astep", "kbps"]
    n = 0
    with ProcessPoolExecutor(3) as ex, out.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        wr.writeheader()
        for row in ex.map(trace, jobs, chunksize=2):
            wr.writerow(row)
            n += 1
            if n % 200 == 0:
                print(n, "/", len(jobs), flush=True)
    print(n, "rows ->", out)


if __name__ == "__main__":
    main()
