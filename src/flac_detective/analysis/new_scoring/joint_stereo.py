"""The side-channel step: where a joint-stereo coder stops sending the difference.

Rule 15 reads the side channel as *dead* above 10 kHz, against an absolute bar,
and only above a 17 kHz cutoff (below it a band-limited master empties the band
and the bar reads that as death). Issue #12 found the coders it misses. Vorbis at
low quality uses point stereo and CELT at 64 kbps uses intensity stereo: above a
frequency chosen by the encoder both channels carry the same signal up to a gain,
so the side channel falls by ~20 dB against the mid there while it stays at the
music's own ratio below. The side is not dead — it is a fixed fraction of the mid
— and on the issue's ``-q1`` file the cutoff (16,750 Hz) keeps Rule 15 from
looking at all.

This reads the step itself, relative to the file's own stereo image and only
below the file's own cutoff, so a band-limited master has nothing to offer it:

    r[b]  = median over loud frames of 10 log10(E_side / E_mid) in 1 kHz band b,
            from 1 kHz to (cutoff - 500 Hz)
    step  = max over splits s of median(r[s-3 .. s-1]) - median(r[s .. s+2])   (dB)

Genuine stereo images change with frequency, but as slopes and bumps; a coder
deciding to stop coding the difference makes a step. The statistic abstains on
mono (side 40 dB under the mid over the whole band) and when fewer than six
bands lie under the cutoff.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

FFT_SIZE = 2048
N_FRAMES = 600
BAND_HZ = 1000.0
LOW_HZ = 1000.0
TOP_HZ = 20000.0
SPAN = 3
CUTOFF_MARGIN_HZ = 500.0
LOUD_PERCENTILE = 25
MIN_LOUD_FRAMES = 16
MONO_GATE_DB = -40.0


def side_step(
    audio: np.ndarray, sample_rate: int, cutoff_hz: Optional[float] = None
) -> Tuple[float, float, float]:
    """Return ``(step_db, split_hz, side_to_mid_db)``; NaN where not measurable."""
    nan = float("nan")
    if audio.ndim != 2 or audio.shape[1] < 2:
        return nan, nan, nan
    n = len(audio)
    total = (n - FFT_SIZE) // (FFT_SIZE // 2)
    if total < 64:
        return nan, nan, nan
    starts = np.linspace(0, n - FFT_SIZE - 1, min(N_FRAMES, total)).astype(int)
    window = np.hanning(FFT_SIZE)
    index = starts[:, None] + np.arange(FFT_SIZE)[None, :]
    # Only the read frames are converted: a whole-file float64 copy of four
    # signals costs ~400 MB on a five-minute track, per worker.
    left = audio[index, 0].astype(np.float64)
    right = audio[index, 1].astype(np.float64)
    e_mid = np.abs(np.fft.rfft((left + right) / 2 * window, axis=1)) ** 2
    e_side = np.abs(np.fft.rfft((left - right) / 2 * window, axis=1)) ** 2
    freqs = np.fft.rfftfreq(FFT_SIZE, 1 / sample_rate)
    side_to_mid = float(10 * np.log10(e_side.sum() / max(float(e_mid.sum()), 1e-30) + 1e-30))
    if side_to_mid < MONO_GATE_DB:
        return nan, nan, side_to_mid

    top = min(sample_rate / 2 - 1000, TOP_HZ)
    if cutoff_hz is not None and np.isfinite(cutoff_hz):
        top = min(top, cutoff_hz - CUTOFF_MARGIN_HZ)
    edges = np.arange(LOW_HZ, top + 1, BAND_HZ)
    ratios = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        band = (freqs >= lo) & (freqs < hi)
        em, es = e_mid[:, band].sum(axis=1), e_side[:, band].sum(axis=1)
        loud = em > np.percentile(em, LOUD_PERCENTILE)
        if loud.sum() < MIN_LOUD_FRAMES:
            ratios.append(nan)
            continue
        ratios.append(float(np.median(10 * np.log10((es[loud] + 1e-30) / (em[loud] + 1e-30)))))
    r = np.array(ratios)

    best, where = -np.inf, nan
    for i in range(SPAN, len(r) - SPAN + 1):
        below, above = r[i - SPAN : i], r[i : i + SPAN]
        if np.isnan(below).any() or np.isnan(above).any():
            continue
        step = float(np.median(below) - np.median(above))
        if step > best:
            best, where = step, float(edges[i])
    if not np.isfinite(best):
        return nan, nan, side_to_mid
    return best, where, side_to_mid
