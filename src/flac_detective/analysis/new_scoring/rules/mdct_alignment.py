"""Rule 13: MDCT frame-alignment detection (the high-bitrate rule).

Where this fits. Rules 1–8 and 11 read the spectral cliff and what sits above it;
Rule 12's CNN reads a mel-spectrogram dominated by the same region. All of them
work at 128 kbps and all of them run out of signal at 256–320 kbps, because a
modern encoder at that rate keeps the band. That ceiling is measured, not
assumed: mp3_320 detectability AUC 0.53 (ml/README.md), and on a head-to-head
benchmark FLAC Detective flagged 28 % of 320 kbps AAC.

Rule 13 reads a different thing entirely: the alignment fingerprint left by MDCT
quantisation. See ``..mdct`` for the mechanism and its limits. The property that
matters operationally is that the statistic does not depend on the cutoff at all,
so it keeps working exactly where everything else stops.

Scope. Two transform hypotheses are tried on the mono mix, AAC's and Vorbis's —
they share the 2048-sample long block and differ only in window shape. MP3 has
different geometry entirely and the cutoff rules already convict there.

Since 2.1.0 (issue #12) two more readings are taken when those two do not reach
the hard bar, each with its own certified bars (see ``..codec_grids``):

* **Vorbis with block switching**, read on the left and right channels: a Vorbis
  encoder moves its long-block grid by multiples of 128 samples after every run
  of short blocks, and at high quality keeps its zeros per channel, not in the
  mix.
* **Opus (CELT)**, at 48 kHz with the decoder's de-emphasis undone. This module
  used to say Opus was "out of reach by construction" because resampling destroys
  the alignment. It was the de-emphasis filter, not the resampling: undone, the
  issue's Opus 64 kbps file reads 3.9 against its original's 1.1.

The rule still scores once: the strongest tier any reading reaches.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from ..codec_grids import celt_ratio, vorbis_switch_ratio
from ..mdct import best_alignment_stat

logger = logging.getLogger(__name__)

# Calibration — measured, re-measured, and corrected.
#
# RE-CERTIFIED over 877 certified-genuine files (EAC/XLD/Audiochecker ripper log
# present) under exactly the shipped configuration: both hypotheses, no early
# stop, per-hypothesis values recorded. See ml/recert_880.csv and ``..mdct``.
#
#     genuine    median 1.269   p99 1.449   p99.9 1.614   MAX 2.418   (n = 877)
#     vorbis q8  median 3.61    AUC 0.955
#     opus 256k  median 1.30    AUC 0.575   <- the null; see the module docstring
#     AAC — the encoder matters more than the bitrate:
#       ffmpeg (128/256/320)       median 13.6 – 21.5   fires ~always
#       MediaFoundation 256k       median  2.66         AUC 0.791
#       Apple CoreAudio 128/256/320  1.50 / 1.30 / 1.30   fires 13 % / 2 % / 0 %
#
# WHAT THE RE-CERTIFICATION OVERTURNED. The previous comment here claimed "not one
# genuine file in 880 reached 1.5" and a review bar "34 % clear of the highest
# genuine file ever measured". Both were wrong: 2 files in 877 exceed 1.5 and one
# reaches 2.418. The old 1.494 was a lucky draw of the library sample rather than
# a property of the population.
#
# It was NOT the max-over-hypotheses creep that broke it. That was the suspected
# cause — a maximum over draws does not converge — and it measures exactly zero
# here: the highest genuine file tops out under KBD alone (2.418 against its own
# Vorbis reading of 1.869).
#
# So the bars are set against the genuine p99.9 (1.614), not a sample maximum:
# 2.0 is 24 % clear of it, and 3.0 is 86 % clear. A maximum over a finite sample
# is a lower bound on the population max and cannot be extrapolated.
#
# MEASURED EXCEEDANCE, stated rather than hidden: 1/877 genuine files reach
# RATIO_REVIEW = 0.11 %, Wilson-95 upper bound 0.64 %. That is tolerable because
# SCORE_REVIEW (25) sits BELOW the WARNING threshold (31), so a lone genuine
# outlier at the review bar cannot flag its own file — something independent must
# fire too. The safety argument is that arithmetic, not an empty tail.
RATIO_HARD = 3.0
RATIO_REVIEW = 2.0

# Deliberately calibrated so that Rule 13 ALONE reaches SUSPICIOUS (55) but never
# FAKE_CERTAIN (86). The evidence is strong — AUC 0.993 on 320 kbps AAC — but a
# conviction on a single rule is against this project's "protect authentic files
# first" line, and 0.44 % of a 10 000-file library is still 44 people wrongly
# accused. One very strong signal earns "look at this", not "you are guilty".
SCORE_HARD = 55
SCORE_REVIEW = 25

# No cutoff gate any more (v1.20.1). It sat at 18 kHz on the argument that "below
# that the spectral rules already have plenty to work with". Issue #12 is the
# counter-example: Vorbis at -q1 on a loud master fills the band above its edge
# with noise (-35 dB, so no depth reading) and the edge wanders (gate A), so every
# sub-18 kHz instrument stepped aside and the file read AUTHENTIC 16 while this
# rule, never asked, reads 2.43. Measured under 18 kHz before the gate came off:
# 37 labelled and certified genuine files max 1.46; 45 78 rpm transfers (edges
# down to 2 kHz) max 1.40; 29 cassettes max 1.43
# (ml/exchange/R13_LOW_CUTOFF_REGISTRATION_2026-10-02.md). Kept as a name, at 0,
# so a caller that reads it still gets the truth.
MIN_CUTOFF_HZ = 0.0

# The two readings added in 2.1.0 have their own scales and their own bars,
# calibrated on the genuine population ALONE, never against the transcodes, and
# placed the way RATIO_REVIEW / RATIO_HARD are: review ~25-30 % clear of the
# genuine p99.9, hard ~85 % clear. Measured on 1,151 labelled genuine files
# (certified 877, v2 56, wild 144, attested 28, full-length 12, bench CDs 34):
#
#     Vorbis block-switch   median 1.110   p99.9 1.309   max 1.627   (n = 1,151)
#     CELT                  median 1.226   p99.9 1.720   max 1.925   (n = 1,131)
#
# None of them reaches either review bar. The two maxima are named in
# ml/exchange/ISSUE12_CODEC_GRIDS_REGISTRATION_2026-10-04.md.
VORBIS_SWITCH_REVIEW = 1.7
VORBIS_SWITCH_HARD = 2.4
CELT_REVIEW = 2.2
CELT_HARD = 3.2


def _points(ratio: float, review: float, hard: float) -> int:
    """SCORE_HARD, SCORE_REVIEW or 0 for one reading against its own bars."""
    if not np.isfinite(ratio):
        return 0
    if ratio >= hard:
        return SCORE_HARD
    if ratio >= review:
        return SCORE_REVIEW
    return 0


def apply_rule_13_mdct_alignment(
    file_path: str,
    cutoff_freq: float,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[int, List[str], dict]:
    """Apply Rule 13: MDCT frame-alignment detection.

    Args:
        file_path: Path to the audio being analysed (used only for logging).
        cutoff_freq: Detected spectral cutoff in Hz.
        audio_data: Pre-loaded audio, if the pipeline already has it in hand.
        sample_rate: Sample rate of ``audio_data``.

    Returns:
        ``(score_delta, reasons, details)``. Returns zero — never a penalty — when
        the statistic cannot be computed: an unreadable or too-short file is not
        evidence of anything.
    """
    details: dict = {
        "mdct_peak_ratio": float("nan"),
        "mdct_offset": -1,
        "mdct_hypothesis": "",
        "vorbis_switch_ratio": float("nan"),
        "celt_ratio": float("nan"),
    }

    if audio_data is None or sample_rate is None:
        logger.debug("RULE 13: no audio in hand, skipping")
        return 0, [], details

    try:
        mono = audio_data if audio_data.ndim == 1 else np.mean(audio_data, axis=1)
        mono = np.ascontiguousarray(mono, dtype=np.float32)
        ratio, offset, hypothesis = best_alignment_stat(mono, int(sample_rate))
    except Exception as exc:
        logger.warning("RULE 13: alignment analysis failed: %s", exc)
        return 0, [], details

    details["mdct_peak_ratio"] = float(ratio)
    details["mdct_offset"] = int(offset)
    details["mdct_hypothesis"] = hypothesis
    if np.isfinite(ratio):
        logger.info(
            "RULE 13: MDCT peak ratio %.2f at offset %d (%s window)", ratio, offset, hypothesis
        )

    points, reason = _original_tier(ratio, offset, hypothesis)
    # The 2.1.0 readings, only while they can still raise the tier.
    for name, read in (("vorbis-switch", _vorbis_switch_reading), ("celt", _celt_reading)):
        if points >= SCORE_HARD:
            break
        more, more_reason = read(audio_data, mono, int(sample_rate), details)
        if more > points:
            points, reason = more, more_reason
            details["mdct_hypothesis"] = name

    if points == 0:
        return 0, [], details
    return points, [reason], details


def _original_tier(ratio: float, offset: int, hypothesis: str) -> Tuple[int, str]:
    """Rule 13's own reading (mono, fixed grid, AAC or Vorbis window) against its bars."""
    points = _points(ratio, RATIO_REVIEW, RATIO_HARD)
    if points == SCORE_HARD:
        return points, (
            f"R13: MDCT quantisation grid detected ({hypothesis} window) — hole density "
            f"{ratio:.1f}x higher at frame alignment {offset} than at any other "
            f"(+{SCORE_HARD}pts)"
        )
    if points == SCORE_REVIEW:
        return points, (
            f"R13: possible MDCT alignment structure ({ratio:.1f}x at offset {offset}, "
            f"{hypothesis} window) (+{SCORE_REVIEW}pts)"
        )
    return 0, ""


def _vorbis_switch_reading(
    audio: np.ndarray, mono: np.ndarray, sample_rate: int, details: dict
) -> Tuple[int, str]:
    """The block-switching Vorbis grid on the left and right channels."""
    try:
        ratio, residue = vorbis_switch_ratio(np.asarray(audio), sample_rate)
    except Exception as exc:
        logger.warning("RULE 13: Vorbis block-switch reading failed: %s", exc)
        return 0, ""
    details["vorbis_switch_ratio"] = float(ratio)
    if np.isfinite(ratio):
        logger.info("RULE 13: Vorbis block-switch ratio %.2f (residue %d)", ratio, residue)
    points = _points(ratio, VORBIS_SWITCH_REVIEW, VORBIS_SWITCH_HARD)
    return points, (
        f"R13: Vorbis block grid detected on the left/right channels — hole density "
        f"{ratio:.1f}x higher on one grid, moving in 128-sample steps, than on any "
        f"other (+{points}pts)"
    )


def _celt_reading(
    audio: np.ndarray, mono: np.ndarray, sample_rate: int, details: dict
) -> Tuple[int, str]:
    """The CELT grid at 48 kHz with the decoder's de-emphasis undone."""
    try:
        ratio, offset = celt_ratio(mono, sample_rate)
    except Exception as exc:
        logger.warning("RULE 13: CELT reading failed: %s", exc)
        return 0, ""
    details["celt_ratio"] = float(ratio)
    if np.isfinite(ratio):
        logger.info("RULE 13: CELT ratio %.2f (offset %d at 48 kHz)", ratio, offset)
    points = _points(ratio, CELT_REVIEW, CELT_HARD)
    return points, (
        f"R13: Opus (CELT) frame grid detected — hole density {ratio:.1f}x higher "
        f"at one 20 ms alignment, read at 48 kHz with the decoder's de-emphasis "
        f"undone (+{points}pts)"
    )


def should_run_rule_13(cutoff_freq: float, current_score: int) -> bool:
    """Whether Rule 13 is worth its ~4 s on this file.

    One gate, about value rather than correctness — the rule is safe to run on
    anything: not already convicted, since once the score is at FAKE_CERTAIN there
    is no verdict left to change. The cutoff no longer decides (v1.20.1, see
    ``MIN_CUTOFF_HZ``); ``cutoff_freq`` is kept for the callers.
    """
    from ..constants import SCORE_FAKE_CERTAIN

    return cutoff_freq >= MIN_CUTOFF_HZ and current_score < SCORE_FAKE_CERTAIN
