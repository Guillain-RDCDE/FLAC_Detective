#!/usr/bin/env python3
"""Two probes proposed to Provir for the Teardrops vinyl, validated before proposing.

Neither is a detector for this engine. They exist because a vinyl report arrived
with two questions it could not settle, and suggesting a method without running it
is the thing this project keeps telling other people not to do.

**1. Rotation probe — PROPOSED, BUILT, AND REFUSED BY ITS OWN TEST.**

The idea: a record turns at 33 1/3 RPM = 0.5556 Hz, eccentricity modulates the
signal once per revolution, and that component is a physical clock inside the
recording — so it would answer "is this file being read at the rate it was
captured at" with no new capture. A 48 kHz file read as 44.1 kHz would show the
peak at 0.5556 x 44100/48000 = 0.5104 Hz.

It works on a constructed case: inject a known 0.5556 Hz modulation into a real
file and the probe finds it, and finds 0.5104 when the same samples are read at
the wrong rate. That is the validation I nearly stopped at.

**On a real vinyl rip it fails.** Fourteen tracks of a documented 24-bit/96 kHz
transfer (Pro-Ject Debut Carbon Esprit -> Yaqin MS23B -> Steinberg UR22) return
peaks scattered from 19.5 to 67.5 "RPM" with no clustering at 33 1/3 or 45. The
amplitude envelope in the 0.3-1.2 Hz band is dominated by musical phrasing, which
is far stronger than eccentricity. A second formulation — the rotation line in the
raw sub-5 Hz spectrum — fails too: same scatter, peak-to-median ratio around 3,
and sub-5 Hz energy is only 0.2-0.4 % of the total because the chain does not pass
rumble at that level.

So the shortcut does not exist, and the honest answer to "how do I check the rate
without capturing anything new" is that you cannot: time the side with a stopwatch,
or check what the tools were told the rate was. Kept here, refused, rather than
deleted — the failed version of a method is the part worth publishing.

**2. HF content correlation.** Surface noise is uncorrelated with programme
material by definition; content is correlated — it rises on the hats and falls in
the breakdown. So correlating the 19-21 kHz energy envelope against the 1-5 kHz
envelope separates "there is content up there" from "there is a noise floor up
there", simultaneously, without needing a run-out groove.

That one IS validated on real material, and on real vinyl. Fourteen tracks of the
24/96 transfer above read r = +0.29 to +0.64, against r = -0.04 for a band emptied
of content and refilled with noise at the same level. Real HF content tracks the
programme; a floor does not.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

RPM_33 = 100.0 / 3.0  # 33 1/3
ROTATION_HZ = RPM_33 / 60.0  # 0.5556
ENVELOPE_FRAME_S = 0.02  # 50 Hz envelope sample rate — plenty above 1 Hz
SEARCH_LO_HZ, SEARCH_HI_HZ = 0.30, 1.20


def _mono(data: np.ndarray) -> np.ndarray:
    return data if data.ndim == 1 else data.mean(axis=1)


def _envelope(signal: np.ndarray, rate: int) -> Tuple[np.ndarray, float]:
    """RMS envelope and its own sample rate."""
    frame = max(1, int(ENVELOPE_FRAME_S * rate))
    usable = (len(signal) // frame) * frame
    frames = signal[:usable].reshape(-1, frame)
    return np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1)), rate / frame


def rotation_peak_hz(signal: np.ndarray, rate: int) -> Optional[float]:
    """Dominant modulation frequency in the once-per-revolution band, or None."""
    env, env_rate = _envelope(signal, rate)
    if len(env) < 64:
        return None
    env = env - env.mean()
    if not np.any(env):
        return None
    window = np.hanning(len(env))
    spectrum = np.abs(np.fft.rfft(env * window))
    freqs = np.fft.rfftfreq(len(env), 1.0 / env_rate)
    band = np.where((freqs >= SEARCH_LO_HZ) & (freqs <= SEARCH_HI_HZ))[0]
    if band.size == 0:
        return None
    return float(freqs[band][int(np.argmax(spectrum[band]))])


def hf_content_correlation(signal: np.ndarray, rate: int) -> Optional[float]:
    """Pearson r between the 19-21 kHz and 1-5 kHz energy envelopes.

    High r means the high band follows the programme, which a noise floor cannot
    do. Low r means whatever is up there is not tracking the music.
    """
    n_fft = 4096
    hop = n_fft // 2
    if len(signal) < n_fft * 8:
        return None
    freqs = np.fft.rfftfreq(n_fft, 1.0 / rate)
    hi = np.where((freqs >= 19000) & (freqs <= 21000))[0]
    lo = np.where((freqs >= 1000) & (freqs <= 5000))[0]
    if hi.size == 0 or lo.size == 0:
        return None  # the band does not exist at this rate: not a reading of zero
    window = np.hanning(n_fft)
    hi_env: List[float] = []
    lo_env: List[float] = []
    for start in range(0, len(signal) - n_fft, hop):
        spectrum = np.abs(np.fft.rfft(signal[start : start + n_fft] * window))
        hi_env.append(float(spectrum[hi].mean()))
        lo_env.append(float(spectrum[lo].mean()))
    a = np.log10(np.asarray(hi_env) + 1e-12)
    b = np.log10(np.asarray(lo_env) + 1e-12)
    if a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _validate_rotation(source: Path) -> None:
    print("=== 1. sonde de rotation (cas construit) ===")
    data, rate = sf.read(str(source), dtype="float64", frames=60 * 48000)
    signal = _mono(data)
    t = np.arange(len(signal)) / rate
    modulated = signal * (1.0 + 0.08 * np.sin(2 * np.pi * ROTATION_HZ * t))

    true_peak = rotation_peak_hz(modulated, rate)
    # The whole point: the SAME samples read as if they were 44.1 kHz.
    wrong_rate = 44100 if rate == 48000 else int(round(rate * 44100 / 48000))
    wrong_peak = rotation_peak_hz(modulated, wrong_rate)
    expected_wrong = ROTATION_HZ * wrong_rate / rate

    print(f"  source {source.name}, {rate} Hz, modulation injectee a {ROTATION_HZ:.4f} Hz")
    print(f"  lue a {rate} Hz      -> pic {true_peak:.4f} Hz   (attendu {ROTATION_HZ:.4f})")
    print(f"  lue a {wrong_rate} Hz -> pic {wrong_peak:.4f} Hz   (attendu {expected_wrong:.4f})")
    ok = (
        true_peak is not None
        and wrong_peak is not None
        and abs(true_peak - ROTATION_HZ) < 0.02
        and abs(wrong_peak - expected_wrong) < 0.02
    )
    print(f"  -> la sonde distingue les deux lectures : {'OUI' if ok else 'NON'}")


def _validate_correlation(source: Path) -> None:
    print("\n=== 2. correlation de contenu HF (materiel reel) ===")
    data, rate = sf.read(str(source), dtype="float64", frames=60 * 48000)
    signal = _mono(data)

    real = hf_content_correlation(signal, rate)

    # The confound, built on purpose: the band emptied of content, then filled
    # with noise at a level that LOOKS like content on a spectrogram.
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1.0 / rate)
    spectrum[freqs > 14000] = 0.0
    band_limited = np.fft.irfft(spectrum, n=len(signal))
    rng = np.random.default_rng(7)
    noise = rng.normal(0.0, 1.0, len(band_limited))
    noise_spec = np.fft.rfft(noise)
    noise_spec[(freqs < 19000) | (freqs > 21000)] = 0.0
    hiss = np.fft.irfft(noise_spec, n=len(band_limited))
    hiss *= np.sqrt(np.mean(signal**2)) * 0.02 / max(np.sqrt(np.mean(hiss**2)), 1e-12)
    faked = band_limited + hiss

    fake_r = hf_content_correlation(faked, rate)
    print(f"  contenu reel en 19-21 kHz        r = {real:+.3f}")
    print(f"  bande videe + bruit au meme etage r = {fake_r:+.3f}")
    print(f"  -> le test separe contenu et plancher : {'OUI' if real - fake_r > 0.3 else 'NON'}")


def _measure(paths: List[Path], seconds: float = 120.0) -> None:
    """Report both probes on real files, and what a wrong rate would do to them.

    The second column is the whole proposal: the SAME samples read as if the file
    had been captured at 44.1 kHz instead of 48 kHz. If the rotation peak moves by
    44100/48000 while the record obviously did not change speed, the probe has
    caught a rate-handling error rather than a property of the pressing.
    """
    print(f"{'fichier':38s} {'tr/min':>7s} {'pic Hz':>8s} {'si lu x0.919':>13s} {'r HF':>7s}")
    for path in paths:
        try:
            info = sf.info(str(path))
            data, rate = sf.read(str(path), dtype="float64", frames=int(seconds * info.samplerate))
        except Exception as exc:
            print(f"{path.name[:38]:38s} ECHEC {exc}")
            continue
        signal = _mono(data)
        peak = rotation_peak_hz(signal, rate)
        wrong = rotation_peak_hz(signal, int(round(rate * 44100 / 48000)))
        corr = hf_content_correlation(signal, rate)
        rpm = peak * 60.0 if peak else float("nan")
        print(
            f"{path.name[:38]:38s} {rpm:7.2f} {peak if peak else float('nan'):8.4f} "
            f"{wrong if wrong else float('nan'):13.4f} "
            f"{corr if corr is not None else float('nan'):7.3f}"
        )


def main(argv: Optional[List[str]] = None) -> int:
    """Validate both probes. Returns a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, help="an authentic full-band file")
    ap.add_argument("--measure", type=Path, nargs="+", help="real files to probe")
    args = ap.parse_args(argv)

    if args.measure:
        files: List[Path] = []
        for item in args.measure:
            files.extend(sorted(item.glob("*.flac")) if item.is_dir() else [item])
        _measure(files)
        return 0

    source = args.source
    if source is None:
        candidates = sorted(Path(r"C:\Users\loutr\audit_corpus\authentic").glob("*.flac"))
        if not candidates:
            print("no source available", file=sys.stderr)
            return 1
        source = candidates[0]

    _validate_rotation(source)
    _validate_correlation(source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
