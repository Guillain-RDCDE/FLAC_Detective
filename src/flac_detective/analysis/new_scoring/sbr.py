"""Spectral band replication: a high band that is a phase-locked copy of a lower one.

Every cutoff-shaped rule in this engine reads "energy up to 20 kHz" as "not
truncated". SBR breaks that story. HE-AAC (v1 and v2), mp3PRO and their relatives
code the lower part of the spectrum and rebuild the upper part from it: the
decoder takes complex QMF subbands from below the crossover, copies them up by a
fixed number of subbands, and only adjusts their envelope. The file arrives with
energy to the top of the band, energy that was never in the master. Issue #12's
HE-AAC v2 128 kbps transcode reads AUTHENTIC 0 for exactly that reason.

The copy is what gives it away. A copied subband keeps the phase evolution of its
source, so the high band and the band ``p`` subbands below it stay coherent in the
complex domain over time, after one sign correction for the shift. Natural music
does not do this: two partials in different subbands drift in phase against each
other unless their frequency difference happens to be an exact multiple of the
subband spacing, and the median over every high subband and every segment is
indifferent to the few that do. A drum hit is broadband, but its phases across
subbands are noise, not a copy.

    X      = 128-point STFT, hop 64: 64 subbands of fs/128 Hz, the QMF geometry
    coh(p) = median over (segment, high subband k) of
             |sum_t X[t, k] conj(X[t, k - p] (-1)^(p t))| / (|X[., k]| |X[., k - p]|)
    ratio  = max over p of coh(p)

High subbands are those from 5.5 kHz to 20 kHz (or 1 kHz under Nyquist); ``p``
runs from 6 to 40 subbands. The reading is taken on the mono mix, where parametric
stereo, which rebuilds left and right from that mix, does not hide it.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

QMF_BANDS = 64
STFT_SIZE = 2 * QMF_BANDS
STFT_HOP = QMF_BANDS
SEGMENT_FRAMES = 256
N_SEGMENTS = 32
SHIFT_RANGE = (6, 41)
HIGH_BAND_HZ = (5500.0, 20000.0)
MIN_ENERGY = 1e-6


def replication_coherence(mono: np.ndarray, sample_rate: int) -> Tuple[float, int]:
    """Return ``(coherence, shift_in_subbands)``; ``(nan, -1)`` when it cannot be read."""
    x = np.asarray(mono, dtype=np.float32)
    window = np.hanning(STFT_SIZE).astype(np.float32)
    total = (len(x) - STFT_SIZE) // STFT_HOP
    if total < SEGMENT_FRAMES * 4:
        return float("nan"), -1
    starts = np.linspace(
        0, total - SEGMENT_FRAMES, min(N_SEGMENTS, total // SEGMENT_FRAMES)
    ).astype(int)
    frames = (starts[:, None] + np.arange(SEGMENT_FRAMES)[None, :]).ravel()
    index = frames[:, None] * STFT_HOP + np.arange(STFT_SIZE)[None, :]
    spec = np.fft.rfft(x[index] * window[None, :], axis=1)[:, :QMF_BANDS].astype(np.complex64)
    spec = spec.reshape(len(starts), SEGMENT_FRAMES, QMF_BANDS)
    alternate = np.where(np.arange(SEGMENT_FRAMES) % 2 == 0, 1.0, -1.0).astype(np.float32)
    alternate = alternate[None, :, None]

    width = sample_rate / STFT_SIZE
    k_lo = int(HIGH_BAND_HZ[0] / width)
    k_hi = int(min(HIGH_BAND_HZ[1], sample_rate / 2 - 1000) / width)
    best = (float("nan"), -1)
    for shift in range(*SHIFT_RANGE):
        ks = np.arange(max(k_lo, shift + 2), k_hi)
        if ks.size == 0:
            continue
        high = spec[:, :, ks]
        low = spec[:, :, ks - shift] * (alternate if shift % 2 else 1.0)
        e_high = np.sum(np.abs(high) ** 2, axis=1)
        e_low = np.sum(np.abs(low) ** 2, axis=1)
        coherence = np.abs(np.sum(high * np.conj(low), axis=1)) / (np.sqrt(e_high * e_low) + 1e-20)
        live = e_high > MIN_ENERGY
        if not live.any():
            continue
        value = float(np.median(coherence[live]))
        if not np.isfinite(best[0]) or value > best[0]:
            best = (value, shift)
    return best
