"""Rule 15: joint-stereo dead runs — the second witness that never scores.

The strongest independent observable this engine holds
------------------------------------------------------
Re-measured in v1.11.2 against a genuine population of 228 files whose 95th
percentile is 1.74, at the shipped bar of 2.0:

    opus_256    fires 92 %
    vorbis_q8   fires 93 %
    mp3_320     fires 92 %
    mp3_V0      fires 81 %
    aacmf_256   fires 73 %
    aac_ff320   fires 19 %
    genuine     fires  5 %   (by construction — the bar is p95)

Better than the temporal family on every arm, and better than anything else this
engine has on Opus, Vorbis and high-bitrate MP3. And still complementary rather
than superior: `aac_ff320` is the one arm it barely reaches, against Rule 13's
0.99 there, so the alignment family remains the only one that reads ffmpeg AAC.
That division of labour is why the max-over-frames variant was rejected in
v1.11.2 — it bought aac_ff320 recall that Rule 13 already owns, with Opus and
Vorbis recall that nothing else in this engine can replace.

Why it also contributes ZERO points
------------------------------------
Same reasoning as Rule 14, and the same measurement. As a pointless witness it adds
**0 new false convictions** across 258 genuine files at every bar from 1.87 to 8.0.
Awarding it points would repeat the mechanism v1.10 removed: a second family that
also pushes mid-scoring genuine recordings past ``CONVICTION_MIN_SCORE``.

So it can complete a corroboration for a file other evidence has already carried
past the bar, and it cannot move any file toward that bar.

The gate that is not optional
------------------------------
Mono material has no side channel, so every high bin is trivially dead and the
statistic manufactures a maximal reading out of nothing. Provir came within a few
units of convicting a legitimate mono master that way. ``side_dead_run`` returns
NaN below ``MONO_GATE`` and this rule then declines to testify — the correct
behaviour being silence, not a low score, because a low score is still an opinion.

20 of our own 258 genuine files are mono-gated, so the case is not hypothetical.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np

from ..stereo_image import side_dead_run

logger = logging.getLogger(__name__)

# Calibrated on the genuine arm ALONE, and RE-confirmed in v1.11.2 on 228 measured
# genuine files (20 more mono-gated): p95 = 1.74. The bar sits just above it, where
# ~5 % of real music testifies and has nothing to corroborate.
#
# RE-VERIFIED 2026-08-21 after the corpus purge (32 taper-documented lossy files
# quarantined from the "genuine" wild corpus — ml/recal_clean228.py): clean p95
# = 1.94. The quarantined files were pulling the p95 DOWN (they read like
# genuine here, median 1.00), so the shipped margin was UNDER-stated. The bar
# holds; the margin is 2.0 vs 1.94 and is now measured on a clean population.
#
# Measured new false convictions at this bar and at p90, p99 and above the maximum:
# zero in every case.
#
# v1.11.2 also re-derived this against a max-over-frames variant of the statistic,
# whose own p95 is 27.6. That variant was rejected — a bar fitted to one aggregate
# is meaningless against another, and the two must move together or not at all.
RUN_BAR = 2.0

# Below this cutoff the file is band-limited and the 10 kHz band is empty anyway.
#
# Raised 12,000 -> 17,000 on 2026-08-31, and the reasoning above is why: it was
# already right and the constant was in the wrong place. Measured on 44 parked
# genuine sources given a 14 kHz roll-off and NOTHING else — no transcode, no
# re-encode — the engine convicted 15 of them, because the side channel falls
# under an absolute bar that the mid channel does not, the witness reports a dead
# side channel, and `spectral` plus `stereo` is two evidence families, which is
# what the corroboration gate asks for. Those files read a cutoff of 15,250 to
# 15,500 Hz: above the old gate, so they walked through it.
#
# The gap the new value sits in, measured before it was chosen:
#
#     genuine                 min 19,500      band-limited controls  median 15,500
#     mp3_320   min 19,250    aac_ff256 min 19,500
#     opus_256  min 19,500    vorbis_q8 min 19,500
#
# 17,000 is the round figure inside 15,500-19,250, 2,250 Hz below the lowest arm
# reading. Two repairs INSIDE the statistic were tried first and both were
# refused: restricting to live-MID bins (the mid channel is not dead on these
# files — live share 0.88-0.94, higher than a real mp3_320) and a dead test
# relative to the file's own side level (removes the artefact completely and
# costs 0.10 of arm-vs-genuine AUC against a 0.03 budget — the absolute bar is
# where this witness's signal lives). See
# ml/exchange/R15_DOMAIN_GATE_REGISTRATION_2026-08-31.md and its two predecessors.
#
# The cost, disclosed: the witness stops testifying about heavily band-limited
# transcodes (mp3_192, aac_ff128), which is Rule 1's domain — they are convicted
# on the wall itself.
MIN_CUTOFF_HZ = 17000.0


def apply_rule_15_stereo_seam(
    file_path: str,
    cutoff_freq: float,
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None,
) -> Tuple[int, List[str], dict]:
    """Apply Rule 15. Returns ``(0, reasons, details)`` — always zero points."""
    details: dict = {
        "stereo_dead_run": float("nan"),
        "stereo_ratio": float("nan"),
        "stereo_witness": False,
    }

    if audio_data is None or sample_rate is None:
        return 0, [], details
    if cutoff_freq < MIN_CUTOFF_HZ:
        return 0, [], details

    try:
        run, ratio = side_dead_run(audio_data, int(sample_rate))
    except Exception as exc:
        logger.warning("RULE 15: stereo dead-run failed: %s", exc)
        return 0, [], details

    details["stereo_dead_run"] = float(run)
    details["stereo_ratio"] = float(ratio)
    if not np.isfinite(run) or run < RUN_BAR:
        return 0, [], details

    details["stereo_witness"] = True
    logger.info("RULE 15: side-channel dead run %.1f bins — witness", run)
    return (
        0,
        [
            f"R15: the stereo side channel dies in runs of {run:.0f} bins above "
            f"10 kHz — independent witness, no points"
        ],
        details,
    )
