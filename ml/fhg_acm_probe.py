#!/usr/bin/env python3
"""A Fraunhofer probe in our hands: l3codecp.acm 3.4 as an idem instrument.

Where it comes from (2026-08-22)
---------------------------------
Provir: Windows ships Fraunhofer's PROFESSIONAL MP3 codec (l3codecp.acm 3.4),
unregistered; loaded in-process it is an encoder, and as an idem probe it
self-pairs at 320 with AUC 0.999 on his bench, family- and generation-locked
(LAME-320 arms: 1 of 72 below his lawful minimum). His encoder tool is
archived at ml/exchange/provir-fhg_acm_encode.py and is used here unmodified.
Verified before anything ran: our System32 x64 l3codecp.acm is byte-identical
to his identity file (sha256 587d64b9eedf3ea3...), and the x86 copy matches
too (7f0b3f35a85db853...). The probe is the era's largest casual Fraunhofer
share (WMP-era, Sound Forge, Cool Edit) — the second family of our per-codec
battery, and it was on this machine the whole time.

Phase-aware from birth
-----------------------
The ACM emits RAW MP3 frames — no Xing/LAME tag — so its decodes are
untrimmed BY CONSTRUCTION and sit off phase 0 (the grid-lock finding,
FINDINGS_idem_grid_lock, applies from day one). Every read here is therefore
the MINIMUM over the canonical phases {0, 529, 47}; nothing in this file ever
quotes a phase-0-only number.

Validation on known answers, registered before the run — results appended
--------------------------------------------------------------------------
    AV1  SELF-PAIRING. 5 ACM-320 fixtures (audit sources through the ACM
         itself) read closer to the fixed point under the ACM probe than any
         of 5 certified-genuine sources: max(fixture R) < min(genuine R).
    AV2  FAMILY LOCK, our side of his 1/72: 5 direct lab LAME-320 arms read
         HIGH under the ACM probe — median(arm R) >= median(fixture R) + 1.5
         dB. Failure would say the probe reads "MP3-ness", not Fraunhofer.
    AV3  THE DIAGONAL. The same 5 ACM fixtures under our shipped LAME-320
         probe read at least 1.0 dB higher than under the ACM probe —
         "a Fraunhofer file needs a Fraunhofer probe", measured here.

If AV1 fails the probe is not adopted and the failure ships as the result.
--------------------------------------------------------------------------------
RESULTS (2026-08-22, n = 5 per population, 30-s excerpts, canonical phases)

    AV1  HELD    fixtures -0.13..0.10 vs genuine 1.13..1.82 — the ACM
                 self-pairs with clean separation, his AUC-0.999 shape
                 reproduced in our hands.
    AV3  HELD    the same fixtures read 1.39..2.39 under our LAME-320 probe,
                 median diagonal 2.26 dB — a Fraunhofer file needs a
                 Fraunhofer probe, measured here.
    AV2  FAILED  as registered — and the failure is the registered margin,
                 not the lock. Measured: LAME arms 0.72..1.18 under the ACM
                 probe vs fixtures -0.13..0.10 — ZERO overlap, 0.62 dB of
                 absolute clearance, arms never reach the fixed point. The
                 1.5 dB median-gap bar was a guess and the measured gap is
                 0.91 dB. Consistent with his bench (1/72 LAME arms below
                 his lawful minimum): the pull toward the ACM fixed point is
                 real but partial. His disambiguator rule is adopted with
                 the probe: the ACM read is quoted beside a LAME read, never
                 alone.

ADOPTED as a measurement instrument (AV1 was the adoption criterion). Not
wired to the engine; a per-codec battery cell like MP3_IDEM before it.
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from idem_phase_probe import CANONICAL, crop  # noqa: E402
from mp3_idem_probe import dist, mp3_idem, require_ffmpeg  # noqa: E402

_ACM_TOOL = Path(__file__).resolve().parent / "exchange" / "provir-fhg_acm_encode.py"
_spec = importlib.util.spec_from_file_location("provir_fhg_acm", _ACM_TOOL)
fhg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fhg)

RATE = 44100
KBPS = 320
_HAD = None


def _driver():
    global _HAD
    if _HAD is None:
        _HAD = fhg.add_driver()
    return _HAD


def acm_roundtrip(audio: np.ndarray, ffmpeg: str) -> Optional[np.ndarray]:
    """decode(l3codecp-320(audio)) — raw frames to disk, ffmpeg decodes them."""
    x = audio if audio.ndim == 2 else np.stack([audio, audio], axis=1)
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    frames = fhg.encode(_driver(), pcm, RATE, 2, KBPS, 2)
    if len(frames) < 4096:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        enc = Path(tmp) / "acm.mp3"
        dec = Path(tmp) / "acm.wav"
        enc.write_bytes(frames)
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(enc), str(dec)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return None
        out, rate = sf.read(str(dec), dtype="float32")
    return out if rate == RATE else None


def acm_idem(audio: np.ndarray, ffmpeg: str) -> float:
    b = acm_roundtrip(audio, ffmpeg)
    if b is None:
        return float("nan")
    c = acm_roundtrip(b, ffmpeg)
    if c is None:
        return float("nan")
    d1, _ = dist(audio, b, RATE)
    d2, _ = dist(b, c, RATE)
    if not np.isfinite(d1) or not np.isfinite(d2) or d2 <= 0:
        return float("nan")
    return float(20.0 * np.log10(d1 / d2))


def best_phase_read(audio: np.ndarray, ffmpeg: str, probe: str) -> float:
    """min over the canonical phases — no phase-0-only numbers in this file."""
    reads = []
    for k in CANONICAL:
        x = crop(audio, k)
        if probe == "acm":
            reads.append(acm_idem(x, ffmpeg))
        else:
            r, _, _ = mp3_idem(x, RATE, ffmpeg)
            reads.append(r)
    finite = [r for r in reads if np.isfinite(r)]
    return min(finite) if finite else float("nan")


def load_excerpt(path: str, secs: float = 30.0) -> Optional[np.ndarray]:
    try:
        info = sf.info(path)
        if info.samplerate != RATE:
            return None
        data, _ = sf.read(path, dtype="float32", frames=int(secs * RATE))
        return data if data.size else None
    except Exception:
        return None


def main(argv: Optional[List[str]] = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    ffmpeg = require_ffmpeg()

    genuine = sorted(glob.glob("C:/Users/loutr/audit_corpus/authentic/*.flac"))[:5]
    arms = sorted(glob.glob("C:/Users/loutr/audit_corpus/fake/mp3_320/*.flac"))[:5]

    fixture_acm, fixture_lame, genuine_acm, arm_acm = [], [], [], []

    print("fixtures ACM-320 (sources auditees a travers le codec lui-meme) :")
    for path in genuine:
        audio = load_excerpt(path)
        if audio is None:
            continue
        fixture = acm_roundtrip(audio, ffmpeg)
        if fixture is None:
            print(f"  encodage ACM ECHOUE sur {Path(path).name}")
            continue
        r_acm = best_phase_read(fixture, ffmpeg, "acm")
        r_lame = best_phase_read(fixture, ffmpeg, "lame")
        fixture_acm.append(r_acm)
        fixture_lame.append(r_lame)
        print(f"  {Path(path).name[:44]:44} ACM={r_acm:6.2f}  LAME={r_lame:6.2f}")

    print("genuines sous la sonde ACM :")
    for path in genuine:
        audio = load_excerpt(path)
        if audio is None:
            continue
        r = best_phase_read(audio, ffmpeg, "acm")
        genuine_acm.append(r)
        print(f"  {Path(path).name[:44]:44} ACM={r:6.2f}")

    print("bras lab LAME-320 sous la sonde ACM :")
    for path in arms:
        audio = load_excerpt(path)
        if audio is None:
            continue
        r = best_phase_read(audio, ffmpeg, "acm")
        arm_acm.append(r)
        print(f"  {Path(path).name[:44]:44} ACM={r:6.2f}")

    fx = np.array([r for r in fixture_acm if np.isfinite(r)])
    fl = np.array([r for r in fixture_lame if np.isfinite(r)])
    ge = np.array([r for r in genuine_acm if np.isfinite(r)])
    ar = np.array([r for r in arm_acm if np.isfinite(r)])

    av1 = fx.size >= 4 and ge.size >= 4 and fx.max() < ge.min()
    av2 = ar.size >= 4 and np.median(ar) >= np.median(fx) + 1.5
    av3 = fl.size >= 4 and np.median(fl - fx[: fl.size]) >= 1.0

    print(
        f"\nAV1 auto-appariement (max fixture {fx.max():.2f} < min genuine {ge.min():.2f}): "
        f"{'HELD' if av1 else 'FAILED'}"
    )
    print(
        f"AV2 verrou de famille (med bras {np.median(ar):.2f} >= med fixture {np.median(fx):.2f} + 1.5): "
        f"{'HELD' if av2 else 'FAILED'}"
    )
    print(
        f"AV3 diagonale (med LAME-ACM {np.median(fl - fx[: fl.size]):.2f} >= 1.0): "
        f"{'HELD' if av3 else 'FAILED'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
