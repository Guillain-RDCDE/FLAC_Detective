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

Scope, stated plainly, and measured rather than assumed:

* **AAC and Vorbis are read**, both via the 2048-sample long block. They differ only
  in window shape, so the module tries both (see ``HYPOTHESES``). Reading Vorbis with
  AAC's window measures AUC 0.806; reading it with its own measures 0.984.
* **MP3 is not** — a hybrid polyphase filterbank plus an 18-point MDCT matches none
  of this geometry. The cutoff rules already convict there.
* **Opus is not, and cannot be.** CELT transforms at 48 kHz regardless of input, so
  a 44.1 kHz source is resampled up, encoded, decoded and resampled back down.
  Resampling destroys the sample-exact alignment the whole statistic rests on.
  Measured at Opus's own 960-sample geometry: 1.26 against a genuine baseline of
  1.29 — the null. This gap is physics, not a missing hypothesis, and no window
  choice will close it.
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
    window: np.ndarray = np.concatenate([rising, rising[::-1]]).astype(np.float32)
    return window


def sine_window(length: int = WINDOW_LEN) -> np.ndarray:
    """Sine window — MPEG's other standard long window."""
    n = np.arange(length)
    window: np.ndarray = np.sin(np.pi / length * (n + 0.5)).astype(np.float32)
    return window


def vorbis_window(length: int = WINDOW_LEN) -> np.ndarray:
    """Vorbis window: sin(pi/2 · sin²(pi/N · (n + 0.5))).

    Vorbis uses the same 2048-sample long block as AAC but a different window, and
    it transforms at the file's native rate — nothing resamples. So the alignment
    survives and only the window was wrong: measured on the exchange corpus, the
    statistic reads Vorbis at AUC 0.806 with the KBD window and **0.984** with this
    one. It also happens to read ffmpeg AAC at 0.971, so the two hypotheses overlap
    rather than partition.
    """
    n = np.arange(length)
    window: np.ndarray = np.sin(np.pi / 2 * np.sin(np.pi / length * (n + 0.5)) ** 2).astype(
        np.float32
    )
    return window


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
    basis: np.ndarray = np.cos(np.pi / half * (n + 0.5 + half / 2) * (k + 0.5)).astype(np.float32)
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
        no_offsets: np.ndarray = np.empty(0)
        return no_offsets

    usable = len(x) - WINDOW_LEN - int(offs.max())
    if usable <= 0:
        empty_result: np.ndarray = np.full(offs.size, np.nan)
        return empty_result
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
        curve: np.ndarray = np.where(used > 0, hole_count / used, np.nan)
        return curve


# Transform hypotheses tried, in order. Each is (name, window factory).
#
# Only the window differs: AAC and Vorbis share the 2048-sample long block, so one
# basis serves both. Opus is deliberately absent and that is a measurement, not an
# omission — CELT transforms at 48 kHz whatever you feed it, so a 44.1 kHz source is
# resampled up, encoded, decoded and resampled back. Resampling destroys the
# sample-exact alignment this statistic depends on, and no window can recover it.
# Measured: Opus reads 1.26 against a genuine baseline of 1.29 at its own 960-sample
# geometry — the null. That gap is physics, not a missing hypothesis.
HYPOTHESES = (("kbd", kbd_window), ("vorbis", vorbis_window))

# ========== WHY THIS COUNT IS A CONSTANT AND NOT JUST len(HYPOTHESES) ==========
#
# ``best_alignment_stat`` returns the strongest reading across hypotheses, which
# makes the shipped statistic a MAXIMUM OVER DRAWS. A maximum does not converge as
# draws are added — it creeps upward forever. Jamie Dodd of Provir spotted this in
# v1.10's own release numbers, in the digit nobody was looking at: the genuine
# ceiling moved 1.42 -> 1.427 when the second hypothesis landed. That is not noise,
# it is the mechanism, and the measurement confirms it — across 80 certified-genuine
# files the two hypotheses split the maximum 33/47, so they compete for it on
# essentially every file.
#
# The consequence that matters: RATIO_REVIEW (2.0) and RATIO_HARD (3.0) in
# rules/mdct_alignment.py were calibrated against a genuine population measured
# under a specific number of hypotheses. Adding a third would raise the genuine
# ceiling again, toward bars that were set when there were fewer draws — silently,
# and in the one direction that costs authentic files.
#
# So the count is pinned here and asserted in tests/test_mdct.py. Adding a
# hypothesis is not forbidden; adding one *without re-certifying the genuine
# baseline* is. The test failure is the reminder.
CERTIFIED_HYPOTHESIS_COUNT = 2

# ========== THE RE-CERTIFICATION, AND WHAT IT OVERTURNED ==========
#
# Measured on 877 certified-genuine files under exactly the shipped configuration
# — both hypotheses, no early stop, per-hypothesis values recorded rather than
# only the winner (ml/recert_880.csv).
#
#     median 1.269   p99 1.449   p99.9 1.614   MAX 2.418
#
# Two things came out of it, and neither was the thing being looked for.
#
# 1. The creep Jamie predicted is real in principle and measures EXACTLY ZERO
#    here. The single highest genuine file tops out under KBD alone (2.418
#    against its own Vorbis reading of 1.869), so taking the maximum over
#    hypotheses added nothing to the ceiling. The 33/47 split of which hypothesis
#    wins is real, but it happens in the body of the distribution, not the tail.
#
# 2. The previously published calibration was WRONG, and by more than the creep
#    would have been. It claimed "not one genuine file in 880 reached 1.5" and a
#    review bar "34 % clear of the highest genuine file ever measured". Measured
#    properly: 2 files in 877 exceed 1.5 and one reaches 2.418. The old figure
#    (1.494) was a lucky draw of the 800-file library sample, not a property of
#    the population — the exact error Provir's "price eligibility, not the
#    observed rate" lesson describes, applied to a calibration instead of a
#    conviction.
#
# So the bars are calibrated against a QUANTILE now, not a sample maximum. A max
# over a finite sample is a lower bound on the population max and cannot be
# extrapolated; a high quantile can. This is what Jamie proposed, arrived at from
# his own permutation nulls walking as N grew.
#
# ADMISSION PASS 2026-08-20 (ml/recert_admission_pass.py, ml/recert_admission.csv):
# the 877 above were measured with no cutoff filter, while should_run_rule_13
# refuses anything under 18 kHz — the week's species, "a statistic computed
# across a population the rule cannot read". Measured rather than argued:
# 22/877 certified files (2.5 %) sit under the floor, and the ADMITTED
# population reads median 1.269 · p99 1.447 · p99.9 1.634 · max 2.418. The
# review bar keeps 22 % clearance over the admitted p99.9 (was quoted as 24 %
# over the all-certified one); measured exceedance 1/855 = 0.12 %
# (all-certified: 1/877 = 0.11 %); hard-bar exceedance zero on both. No
# constant moves — but the next recalibration starts from the admitted
# population, and quotes both.
CERTIFIED_GENUINE_P999 = 1.614
CERTIFIED_GENUINE_ADMITTED_P999 = 1.634
CERTIFIED_GENUINE_MAX = 2.418

# Measured exceedance of RATIO_REVIEW on that corpus: 1/877 = 0.11 %
# (Wilson-95 upper bound 0.64 %). Stated rather than hidden, because the honest
# claim is "one genuine file in a thousand draws a review", not "none ever do".
#
# Why that is acceptable rather than a defect: a lone Rule 13 review contributes
# SCORE_REVIEW (25), which is BELOW SCORE_WARNING (31). A genuine outlier at the
# review bar therefore cannot flag its own file — something independent has to
# fire too, and a conviction needs a second evidence family on top of that. The
# safety argument rests on that arithmetic, not on the tail being empty.
CERTIFIED_REVIEW_EXCEEDANCE = 0.0064


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
    factory = {"kbd": kbd_window, "sine": sine_window, "vorbis": vorbis_window}[window_kind]
    window = factory()

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


def best_alignment_stat(
    x: np.ndarray,
    sample_rate: int,
    stop_at: float = 3.0,
) -> Tuple[float, int, str]:
    """Try each transform hypothesis and return the strongest reading.

    Returns ``(peak_ratio, best_offset, hypothesis_name)``.

    Encoders do not share a window. Reading a Vorbis transcode with AAC's KBD window
    measures it at AUC 0.806; reading it with its own window measures 0.984. Since a
    file's provenance is exactly what is unknown, the honest move is to try both and
    keep the strongest — the genuine null is the same under either window (max 1.51
    across 60 genuine files), so trying more hypotheses costs specificity nothing.

    ``stop_at`` short-circuits once a hypothesis is already conclusive, which keeps
    the common AAC case at its old cost instead of doubling it.
    """
    best = (float("nan"), -1, "none")
    for name, _ in HYPOTHESES:
        ratio, offset = alignment_stat(x, sample_rate, window_kind=name)
        if np.isfinite(ratio) and (not np.isfinite(best[0]) or ratio > best[0]):
            best = (ratio, offset, name)
        if np.isfinite(ratio) and ratio >= stop_at:
            break
    return best
