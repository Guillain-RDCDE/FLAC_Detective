#!/usr/bin/env python3
"""First controlled execution of Provir's era encoders, and one era-paired cell.

Execution protocol, declared before anything runs
--------------------------------------------------
Provir's encoder collection was received 2026-08-21 and verified 174/174
against his own SHA256SUMS before anything here. This file performs the FIRST
executions: CLI encoders only, on synthetic input, in a temporary working
directory, output validated by decoding it back with our own ffmpeg. The
binaries executed here are exactly the manifest-verified bytes — lame3.92's
lame.exe is byte-identical to the pinned arm-1 exhibit key (cb2cdfde7b170d90).

The cell, and its registered predictions
-----------------------------------------
His era bench says the idem tell is VERSION-LOCKED: a 3.100-paired probe reads
3.90-3.93-era MP3s as lawful-like. This runs the mirror in OUR hands, one cell:
a synthetic source is transcoded through HIS lame3.92, then measured by two
probes — our libmp3lame 3.100 (the shipped ml/mp3_idem_probe.py instrument) and
an era-PAIRED probe that re-encodes through the same lame3.92 binary.

    E1  The era-paired probe reads the 3.92 transcode at least 1.0 dB CLOSER
        to the fixed point than the 3.100 probe reads it (R_paired < R_3100 - 1).
    E2  Both probes read the FRESH source far from their fixed points
        (R > 2.0 dB each) — the ordering control.

Being wrong on E1 would say generation-pairing does not recover the tell and
his wild bins measured something else. Results appended below.
--------------------------------------------------------------------------------
E-SERIES RESULTS (2026-08-21, cell 1, seed 20260820)

    smoke        HELD    lame3.92 executed, banner "LAME version 3.92 MMX
                         (http://www.mp3dev.org/)", output decodes.
    E1           FAILED  as registered — and the registered premise was wrong,
                         which is part of the result. Measured:

                                          3.100 probe   3.92-paired
                     fresh source              9.44         21.95
                     lame3.92 transcode        5.63          7.79

                         Absolute R is PROBE-RELATIVE: lame3.92's second pass
                         converges faster to its own fixed point (smaller d2),
                         inflating every R it produces. Comparing raw R across
                         probes was a category error. Within each probe's own
                         scale the tell is not merely present under pairing, it
                         is LARGER: fresh-vs-transcode contrast is 14.16 dB for
                         the era-paired probe against 3.81 dB for 3.100.
    E2           HELD    both probes read fresh far from their fixed points.

E1-PRIME, registered before cell 2 (the revision must not be graded on the
data that suggested it):

    E1'  On a NEW excerpt (different seed, different partials), the
         within-probe contrast R(fresh) - R(lame3.92 transcode) is at least
         3.0 dB larger for the era-paired probe than for the 3.100 probe.

CELL 2 RESULTS
(not yet run)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mp3_idem_probe import _tonal_mix, dist, mp3_idem, require_ffmpeg  # noqa: E402

LAME392 = Path(r"C:\Users\loutr\provir_encoders\Encoders\LAME\lame3.92\lame.exe")
RATE = 44100


def lame392_roundtrip(audio: np.ndarray, work: Path, ffmpeg: str) -> Optional[np.ndarray]:
    """decode(lame3.92 -b 320 (audio)) — files, never pipes, per the standing trap."""
    src = work / "in.wav"
    enc = work / "out.mp3"
    dec = work / "dec.wav"
    sf.write(str(src), audio, RATE, subtype="PCM_16")
    r = subprocess.run([str(LAME392), "-b", "320", str(src), str(enc)],
                       capture_output=True, text=True, timeout=120, cwd=str(work))
    if r.returncode != 0 or not enc.exists() or enc.stat().st_size < 1000:
        print(f"  lame3.92 failed: rc={r.returncode} {r.stderr[-200:]}")
        return None
    banner = [ln for ln in (r.stderr or r.stdout).splitlines() if "LAME" in ln][:1]
    print(f"  lame3.92 banner: {banner[0].strip() if banner else '(none printed)'}")
    r2 = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                         "-i", str(enc), str(dec)], capture_output=True, text=True)
    if r2.returncode != 0:
        return None
    out, rate = sf.read(str(dec), dtype="float32")
    return out if rate == RATE else None


def paired_idem(audio: np.ndarray, ffmpeg: str) -> float:
    """R through two sequential lame3.92 passes — the era-paired probe."""
    with tempfile.TemporaryDirectory() as tmp1:
        b = lame392_roundtrip(audio, Path(tmp1), ffmpeg)
    if b is None:
        return float("nan")
    with tempfile.TemporaryDirectory() as tmp2:
        c = lame392_roundtrip(b, Path(tmp2), ffmpeg)
    if c is None:
        return float("nan")
    d1, _ = dist(audio, b, RATE)
    d2, _ = dist(b, c, RATE)
    if not np.isfinite(d1) or not np.isfinite(d2) or d2 <= 0:
        return float("nan")
    return float(20.0 * np.log10(d1 / d2))


def _tonal_mix_cell2(seconds: float = 30.0) -> np.ndarray:
    """A different excerpt for E1-prime: new seed, new partials, noise bursts."""
    rng = np.random.default_rng(20260821)
    t = np.arange(int(RATE * seconds)) / RATE
    x = np.zeros_like(t)
    for f0, amp in ((196, 0.14), (587, 0.10), (1760, 0.07), (5274, 0.04), (11000, 0.02)):
        x += amp * np.sin(2 * np.pi * f0 * t + rng.uniform(0, 6.28))
    x += 0.03 * rng.standard_normal(len(t))
    bursts = (rng.random(len(t)) < 0.0005).astype(np.float32)
    x += 0.25 * np.convolve(bursts, np.hanning(64), mode="same")
    env = 0.5 * (1 + np.sin(2 * np.pi * 0.53 * t + 1.0))
    return (x * env).astype(np.float32)


def run_cell(fresh: np.ndarray, ffmpeg: str, label: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        transcode392 = lame392_roundtrip(fresh, Path(tmp), ffmpeg)
    if transcode392 is None:
        raise SystemExit("lame3.92 produced no decodable output")

    r_fresh_3100, _, _ = mp3_idem(fresh, RATE, ffmpeg)
    r_fresh_392 = paired_idem(fresh, ffmpeg)
    r_t392_3100, _, _ = mp3_idem(transcode392, RATE, ffmpeg)
    r_t392_392 = paired_idem(transcode392, ffmpeg)

    print(f"\n[{label}]")
    print(f"{'':24}{'3.100 probe':>13}{'3.92-paired':>13}")
    print(f"{'fresh source':24}{r_fresh_3100:>13.2f}{r_fresh_392:>13.2f}")
    print(f"{'lame3.92 transcode':24}{r_t392_3100:>13.2f}{r_t392_392:>13.2f}")

    contrast_3100 = r_fresh_3100 - r_t392_3100
    contrast_392 = r_fresh_392 - r_t392_392
    print(f"{'within-probe contrast':24}{contrast_3100:>13.2f}{contrast_392:>13.2f}")
    e1p = np.isfinite(contrast_392) and np.isfinite(contrast_3100) \
        and contrast_392 >= contrast_3100 + 3.0
    print(f"E1'  paired contrast >= 3.100 contrast + 3 dB: "
          f"{'HELD' if e1p else 'FAILED'}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cell2", action="store_true",
                   help="run the E1-prime cell on the fresh excerpt")
    args = p.parse_args(argv)
    if not LAME392.exists():
        raise SystemExit(f"missing {LAME392}")
    ffmpeg = require_ffmpeg()

    if args.cell2:
        run_cell(_tonal_mix_cell2(30.0), ffmpeg, "cell 2, seed 20260821")
        return 0

    print("smoke: encoding synthetic source through lame3.92 (first execution)")
    fresh = _tonal_mix(30.0)
    with tempfile.TemporaryDirectory() as tmp:
        transcode392 = lame392_roundtrip(fresh, Path(tmp), ffmpeg)
    if transcode392 is None:
        raise SystemExit("smoke FAILED: lame3.92 produced no decodable output")
    print("  smoke OK: output decodes\n")

    r_fresh_3100, _, _ = mp3_idem(fresh, RATE, ffmpeg)
    r_fresh_392 = paired_idem(fresh, ffmpeg)
    r_t392_3100, _, _ = mp3_idem(transcode392, RATE, ffmpeg)
    r_t392_392 = paired_idem(transcode392, ffmpeg)

    print(f"{'':24}{'3.100 probe':>13}{'3.92-paired':>13}")
    print(f"{'fresh source':24}{r_fresh_3100:>13.2f}{r_fresh_392:>13.2f}")
    print(f"{'lame3.92 transcode':24}{r_t392_3100:>13.2f}{r_t392_392:>13.2f}")

    e1 = np.isfinite(r_t392_392) and np.isfinite(r_t392_3100) \
        and r_t392_392 < r_t392_3100 - 1.0
    e2 = r_fresh_3100 > 2.0 and r_fresh_392 > 2.0
    print(f"\nE1  era pairing recovers the tell (paired < 3.100 - 1 dB): "
          f"{'HELD' if e1 else 'FAILED'}")
    print(f"E2  both probes read fresh high (> 2 dB): {'HELD' if e2 else 'FAILED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
