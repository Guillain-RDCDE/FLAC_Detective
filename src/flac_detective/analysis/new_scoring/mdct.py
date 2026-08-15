"""MDCT frame-alignment analysis — reading the encoder's arithmetic, not its cutoff.

Every other detector in this package looks ABOVE the encoder's cutoff: the
spectral cliff, Rule 7's silent-passage HF energy, the (now removed) pre-echo and
aliasing tests, and the CNN's effective attention. That works at 128 kbps and
stops working at 256–320 kbps, where the encoder keeps the whole band. The
project's own measurement of that ceiling: mp3_320 detectability AUC 0.53, i.e.
none (ml/README.md).

This module tests something the cutoff cannot hide. An MDCT codec quantises
transform coefficients, and quantisation sends a large fraction of them to exactly
zero. Those zeros survive decoding: re-analyse the decoded audio with the SAME
transform — same frame length, same window, same sample alignment — and the
zeroed bins reappear as deep holes in the spectrum. Analyse at any other
alignment and the holes smear across neighbouring bins and disappear.

The statistic is therefore not "how many holes" (real music has holes too) but
"is there ONE alignment at which holes are far more common than at all others".
Genuine lossless audio has no preferred alignment — its curve is flat, around
1.0. That flatness is the analytic null the test is read against.

Two details decide whether this reads anything at all:

* **The window must match the encoder's.** ffmpeg-family AAC uses a
  Kaiser-Bessel-derived window with alpha = 4 for long blocks, not the sine
  window. Analysed with a sine window the statistic collapses to the floor, which
  looks exactly like "the method does not work". (Jamie Dodd of Provir flagged
  this trap; it cost him a day and it is reproducible here with ``sine``.)
* **The alignment search must be sample-exact.** Encoder priming delay is
  arbitrary, so the correct offset is unknown and all 1024 must be searched.

Scope, stated plainly: this reads AAC-family transcodes, whose long block is a
2048-sample MDCT. MP3 (hybrid polyphase + 18-point MDCT), Opus/CELT (480/960) and
Vorbis (different window shape) do not match this hypothesis and score at the
null — for them the existing rules already do the work.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import median_filter

logger = logging.getLogger(__name__)

# AAC long block: 2048-sample window, 1024-sample hop.
WINDOW_LEN = 2048
HOP = WINDOW_LEN // 2

# Analysis band. Below ~2 kHz the encoder quantises far more finely (few zeros),
# above ~16 kHz band-limited material is empty and would read as all-holes.
BAND_HZ: Tuple[float, float] = (2000.0, 16000.0)

# A bin counts as a hole at this depth below its local neighbourhood median.
HOLE_DEPTH_DB = 40.0

# Reliability gate. peak_ratio is a ratio, so it is only meaningful while its
# denominator is. Material whose 2-16 kHz band is nearly empty — a handful of
# pure tones, a heavily band-limited source — produces a baseline hole fraction
# near zero, and a ratio of two near-zero numbers is noise that can land anywhere.
# Measured: real music, white noise and AAC transcodes all sit around 0.005,
# while four bare sine waves give 0.00019, i.e. 27x lower, and drift to a
# peak_ratio of 3.0 on nothing at all. Below this floor the statistic abstains
# rather than guessing — the same choice Rule 12 makes below a 7 kHz rolloff.
MIN_BASELINE_HOLE_FRACTION = 0.001

_BASIS_CACHE: Dict[Tuple[int, Tuple[float, float]], np.ndarray] = {}


def kbd_window(length: int = WINDOW_LEN, alpha: float = 4.0) -> np.ndarray:
    """Kaiser-Bessel-derived window — ffmpeg's AAC long-block window (alpha=4)."""
    half = length // 2
    kaiser = np.kaiser(half + 1, np.pi * alpha)
    cumulative = np.cumsum(kaiser)
    rising = np.sqrt(cumulative[:half] / cumulative[-1])
    return np.concatenate([rising, rising[::-1]]).astype(np.float32)


def sine_window(length: int = WINDOW_LEN) -> np.ndarray:
    """Sine window — MPEG's other standard long window."""
    n = np.arange(length)
    return np.sin(np.pi / length * (n + 0.5)).astype(np.float32)


def mdct_basis(sample_rate: int, band_hz: Tuple[float, float] = BAND_HZ) -> np.ndarray:
    """MDCT basis restricted to the analysis band, cached per (rate, band).

    Restricting the columns before the matmul — rather than slicing the result —
    is what keeps a full-hop scan affordable: the discarded bins are never
    computed.
    """
    key = (sample_rate, band_hz)
    cached = _BASIS_CACHE.get(key)
    if cached is not None:
        return cached
    half = WINDOW_LEN // 2
    lo = max(1, int(band_hz[0] / (sample_rate / 2) * half))
    hi = min(half, int(band_hz[1] / (sample_rate / 2) * half))
    n = np.arange(WINDOW_LEN)[:, None]
    k = np.arange(lo, hi)[None, :]
    basis = np.cos(np.pi / half * (n + 0.5 + half / 2) * (k + 0.5)).astype(np.float32)
    _BASIS_CACHE[key] = basis
    return basis


def alignment_curve(
    x: np.ndarray,
    sample_rate: int,
    window: np.ndarray,
    n_frames: int = 24,
    offsets: Optional[Sequence[int]] = None,
    ref_size: int = 33,
    depth_db: float = HOLE_DEPTH_DB,
) -> np.ndarray:
    """Hole fraction per frame alignment.

    A hole is an MDCT bin ``depth_db`` below the median of its own ±(ref_size//2)
    neighbourhood. The reference is local and therefore scale-free: an absolute
    threshold would only measure how quiet the track is, whereas what is being
    detected is a coefficient *set to zero while its neighbours were kept*.

    All requested offsets are evaluated in ONE matmul per frame. The obvious
    loop-over-offsets version is ~15x slower for identical output — the cost is
    per-call overhead, not arithmetic.
    """
    basis = mdct_basis(sample_rate)
    offs = np.asarray(list(range(HOP) if offsets is None else offsets), dtype=np.int64)
    if offs.size == 0:
        return np.empty(0)

    usable = len(x) - WINDOW_LEN - int(offs.max())
    if usable <= 0:
        return np.full(offs.size, np.nan)
    # Spread the sampled frames over the whole excerpt rather than taking a
    # contiguous run: one loud chorus should not decide the verdict.
    stride = max(HOP, (usable // max(1, n_frames)) // HOP * HOP)

    tap = np.arange(WINDOW_LEN)
    thr = 10 ** (-depth_db / 20.0)
    hole_count = np.zeros(offs.size, dtype=np.float64)
    used = np.zeros(offs.size, dtype=np.float64)

    for frame in range(n_frames):
        starts = offs + frame * stride
        if int(starts.max()) + WINDOW_LEN > len(x):
            break
        blocks = x[starts[:, None] + tap[None, :]] * window[None, :]
        spec = np.abs(blocks @ basis)
        ref = median_filter(spec, size=(1, ref_size), mode="nearest")
        # Near-silent frames carry no information and would read as all-holes.
        energetic = ref.mean(axis=1) > 1e-7
        hole_count += np.where(energetic, (spec < ref * thr).mean(axis=1), 0.0)
        used += energetic

    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(used > 0, hole_count / used, np.nan)


def alignment_stat(
    x: np.ndarray,
    sample_rate: int,
    window_kind: str = "kbd",
    coarse_frames: int = 3,
    fine_frames: int = 24,
    n_candidates: int = 24,
    n_baseline: int = 64,
) -> Tuple[float, int]:
    """Return ``(peak_ratio, best_offset)`` for one mono excerpt.

    ``peak_ratio`` is the test statistic: hole fraction at the best alignment,
    divided by the median hole fraction at unrelated alignments. ~1.0 means no
    alignment is special (the genuine-audio null).

    Two stages, because an exhaustive 24-frame scan of all 1024 offsets costs
    ~24 s per file — unusable in a library scan. The peak is sharp and strong
    enough that a 3-frame triage ranks the true alignment first on every AAC
    transcode measured; stage 2 then re-measures only the survivors, plus a
    spread of baseline offsets for the denominator, at full precision.

    Baseline offsets exclude the neighbourhood of every candidate on purpose:
    letting the peak contribute to its own denominator would flatten the
    statistic on exactly the files this is meant to catch.
    """
    window = kbd_window() if window_kind == "kbd" else sine_window()

    coarse = alignment_curve(x, sample_rate, window, n_frames=coarse_frames, ref_size=9)
    if not np.isfinite(coarse).any():
        return (float("nan"), -1)

    ranked = np.argsort(np.nan_to_num(coarse, nan=-1.0))[::-1]
    candidates = sorted(int(o) for o in ranked[:n_candidates])

    spread = np.linspace(0, HOP - 1, n_baseline * 2).astype(int)
    baseline = sorted({int(o) for o in spread if min(abs(int(o) - c) for c in candidates) > 4})
    baseline = baseline[:n_baseline]
    if not baseline:
        return (float("nan"), -1)

    fine = alignment_curve(
        x, sample_rate, window, n_frames=fine_frames, offsets=candidates + baseline
    )
    cand_vals = fine[: len(candidates)]
    base_vals = fine[len(candidates) :]
    base_vals = base_vals[np.isfinite(base_vals)]
    if base_vals.size == 0 or not np.isfinite(cand_vals).any():
        return (float("nan"), -1)

    best_idx = int(np.nanargmax(np.nan_to_num(cand_vals, nan=-1.0)))
    peak = float(cand_vals[best_idx])
    median_base = float(np.median(base_vals))

    if median_base < MIN_BASELINE_HOLE_FRACTION:
        # Denominator too sparse to divide by — abstain rather than guess.
        logger.debug(
            "MDCT: abstaining, baseline hole fraction %.6f below %.4f "
            "(analysis band nearly empty)",
            median_base,
            MIN_BASELINE_HOLE_FRACTION,
        )
        return (float("nan"), -1)

    return (peak / median_base, candidates[best_idx])
