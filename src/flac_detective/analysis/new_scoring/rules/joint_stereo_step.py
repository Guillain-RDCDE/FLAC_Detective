"""Rule 18: the side-channel step — a stereo witness that testifies without scoring.

What it reads is in ``..joint_stereo``: the step down in side-to-mid energy left by
a coder that stops sending the difference above some frequency (Vorbis point
stereo at low quality, CELT intensity stereo at low bitrate). It belongs to the
``stereo`` family with Rule 15, because both read joint-stereo coding, and it is
wired exactly like Rule 15: zero points, a witness only.

That wiring is the safety argument, as it is for Rules 14 and 15. A genuine
recording whose stereo image happens to step down by that much offers a witness
with nothing to corroborate; the witness can complete a conviction only for a
file that another family has already carried past the points bar.

Unlike Rule 15 it has no cutoff gate: it reads only the bands under the file's
own cutoff, relative to the file's own stereo image, so a band-limited master has
no empty band to offer it. Issue #12's ``-q1`` file (cutoff 16,750 Hz) is the case
Rule 15's 17 kHz gate keeps it from seeing.

Calibrated on the genuine population alone; see
ml/exchange/ISSUE12_CODEC_GRIDS_REGISTRATION_2026-10-04.md.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from ..joint_stereo import side_step

logger = logging.getLogger(__name__)

# The genuine p95, as for Rule 15: 1,048 measured labelled genuine files (mono
# gated out), median 1.6 dB, p95 7.5, p99 12.1, max 34.5. About one genuine file
# in twenty offers this witness, with nothing to corroborate.
STEP_BAR_DB = 7.5


def apply_rule_18_side_step(
    file_path: str,
    cutoff_freq: float,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[int, List[str], dict]:
    """Apply Rule 18. Returns ``(0, reasons, details)`` — always zero points."""
    details: dict = {
        "side_step_db": float("nan"),
        "side_step_hz": float("nan"),
        "step_witness": False,
    }
    if audio_data is None or sample_rate is None or audio_data.ndim != 2:
        return 0, [], details
    try:
        cutoff = cutoff_freq if cutoff_freq and np.isfinite(cutoff_freq) else None
        step, where, _ = side_step(audio_data, int(sample_rate), cutoff)
    except Exception as exc:
        logger.warning("RULE 18: side-step reading failed: %s", exc)
        return 0, [], details

    details["side_step_db"] = float(step)
    details["side_step_hz"] = float(where)
    if not np.isfinite(step) or step < STEP_BAR_DB:
        return 0, [], details

    details["step_witness"] = True
    logger.info("RULE 18: side channel steps down %.1f dB at %.0f Hz — witness", step, where)
    return (
        0,
        [
            f"R18: the stereo side channel steps down {step:.0f} dB at {where:.0f} Hz "
            f"(joint-stereo coding) — independent witness, no points"
        ],
        details,
    )
