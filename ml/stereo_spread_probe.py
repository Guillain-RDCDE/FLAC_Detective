"""Rule 15 position probe (ml/stereo_spread_probe.py): the witness read at the START vs SPREAD.

Written for ml/exchange/STEREO_SPREAD_REGISTRATION_2026-09-25.md. Usage:
    python ml/stereo_spread_probe.py <src dir of the engine> out.csv label=folder [...]


The shipped ``stereo_image._spectra`` takes the first MAX_FRAMES (200) frames
from sample 0 â€” ~4.7 s at 44.1 kHz â€” of whatever audio it is handed, and the
engine hands it the whole file. So on a full track the witness reads the intro.

For every file this computes ``side_dead_run`` twice on the SAME audio:
  start   the shipped function, unchanged
  spread  the same statistic with the 200 frames spread evenly over the file
          (stride = max(HOP, usable // 200) rounded to HOP, as mdct.py does)
Offline, read-only. Output CSV: file, label, seconds, start, spread, ratio.
"""
from __future__ import annotations

import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

SRC = sys.argv[1]
sys.path.insert(0, SRC)
from flac_detective.analysis.new_scoring import stereo_image as si  # noqa: E402


def spectra_spread(signal, rate):
    window = np.hanning(si.FFT_SIZE).astype(np.float32)
    freqs = np.fft.rfftfreq(si.FFT_SIZE, 1.0 / rate)
    band = np.where(freqs >= si.BAND_LO_HZ)[0]
    usable = len(signal) - si.FFT_SIZE
    if usable <= 0:
        return np.empty((0, 0))
    stride = max(si.HOP, (usable // si.MAX_FRAMES) // si.HOP * si.HOP)
    frames = []
    for start in range(0, usable, stride):
        block = signal[start: start + si.FFT_SIZE] * window
        frames.append(np.abs(np.fft.rfft(block))[band])
        if len(frames) >= si.MAX_FRAMES:
            break
    return np.asarray(frames) if frames else np.empty((0, 0))


def run_spread(data, rate):
    left = data[:, 0].astype(np.float64)
    right = data[:, 1].astype(np.float64)
    mid_raw = ((left + right) / 2.0).astype(np.float32)
    side_raw = (left - right).astype(np.float32)
    mid_energy = float(np.mean(mid_raw.astype(np.float64) ** 2))
    ratio = 0.0 if mid_energy <= 0 else float(np.mean(side_raw.astype(np.float64) ** 2) / mid_energy)
    if ratio < si.MONO_GATE:
        return float("nan")
    side_spec = spectra_spread(si._restore(side_raw), rate)
    mid_spec = spectra_spread(si._restore(mid_raw), rate)
    if side_spec.shape != mid_spec.shape or len(side_spec) < si.MIN_FRAMES:
        return float("nan")
    dead = (mid_spec < si.UNION_DEAD) | (side_spec < si.UNION_DEAD)
    per_frame = []
    for row in dead:
        runs = si._interior_runs(row)
        per_frame.append(float(runs.mean()) if runs.size else 0.0)
    return float(np.median(per_frame)) if per_frame else 0.0


def probe(job):
    path, label = job
    try:
        data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "label": label, "error": str(e)}
    if data.shape[1] < 2:
        return {"file": path.name, "label": label, "seconds": round(len(data) / rate, 1),
                "start": "nan", "spread": "nan", "ratio": 0.0}
    start, ratio = si.side_dead_run(data, int(rate))
    spread = run_spread(data, int(rate))
    return {"file": path.name, "label": label, "seconds": round(len(data) / rate, 1),
            "start": round(start, 3) if np.isfinite(start) else "nan",
            "spread": round(spread, 3) if np.isfinite(spread) else "nan",
            "ratio": ratio}


def main():
    out = Path(sys.argv[2])
    jobs = []
    for spec in sys.argv[3:]:
        label, folder = spec.split("=", 1)
        for p in sorted(Path(folder).rglob("*")):
            if p.suffix.lower() in (".flac", ".wav", ".aif", ".aiff"):
                jobs.append((p, label))
    with ProcessPoolExecutor(2) as ex:
        rows = list(ex.map(probe, jobs, chunksize=4))
    with out.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["file", "label", "seconds", "start", "spread", "ratio", "error"])
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()

