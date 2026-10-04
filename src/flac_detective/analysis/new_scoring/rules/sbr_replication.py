"""Rule 17: spectral band replication — the high band is a copy of a lower one.

What it reads is in ``..sbr``. What it means: the energy above the SBR crossover was
rebuilt by a decoder from the band below, so the file went through HE-AAC (v1 or
v2), mp3PRO or a relative, however full its spectrum looks. Every cutoff rule
reads that file as untouched, and issue #12's HE-AAC v2 128 kbps transcode read
AUTHENTIC 0.

It is its own evidence family, ``sbr``: it reads neither the cutoff, nor a frame
grid, nor the stereo image, nor temporal variance, but a phase relation between
subbands that only a copy produces. Like Rule 13 it scores in two tiers and can
therefore reach SUSPICIOUS on its own and FAKE_CERTAIN only with a second family.

Calibrated on the genuine population alone; see
ml/exchange/ISSUE12_CODEC_GRIDS_REGISTRATION_2026-10-04.md.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from ..sbr import replication_coherence

logger = logging.getLogger(__name__)

# 1,151 labelled genuine files: median 0.086, p99.9 0.232, max 0.363. The review
# bar sits above the maximum, the hard bar 2.4 times the p99.9.
COHERENCE_REVIEW = 0.40
COHERENCE_HARD = 0.55

SCORE_HARD = 55
SCORE_REVIEW = 25


def apply_rule_17_sbr_replication(
    file_path: str,
    cutoff_freq: float,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[int, List[str], dict]:
    """Apply Rule 17. Returns ``(score_delta, reasons, details)``; 0 when it cannot read."""
    details: dict = {"sbr_coherence": float("nan"), "sbr_shift": -1}
    if audio_data is None or sample_rate is None:
        return 0, [], details
    try:
        mono = audio_data if audio_data.ndim == 1 else np.mean(audio_data, axis=1)
        coherence, shift = replication_coherence(mono, int(sample_rate))
    except Exception as exc:
        logger.warning("RULE 17: replication reading failed: %s", exc)
        return 0, [], details

    details["sbr_coherence"] = float(coherence)
    details["sbr_shift"] = int(shift)
    if not np.isfinite(coherence):
        return 0, [], details
    logger.info("RULE 17: replication coherence %.3f at a %d-subband shift", coherence, shift)

    if coherence >= COHERENCE_HARD:
        return (
            SCORE_HARD,
            [
                f"R17: the high band is a copy of a lower one (SBR, as in HE-AAC) — phase "
                f"coherence {coherence:.2f} across a {shift}-subband shift (+{SCORE_HARD}pts)"
            ],
            details,
        )
    if coherence >= COHERENCE_REVIEW:
        return (
            SCORE_REVIEW,
            [
                f"R17: possible band replication (coherence {coherence:.2f} across a "
                f"{shift}-subband shift) (+{SCORE_REVIEW}pts)"
            ],
            details,
        )
    return 0, [], details
