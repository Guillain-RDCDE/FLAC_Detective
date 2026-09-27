"""Rule 16: the MP3 frame grid — a witness that never scores (v1.19.0).

Reads the decoded audio back through the MPEG-1 Layer III analysis
filterbank (``mp3_grid``) and asks whether one of the 576 granule alignments
shows the holes an MP3 encoder's zero-quantised lines leave. Independent of
the cutoff: it does not read where the spectrum stops.

Why a witness and not points
----------------------------
Same measured reasoning as Rules 14 and 15. A witness completes a
corroboration for a file other evidence has already carried to
``CONVICTION_MIN_SCORE``; it cannot move any file toward that bar. And the
one genuine file of the audit corpus that reads a strong grid (Mondkopf,
peak 8.1) is exactly why that matters: two independent readings of it — a
hard 19 kHz wall and this grid — now say MP3, and it still cannot be
convicted by this rule, because it has no points. Whether it is an MP3-sourced
master is a question for its provenance, not for the detector (a verdict is
never a label).

When it runs
------------
Only where it can change a verdict: a file already at or above
``CONVICTION_MIN_SCORE`` with fewer than ``CONVICTION_MIN_FAMILIES``
families. Everywhere else its reading could not move anything, and the
filterbank pass costs several seconds. See the calculator.

See ml/exchange/MP3_GRID_REGISTRATION_2026-09-27.md.
"""

from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

import numpy as np

from ..mp3_grid import grid_peak_ratio

logger = logging.getLogger(__name__)

# The hole fraction at the best alignment over its median across all 576.
# Set on 291 labelled genuine files outside the audit corpus: every one under
# 1.50 but three that read a grid as strong as a real MP3 (named in the
# registration, counted as genuine). Depth and granule count were chosen on the
# development half of the audit corpus; the held-out half reads AUC 0.96-1.00
# on the four MP3 arms and chance on AAC and Vorbis.
GRID_BAR = 1.6


def apply_rule_16_mp3_grid(
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[int, List[str], dict]:
    """Apply Rule 16. Returns ``(0, reasons, details)`` — always zero points."""
    details: dict = {"mp3_grid_ratio": float("nan"), "mp3_grid_offset": -1, "mp3_witness": False}
    if audio_data is None or sample_rate is None:
        return 0, [], details
    try:
        ratio, offset = grid_peak_ratio(audio_data, int(sample_rate))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("RULE 16: MP3 grid failed: %s", exc)
        return 0, [], details
    details["mp3_grid_ratio"] = ratio
    details["mp3_grid_offset"] = offset
    if math.isnan(ratio) or ratio < GRID_BAR:
        return 0, [], details
    details["mp3_witness"] = True
    logger.info(
        "RULE 16: MP3 granule grid at alignment %d, peak ratio %.2f — witness", offset, ratio
    )
    return (
        0,
        [
            f"R16: the audio carries an MP3 granule grid (alignment {offset}, "
            f"holes {ratio:.1f}x the other alignments) — independent witness, no points"
        ],
        details,
    )
