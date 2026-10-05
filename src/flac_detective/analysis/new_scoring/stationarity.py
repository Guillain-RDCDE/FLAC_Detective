"""Does the spectrum move? The guard the 2.1.0 codec readings need.

The Vorbis block-switch grid, the CELT grid and the replication coherence all
assume a signal that changes from frame to frame. A perfectly stationary one — a
test tone, a fixed synthetic waveform, a few pure sines — breaks both assumptions
without any codec involved: its leakage into every MDCT bin depends on the frame
alignment, and the leakage of its few lines is phase-locked across subbands. The
issue #12 amendment found the repository's own clean test signal (200 phase-locked
harmonics of 100 Hz) convicted at 116 by those readings; a 1 kHz sine read CELT
4.40 and replication 0.751.

Recorded music moves: on the issue's files the statistic below reads 17-18 dB, on
those synthetic signals 0.04-0.39 dB.

    motion = median over 1-16 kHz bins of the standard deviation over time of the
             dB magnitude (2048-point Hann frames, hop 1024, 8 spread 2 s segments)
"""

from __future__ import annotations

import numpy as np

FFT_SIZE = 2048
N_SEGMENTS = 8
SEGMENT_S = 2.0
BAND_HZ = (1000.0, 16000.0)

# Under this the spectrum does not move and the 2.1.0 readings abstain.
STATIONARY_BELOW_DB = 2.0


def spectral_motion_db(mono: np.ndarray, sample_rate: int) -> float:
    """Return the motion statistic in dB; NaN when there is nothing to read."""
    seg = int(SEGMENT_S * sample_rate)
    if len(mono) < seg:
        return float("nan")
    window = np.hanning(FFT_SIZE)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1 / sample_rate)
    band = (freqs >= BAND_HZ[0]) & (freqs < min(BAND_HZ[1], sample_rate / 2))
    hop = FFT_SIZE // 2
    index = np.arange(0, seg - FFT_SIZE, hop)[:, None] + np.arange(FFT_SIZE)[None, :]
    rows = []
    for start in np.linspace(0, len(mono) - seg, N_SEGMENTS).astype(int):
        x = np.asarray(mono[start : start + seg], dtype=np.float64)
        if float(np.dot(x, x)) <= 1e-8 * seg:
            continue
        spec = np.abs(np.fft.rfft(x[index] * window, axis=1))[:, band]
        rows.append(20 * np.log10(spec + 1e-9))
    if not rows:
        return float("nan")
    return float(np.median(np.concatenate(rows, axis=0).std(axis=0)))


def is_stationary(mono: np.ndarray, sample_rate: int) -> bool:
    """True when the spectrum does not move enough for a codec reading to mean anything."""
    motion = spectral_motion_db(mono, sample_rate)
    return bool(np.isfinite(motion) and motion < STATIONARY_BELOW_DB)
