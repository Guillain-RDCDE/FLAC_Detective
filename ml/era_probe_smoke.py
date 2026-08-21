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


def main(argv=None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    if not LAME392.exists():
        raise SystemExit(f"missing {LAME392}")
    ffmpeg = require_ffmpeg()

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
