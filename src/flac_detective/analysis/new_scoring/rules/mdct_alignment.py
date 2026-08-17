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

Scope. Two transform hypotheses are tried, AAC's and Vorbis's — they share the
2048-sample long block and differ only in window shape. MP3 has different geometry
entirely and the cutoff rules already convict there. Opus is out of reach by
construction: CELT transforms at 48 kHz whatever the input, so any non-48k source
is resampled on the way in and back out, and resampling destroys the sample-exact
alignment. That was measured (1.26 against a 1.29 genuine baseline), not assumed.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from ..mdct import best_alignment_stat

logger = logging.getLogger(__name__)

# Calibration — measured, not guessed.
#
# Single hypothesis (KBD only, v1.9), 880 certified-genuine files (EAC/XLD/
# Audiochecker ripper log present): the audit corpus's 80 plus an 800-file sweep
# over the rest of the library (ml/wild_audit.py sample).
#
#     genuine  median 1.24   p99 1.41   p99.9 1.48   MAX 1.494   (n = 880)
#
# Two hypotheses (KBD + Vorbis, v1.10). Taking a max over two windows can only
# push the genuine baseline UP, so it was re-measured rather than assumed. On the
# audit corpus's 80 certified-genuine files (ml/probe, stop_at disabled):
#
#     genuine    median 1.28   p95 1.39   MAX 1.427   (n = 80)
#     vorbis q8  median 3.61   AUC 0.955
#     opus 256k  median 1.30   AUC 0.575   <- the null; see the module docstring
#     AAC (ffmpeg, 128/256/320 kbps)   median 13.6 – 21.5
#
# The second hypothesis cost 0.04 on the median and nothing at the maximum, which
# is the point: genuine audio has no preferred alignment under EITHER window.
#
# Both thresholds therefore sit in empty space rather than being squeezed against
# a tail: 2.0 is 40 % clear of the highest genuine file measured under the
# two-hypothesis search, 3.0 is more than double it.
#
# The honest reading of 0/880 is "up to 0.44 %" (Wilson-95), NOT "zero" — the
# same caveat Provir's benchmark attaches to its own clean rows.
RATIO_HARD = 3.0
RATIO_REVIEW = 2.0

# Deliberately calibrated so that Rule 13 ALONE reaches SUSPICIOUS (55) but never
# FAKE_CERTAIN (86). The evidence is strong — AUC 0.993 on 320 kbps AAC — but a
# conviction on a single rule is against this project's "protect authentic files
# first" line, and 0.44 % of a 10 000-file library is still 44 people wrongly
# accused. One very strong signal earns "look at this", not "you are guilty".
SCORE_HARD = 55
SCORE_REVIEW = 25

# Below this cutoff the spectral rules already have plenty to work with, and
# running a ~4 s analysis to confirm what Rule 2 said for free is not worth the
# scan time. Rule 13 exists for the case where the band is intact.
MIN_CUTOFF_HZ = 18000.0


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
    details: dict = {"mdct_peak_ratio": float("nan"), "mdct_offset": -1, "mdct_hypothesis": ""}

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

    if not np.isfinite(ratio):
        logger.debug("RULE 13: statistic not finite, abstaining")
        return 0, [], details

    logger.info("RULE 13: MDCT peak ratio %.2f at offset %d (%s window)", ratio, offset, hypothesis)

    if ratio >= RATIO_HARD:
        return (
            SCORE_HARD,
            [
                f"R13: MDCT quantisation grid detected ({hypothesis} window) — hole density "
                f"{ratio:.1f}x higher at frame alignment {offset} than at any other "
                f"(+{SCORE_HARD}pts)"
            ],
            details,
        )
    if ratio >= RATIO_REVIEW:
        return (
            SCORE_REVIEW,
            [
                f"R13: possible MDCT alignment structure ({ratio:.1f}x at offset {offset}, "
                f"{hypothesis} window) (+{SCORE_REVIEW}pts)"
            ],
            details,
        )
    return 0, [], details


def should_run_rule_13(cutoff_freq: float, current_score: int) -> bool:
    """Whether Rule 13 is worth its ~4 s on this file.

    Two gates, both about value rather than correctness — the rule is safe to run
    on anything:

    * ``cutoff_freq >= MIN_CUTOFF_HZ`` — below that the cheap spectral rules are
      already informative.
    * not already convicted — once the score is at FAKE_CERTAIN there is no
      verdict left to change.
    """
    from ..constants import SCORE_FAKE_CERTAIN

    return cutoff_freq >= MIN_CUTOFF_HZ and current_score < SCORE_FAKE_CERTAIN
