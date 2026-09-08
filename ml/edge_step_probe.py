"""Edge-shape probe for the Rule 1 wall gate (WALL_GATE_REGISTRATION_2026-09-08).

For every file of the given corpora, reads what ``analyze_spectrum`` reads (the
same three windows, the same Hann-windowed FFT) and writes, per window, the
detected cutoff and the 250 Hz cell profile from 14 kHz to Nyquist, each cell
expressed relative to the 10-14 kHz reference median, exactly as
``detect_cutoff`` sees it. Every steepness statistic can then be computed
offline from the same rows, and the bar is set on a table that stays on disk.

Two readings are derived on the spot, for the window that produced the
minimum cutoff (the one Rule 1 acts on):

* ``edge_step_db`` — the largest fall over two adjacent cells (500 Hz) in the
  zone [cutoff - 1 kHz, cutoff + 1 kHz). A codec low-pass falls 20-40 dB
  there; a mastering slope of 6-8 dB/kHz falls 3-5 dB. This is the statistic
  ``spectrum.edge_step_db`` ships.
* ``width_hz`` — ``detect_cutoff_detailed``'s transition width, kept for the
  record: it reads 0 Hz on a slope that is already 30 dB down at the edge
  (the reporter's file), which is why it is not the instrument.

No verdicts: this is the instrument, not the rule.

Usage::

    python ml/edge_step_probe.py OUT.csv LABEL=DIR [LABEL=DIR ...] [--duration 30]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq

from flac_detective.analysis.spectrum import (
    cell_profile_db,
    detect_cutoff_detailed,
    edge_step_db,
)


def windows(total: float, duration: float):
    n = 3 if total > 90 else 1
    d = min(duration, total / n)
    for i in range(n):
        start = max(0.0, (total / (n + 1)) * (i + 1) - d / 2)
        yield start, d


def probe(path: Path, duration: float) -> dict:
    audio, sr = sf.read(path, dtype="float32")
    if audio.ndim == 1:
        audio = audio[:, None]
    total = len(audio) / sr
    cutoffs, widths, profiles, steps = [], [], [], []
    for start, d in windows(total, duration):
        seg = audio[int(start * sr) : int(start * sr) + int(d * sr)].mean(axis=1)
        w = np.hanning(len(seg))
        mag_db = 20 * np.log10(np.abs(rfft(seg * w)) + 1e-10)
        freq = rfftfreq(len(seg), 1 / sr)
        r = detect_cutoff_detailed(freq, mag_db, sr)
        cutoffs.append(r.cutoff_hz)
        widths.append(r.width_hz if r.found else float("nan"))
        profiles.append(cell_profile_db(freq, mag_db, sr)[1])
        steps.append(edge_step_db(freq, mag_db, r.cutoff_hz, sr))
    fin = min(cutoffs)
    idx = cutoffs.index(fin)
    row = {
        "sr": sr,
        "cutoff_min": fin,
        "cutoffs": "|".join(f"{c:.0f}" for c in cutoffs),
        "width_at_min": widths[idx],
        "edge_step_db": steps[idx],
        "duration": total,
        "windows": len(cutoffs),
    }
    for i in range(3):
        row[f"profile{i+1}"] = "|".join(f"{v:.1f}" for v in profiles[i]) if i < len(profiles) else ""
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("corpora", nargs="+", help="LABEL=DIR")
    ap.add_argument("--duration", type=float, default=30.0)
    a = ap.parse_args()
    fields = ["label", "file", "sr", "cutoff_min", "cutoffs", "width_at_min", "edge_step_db",
              "duration", "windows", "profile1", "profile2", "profile3"]
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        for spec in a.corpora:
            label, _, d = spec.partition("=")
            files = sorted(Path(d).glob("*.flac"))
            for i, f in enumerate(files, 1):
                try:
                    row = probe(f, a.duration)
                except Exception as e:  # noqa: BLE001 - a probe reports, it does not die
                    row = {"cutoff_min": float("nan"), "cutoffs": f"ERR {e}"}
                row.update(label=label, file=f.name)
                wr.writerow(row)
                fh.flush()
                print(f"{label} {i}/{len(files)} {f.name[:50]} cutoff={row.get('cutoff_min')} "
                      f"step={row.get('edge_step_db')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
