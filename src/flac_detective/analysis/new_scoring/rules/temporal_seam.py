"""Rule 14: the temporal seam — a witness that testifies without scoring.

Why this rule contributes ZERO points
--------------------------------------
The statistic is good where this engine is blind. Measured on 40 files per arm:
AUC 0.89 on `mp3_320` and **0.84 on `opus_256`**, the two arms where the hole
family and the lattice family are both dead — and 0.47 on `aac_ff320`, which Rule
13 reads at 0.99. Complementary, not better.

The obvious way to use it is the wrong one, and it was measured before it was
written. Awarding it 25 points — enough to qualify as a witness under
``MIN_FAMILY_CONTRIBUTION`` — creates **three new false convictions on this
project's own 258 genuine files**, at every threshold tried. Real recordings
scoring 52, 38 and 31 on spectral evidence are pushed over ``CONVICTION_MIN_SCORE``
by the appended points and then convicted by their own new second family. That is
exactly the mechanism v1.10 removed one level down, reappearing one level up.

So the family testifies and adds nothing:

* it can complete a corroboration for a file other evidence has *already* carried
  past the points bar;
* it cannot move any file toward that bar.

Measured with that wiring: **0 new false convictions** across the 258, at every
threshold from 0.55 to 0.708 — including the two genuine files already sitting
past 55 points on a single family, which read 0.415 and 0.323, far below the bar.

What it buys, on the same corpus: 12 files across 240 that were stuck at
SUSPICIOUS purely for want of a second source now convict, and **5 of the 7 blocked
Opus files** among them. The arm it was brought in for.

The production caveat, kept
----------------------------
Provir keeps this measurement-only because it fires on heavy HF limiting and dense
synthetic pads with no codec involved. That caveat is not dismissed here — it is
the reason for the zero. Roughly 8 % of genuine material crosses the bar, and on a
real recording that witness simply has nothing to corroborate, so it is inert. The
protection is structural rather than statistical: this engine separates *how many
points* from *how many sources*, which is what makes a noisy independent observable
safe to hold. Provir's does not, which is why the same statistic cannot be used the
same way there.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from ..temporal import temporal_seam

logger = logging.getLogger(__name__)

# Calibrated on the genuine arm ALONE, never against the fakes: the bar is a
# false-alarm budget, not a recall target.
#
#     258 genuine files (80 certified CD rips + 178 wild taper recordings)
#     median 0.374   p90 0.573   p95 0.651   p99 0.797   max 0.913
#
# The two populations agree closely — unlike Rule 13's, where the wild tail was
# heavier and a lucky sample produced a published calibration that was wrong.
SEAM_BAR = 0.60

# Below this cutoff the file is band-limited enough that the cheap spectral rules
# own it, and a "collapse" in the top octave means only that there is nothing there.
MIN_CUTOFF_HZ = 15000.0


def apply_rule_14_temporal_seam(
    file_path: str,
    cutoff_freq: float,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[int, List[str], dict]:
    """Apply Rule 14. Returns ``(0, reasons, details)`` — always zero points.

    ``details['temporal_witness']`` is the output that matters: True when the
    family may be counted as an independent source. The score is zero by design,
    not by accident, and ``tests/test_rule14_temporal.py`` pins that.
    """
    details: dict = {
        "temporal_seam": float("nan"),
        "temporal_seam_hz": float("nan"),
        "temporal_witness": False,
    }

    if audio_data is None or sample_rate is None:
        return 0, [], details
    if cutoff_freq < MIN_CUTOFF_HZ:
        return 0, [], details

    try:
        mono = audio_data if audio_data.ndim == 1 else np.mean(audio_data, axis=1)
        score, where = temporal_seam(np.ascontiguousarray(mono, dtype=np.float32), int(sample_rate))
    except Exception as exc:
        logger.warning("RULE 14: temporal seam failed: %s", exc)
        return 0, [], details

    details["temporal_seam"] = float(score)
    details["temporal_seam_hz"] = float(where)
    if not np.isfinite(score) or score < SEAM_BAR:
        return 0, [], details

    details["temporal_witness"] = True
    logger.info("RULE 14: temporal seam %.2f at %.0f Hz — witness", score, where)
    return (
        0,
        [
            f"R14: high-frequency variation collapses at {where:.0f} Hz "
            f"({score:.2f}) — independent witness, no points"
        ],
        details,
    )
