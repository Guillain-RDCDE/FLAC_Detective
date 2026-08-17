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
