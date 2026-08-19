"""The temporal seam: does the top of the spectrum stop *moving*?

The observable, and why it is a fourth kind
-------------------------------------------
The cliff, the hole count and the lattice are all spectral geometry — they ask
where energy sits and on what grid. Every one of them recovers coefficient
*values*, so every one of them dies when anything resamples. That was measured
twice: Rule 13 reads Opus at the null because CELT works at 48 kHz whatever it is
fed, and the lattice reads it at AUC 0.48 for the same reason.

This asks nothing about where the energy is. It asks whether each frequency bin
still *varies over time*.

Genuine high frequencies are restless — cymbals decay, sibilants come and go, bow
noise scrapes, a room breathes. A band that has been regenerated or noise-filled
is stationary: it sits at a level and stays there. The seam is the frequency where
restlessness stops.

    v[i]  = std over TIME of log1p(magnitude) in bin i, 10 kHz .. 22.05 kHz
    drop  = (mean(v[i-4:i]) - mean(v[i:i+4])) / mean(v[i-4:i])   for i above 12 kHz
    score = the largest drop, bounded 0..1 by construction

Algorithm from Jamie Dodd of Provir, given after two of this project's own guesses
failed — a step in the time-averaged envelope, then the position of the band edge.
Both read the null, and the reason is instructive: a time-averaged envelope
integrates variance away, and the collapse happens across a band rather than at a
boundary.

What it costs, stated before what it buys
------------------------------------------
It has a named false-positive mode: **production**. Heavy HF limiting, dense
synthetic pads and some mastering chains flatten temporal variance with no codec
involved. Provir keeps it measurement-only for that reason, and an early attempt
there to let it corroborate sent a verified-genuine 2006 record to their
equivalent of a conviction at 0.81.

Measured on 258 genuine files here — 80 certified CD rips and 178 wild taper
recordings, which agree closely:

    median 0.374   p90 0.573   p95 0.651   p99 0.797   max 0.913

So roughly 8 % of real music crosses the shipped bar. That is not a false-positive
rate, because of how the family is wired: see ``rules.temporal_seam``. It is the
rate at which a real recording offers a witness that has nothing to corroborate.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)

FFT_SIZE = 4096

# Analysis band. Below 10 kHz the variance is musical content rather than an
# allocation decision; 22.05 kHz is the ceiling of ordinary CD material.
BAND_LO_HZ = 10000.0
BAND_HI_HZ = 22050.0

# Search starts here: a collapse below 12 kHz is a band-limited master, which the
# cutoff rules already own and which this must not duplicate.
SEARCH_FROM_HZ = 12000.0

# Bins either side of the candidate seam. Four is Provir's value and it matters:
# narrower reads harmonic structure as a seam, wider smears a real one away.
HALF_WIDTH = 4

# Below this many usable frames the statistic is noise rather than a measurement.
MIN_FRAMES = 32


def temporal_seam(x: np.ndarray, sample_rate: int) -> Tuple[float, float]:
    """Return ``(seam_score, seam_hz)``; ``(nan, nan)`` when it cannot be measured.

    Abstaining rather than guessing is deliberate: a file too short, too quiet or
    too band-limited to carry the statistic is not evidence of anything, and a
    witness that speaks when it cannot see is the failure this project spent v1.9
    and v1.10 removing.
    """
    window = np.hanning(FFT_SIZE).astype(np.float32)
    hop = FFT_SIZE // 2

    frames = []
    for start in range(0, len(x) - FFT_SIZE, hop):
        block = x[start : start + FFT_SIZE] * window
        if float(np.abs(block).mean()) < 1e-6:
            continue
        frames.append(np.abs(np.fft.rfft(block)))
    if len(frames) < MIN_FRAMES:
        return float("nan"), float("nan")

    spec = np.asarray(frames)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / sample_rate)
    band = np.where((freqs >= BAND_LO_HZ) & (freqs <= min(freqs[-1], BAND_HI_HZ)))[0]
    if band.size < 4 * HALF_WIDTH + 2:
        return float("nan"), float("nan")

    # log1p, not log: defined at zero, so a silent bin contributes a real value
    # instead of -inf and one dead bin cannot poison the whole measurement.
    variability = np.std(np.log1p(spec[:, band]), axis=0)
    band_freqs = freqs[band]

    candidates = np.where(band_freqs >= SEARCH_FROM_HZ)[0]
    candidates = candidates[
        (candidates >= HALF_WIDTH) & (candidates + HALF_WIDTH <= variability.size)
    ]
    if candidates.size == 0:
        return float("nan"), float("nan")

    best_drop, best_hz = float("-inf"), float("nan")
    for index in candidates:
        before = float(variability[index - HALF_WIDTH : index].mean())
        after = float(variability[index : index + HALF_WIDTH].mean())
        if before <= 0:
            continue
        drop = (before - after) / before
        if drop > best_drop:
            best_drop, best_hz = drop, float(band_freqs[index])

    if not np.isfinite(best_drop):
        return float("nan"), float("nan")
    return max(0.0, best_drop), best_hz
