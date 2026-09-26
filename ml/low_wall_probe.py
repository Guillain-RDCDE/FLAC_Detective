"""Low-wall probe (ml/low_wall_probe.py): per-window profiles for offline threshold exploration.

Written for ml/exchange/LOW_WALL_REGISTRATION_2026-09-25.md. Usage:
    python ml/low_wall_probe.py out.jsonl label=folder [label=folder ...]


Same windows as analyze_spectrum. 250 Hz cells of the absolute PSD (median per
cell) from 1 kHz to 0.993 Nyquist. For each boundary f in [2 kHz, 14 kHz]:
  step(f) = mean(cells[f-500, f)) - mean(cells[f, f+500))      local sharpness
  deep(f) = mean(cells[f-500, f)) - p90(cells[f+1000, top))     what is left above
Output JSON lines: file, label, win, rate, cutoff, found_edge, fs, step, deep, top_abs.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from flac_detective.analysis.spectrum import detect_cutoff  # noqa: E402

CELL = 250
POST_TOP = 16000


def profiles(freqs, psd, rate):
    nyq = rate / 2.0
    edges = np.arange(1000, 0.993 * nyq - CELL + 1, CELL)
    idx = np.searchsorted(freqs, edges)
    idx_hi = np.searchsorted(freqs, edges + CELL)
    cells = np.array([np.median(psd[a:b]) if b > a else np.nan for a, b in zip(idx, idx_hi)])
    fs, steps, deeps = [], [], []
    for f in range(2000, 14001, CELL):
        i = int((f - 1000) // CELL)
        if i + 4 >= len(cells):
            break
        pre = float(np.mean(cells[i - 2:i]))
        steps.append(round(pre - float(np.mean(cells[i:i + 2])), 1))
        hi = min(len(cells), int((POST_TOP - 1000) // CELL))
        if i + 4 >= hi:
            break
        deeps.append(round(pre - float(np.percentile(cells[i + 4:hi], 90)), 1))
        fs.append(f)
    return fs, steps, deeps, float(np.median(cells[-8:]))


def probe(path_label):
    path, label = path_label
    out = []
    try:
        data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception as e:  # noqa: BLE001
        return [{"file": path.name, "label": label, "error": str(e)}]
    total = len(data) / rate
    n = 3 if total > 90 else 1
    dur = min(30.0, total / n)
    for i in range(n):
        start = max(0.0, total / (n + 1) * (i + 1) - dur / 2)
        seg = data[int(start * rate): int(start * rate) + int(dur * rate)].mean(axis=1)
        if len(seg) < 4096:
            continue
        w = np.hanning(len(seg))
        mag = np.abs(rfft(seg * w))
        freqs = rfftfreq(len(seg), 1 / rate)
        cutoff = float(detect_cutoff(freqs, 20 * np.log10(mag + 1e-10), rate))
        psd = 10 * np.log10(2 * mag**2 / (rate * np.sum(w**2)) + 1e-30)
        fs, steps, deeps, top = profiles(freqs, psd, rate)
        out.append({"file": path.name, "path": str(path), "label": label, "win": i,
                    "rate": rate, "cutoff": cutoff, "found_edge": int(cutoff < 0.999 * rate / 2),
                    "fs": fs, "step": steps, "deep": deeps, "top_abs": round(top, 1)})
    return out


def main():
    out = Path(sys.argv[1])
    jobs = []
    for spec in sys.argv[2:]:
        label, folder = spec.split("=", 1)
        for p in sorted(Path(folder).rglob("*")):
            if p.suffix.lower() in (".flac", ".wav", ".aif", ".aiff"):
                jobs.append((p, label))
    n = 0
    with ProcessPoolExecutor(3) as ex, out.open("w", encoding="utf-8") as f:
        for rs in ex.map(probe, jobs, chunksize=4):
            for r in rs:
                f.write(json.dumps(r) + "\n")
                n += 1
    print(f"{n} rows from {len(jobs)} files -> {out}")


if __name__ == "__main__":
    main()
