"""Dead runs in the SIDE channel — what joint stereo leaves behind.

The observable
--------------
Above its coupling frequency a lossy encoder using joint or intensity stereo
quantises the side channel toward zero and leaves long contiguous holes there,
while the mid stays perfectly alive. So the artefact is not in the spectrum at
all — it is in the stereo image, and a mono-sum search cannot see it by
construction.

That is why this project's own first attempt at a run-length statistic measured a
clean null in two domains: it was looking at ``(L+R)/2``, like every other family
here. Jamie Dodd of Provir supplied the channel.

    mid  = |STFT((L+R)/2)|, bins from 10 kHz up
    side = |STFT(L-R)|,     bins from 10 kHz up
    run mask = (mid < UNION_DEAD) OR (side < UNION_DEAD)
    statistic = median over frames of the mean interior run length

INTERIOR ONLY: a run touching the top bin is discarded, because a run reaching
Nyquist is a lowpass edge and belongs to the cutoff rule. The same exclusion this
project applies elsewhere, for the same reason.

The two ways it goes wrong, both measured before use
-----------------------------------------------------
**Mono material manufactures it out of nothing.** No stereo image means no side
channel means every high bin is trivially below any threshold. Provir measured
their own mono CDs at L-R correlation 1.000000 and side/mid energy 3e-8, producing
a dead-run within a few units of their solo conviction floor — that is convicting
a legitimate master for the absence of a stereo image. ``MONO_GATE`` is therefore
not a refinement; without it the statistic is dangerous. The threshold sits in a
7000x gap (their n=360: mono maxes at 2.9e-8, real stereo bottoms at 2.1e-4), so
its placement is not delicate, but its existence is not optional.

**The threshold is absolute, so the reading moves with level.** Provir measured
identical audio at 0 / -12 / -24 / -36 dB reading 16 / 54 / 137 / 283, with six
files out of six changing verdict on gain alone. Plain peak normalisation re-scores
everything the constants were fitted on and cost them 68.9 % -> 59.4 % for no
false-positive benefit. What works, and what is used here, is a floor-guarded
restore: rescale only files below 0.75 of full scale.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger(__name__)

FFT_SIZE = 2048
HOP = FFT_SIZE // 2

# Below 10 kHz the side channel carries real stereo information at every bitrate;
# coupling happens above it.
BAND_LO_HZ = 10000.0

# A bin counts as dead below this magnitude. Absolute, hence the restore below.
UNION_DEAD = 3e-4

# No stereo image below this side/mid energy ratio.
MONO_GATE = 1e-5

# Only quiet files are rescaled, so the constants keep meaning what they meant.
RESTORE_BELOW_PEAK = 0.75

MAX_FRAMES = 200
MIN_FRAMES = 16


def _restore(signal: np.ndarray) -> np.ndarray:
    """Floor-guarded gain restore."""
    peak = float(np.abs(signal).max())
    if 0 < peak < RESTORE_BELOW_PEAK:
        return (signal / peak).astype(np.float32)
    return signal


def _interior_runs(mask: np.ndarray) -> np.ndarray:
    """True-run lengths, discarding any run that touches the top bin."""
    if not mask.any():
        return np.zeros(0, dtype=np.int64)
    padded = np.concatenate(([False], mask, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[::2], edges[1::2]
    return (ends - starts)[ends < mask.size]


def _spectra(signal: np.ndarray, rate: int) -> np.ndarray:
    """|STFT| restricted to bins above ``BAND_LO_HZ``."""
    window = np.hanning(FFT_SIZE).astype(np.float32)
    freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / rate)
    band = np.where(freqs >= BAND_LO_HZ)[0]
    frames = []
    for start in range(0, len(signal) - FFT_SIZE, HOP):
        block = signal[start : start + FFT_SIZE] * window
        frames.append(np.abs(np.fft.rfft(block))[band])
        if len(frames) >= MAX_FRAMES:
            break
    return np.asarray(frames) if frames else np.empty((0, 0))


def side_dead_run(data: np.ndarray, sample_rate: int) -> Tuple[float, float]:
    """Return ``(mean_interior_run, side_mid_ratio)``.

    ``(nan, ratio)`` when the file is mono-gated, too short, or single-channel —
    abstaining rather than guessing, which for this statistic is the difference
    between a measurement and an accusation of having no stereo image.
    """
    if data.ndim < 2 or data.shape[1] < 2:
        return float("nan"), 0.0

    left = data[:, 0].astype(np.float64)
    right = data[:, 1].astype(np.float64)
    mid_raw = ((left + right) / 2.0).astype(np.float32)
    side_raw = (left - right).astype(np.float32)

    mid_energy = float(np.mean(mid_raw.astype(np.float64) ** 2))
    ratio = (
        0.0 if mid_energy <= 0 else float(np.mean(side_raw.astype(np.float64) ** 2) / mid_energy)
    )
    if ratio < MONO_GATE:
        return float("nan"), ratio

    side_spec = _spectra(_restore(side_raw), sample_rate)
    mid_spec = _spectra(_restore(mid_raw), sample_rate)
    if side_spec.shape != mid_spec.shape or len(side_spec) < MIN_FRAMES:
        return float("nan"), ratio

    dead = (mid_spec < UNION_DEAD) | (side_spec < UNION_DEAD)
    per_frame = []
    for row in dead:
        runs = _interior_runs(row)
        per_frame.append(float(runs.mean()) if runs.size else 0.0)
    return float(np.median(per_frame)), ratio
