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
    statistic = MEDIAN over frames of the mean strictly-interior run length

STRICTLY INTERIOR means neither edge. A run reaching Nyquist is a lowpass edge and
belongs to the cutoff rule; a run starting at the 10 kHz band floor is the analysis
window's own boundary and is equally not a hole. v1.11.0 excluded only the top, on
this project's own reasoning; Provir's glossary supplies the other half. Measured:
it changes nothing on our material — at 10 kHz real music essentially always has
energy, so runs rarely start at the floor — but it is the correct definition and it
costs nothing to hold.

MEDIAN OVER FRAMES is kept, and the second glossary correction was REJECTED on
measurement. Provir's standing warning against "any statistic aggregated across
frames" — at transparent bitrates the zeroing is dynamic, and averaging destroys
it; four of their earlier defences died that way — is real, and a max-over-frames
variant was built and priced against it. On 25 genuine files the max looked better
everywhere. On the full 228 it does not:

    arm          median   max
    opus_256       92 %   81 %
    vorbis_q8      93 %   86 %
    mp3_320        92 %   81 %
    mp3_V0         81 %   77 %
    aacmf_256      73 %   73 %
    aac_ff320      19 %   33 %
    TOTAL          75 %   72 %

Each variant priced at its own p95 on the same 228 genuine files, so the columns
cost the same. The max wins on exactly one arm, and it is the one Rule 13 already
reads at AUC 0.99; it pays for that with 11 points on Opus, Vorbis and mp3_320,
where no other family in this engine reaches at all. That is the wrong trade, so
the median stands.

Two lessons, both this project's own: a 25-file calibration reversed the ranking of
228 (the same small-sample error that mis-set Rule 13's ceiling), and a warning
that holds for the author's statistic need not hold for ours — their zeroing is
dynamic per frame, our union mask with the mid channel is already a per-frame
conjunction, so the median is not averaging the artefact away.

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

**The threshold is absolute, so the reading moves with level**, and the fix is to
normalise EVERY file — never to guard the normalisation behind a peak threshold.

That correction came from Provir after this shipped, and it is worth recording in
full because the guarded form is not merely a different choice: it is broken at its
own boundary. A guard makes the statistic peak-relative below the threshold and
absolute at or above it — two different statistics with a discontinuity between
them. Measured here on our own files, scaled in memory so nothing but the level
changed:

    peak 0.7501 -> 2.00      peak 0.7499 -> 16.04
    peak 0.7501 -> 1.67      peak 0.7499 -> 15.29   (verdict flip)

An inaudible 0.002 dB difference moved the reading eightfold across the decision
bar. And the rescaled side is the well-behaved one: 16.04 / 14.28 / 17.85 for peaks
0.7499 / 0.70 / 0.60, against 2.00 for the same audio one ten-thousandth louder.
The guard was applying the good statistic only to quiet files.

Provir measured the same seam from the other side at their own boundary — 235
against 83 — and replaced the guard with unconditional normalisation on
2026-07-28. This engine inherited the broken form from their earlier description
and carried it into v1.11.0.
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

# EVERY file is normalised to full scale. Not a threshold — a statement that there
# is no threshold, kept as a named constant so the next person cannot reintroduce
# one without editing this line and reading the docstring above it.
NORM_GUARD = 1.0

MAX_FRAMES = 200
MIN_FRAMES = 16


def _restore(signal: np.ndarray) -> np.ndarray:
    """Normalise to full scale, unconditionally.

    Unconditional is the whole point. Any guard splits this into two statistics
    with a seam at the guard, and a file one ten-thousandth either side of it gets
    a different verdict — see the module docstring for the measurement.
    """
    peak = float(np.abs(signal).max())
    if 0 < peak < NORM_GUARD:
        return (signal / peak).astype(np.float32)
    return signal


def _interior_runs(mask: np.ndarray) -> np.ndarray:
    """True-run lengths, discarding any run that touches EITHER edge.

    Both exclusions are the same argument. A run reaching the last bin is a lowpass
    edge, which the cutoff rule owns; a run starting at the first bin is the 10 kHz
    analysis floor, which is the window's boundary rather than anything the encoder
    did.
    """
    if not mask.any():
        return np.zeros(0, dtype=np.int64)
    padded = np.concatenate(([False], mask, [False]))
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    starts, ends = edges[::2], edges[1::2]
    return (ends - starts)[(ends < mask.size) & (starts > 0)]


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
    """Return ``(longest_interior_run, side_mid_ratio)``.

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
    # MEDIAN over frames of the per-frame mean. A max variant was measured against
    # this and lost on five arms of six — see the module docstring.
    per_frame = []
    for row in dead:
        runs = _interior_runs(row)
        per_frame.append(float(runs.mean()) if runs.size else 0.0)
    return float(np.median(per_frame)) if per_frame else 0.0, ratio
