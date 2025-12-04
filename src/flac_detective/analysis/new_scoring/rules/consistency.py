"""Consistency analysis rules (Rule 10)."""

import logging
from typing import List, Tuple
from pathlib import Path

from ...spectrum import analyze_segment_consistency
from .spectral import apply_rule_1_mp3_bitrate, apply_rule_2_cutoff

logger = logging.getLogger(__name__)


def apply_rule_10_multi_segment_consistency(
    filepath: str,
    current_score: int,
    sample_rate: int,
    container_bitrate: float
) -> Tuple[int, List[str]]:
    """Apply Rule 10: Multi-Segment Consistency (NEW - PRIORITY 3).

    Validates that anomalies are consistent throughout the file.

    Method:
    1. Divide file into 5 segments (Start, 25%, 50%, 75%, End)
    2. Detect cutoff for each segment
    3. Analyze consistency

    Actions:
    - Cutoffs vary > 1000 Hz: -20 points (Dynamic mastering, not global transcoding)
    - Only one problematic segment (score > 50): -30 points (Local artifact)
    - All segments consistent (variance < 500 Hz): 0 points (Confirms transcoding or authenticity)

    Activation:
    - Only if current score > 30 (already suspect)

    Args:
        filepath: Path to the FLAC file
        current_score: Current accumulated score from other rules
        sample_rate: Sample rate in Hz
        container_bitrate: Container bitrate in kbps

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Activation condition
    if current_score <= 30:
        logger.debug(f"RULE 10: Skipped (current score {current_score} <= 30)")
        return score, reasons

    logger.info("RULE 10: Activation - Analyzing multi-segment consistency...")

    # Analyze segments
    # Returns list of cutoffs and their variance
    cutoffs, variance = analyze_segment_consistency(Path(filepath))

    if not cutoffs:
        logger.warning("RULE 10: Analysis failed (no cutoffs returned)")
        return score, reasons

    # Calculate score for each segment to identify "problematic" ones
    problematic_segments = 0
    segment_details = []

    for i, cutoff in enumerate(cutoffs):
        # Calculate segment score using Rule 1 and Rule 2 logic
        # Rule 1: MP3 detection (max 50 pts)
        r1_res, _ = apply_rule_1_mp3_bitrate(cutoff, container_bitrate, 0.0, sample_rate)
        r1_score = r1_res[0]

        # Rule 2: Low cutoff (max 30 pts)
        r2_score, _ = apply_rule_2_cutoff(cutoff, sample_rate)

        seg_score = r1_score + r2_score
        segment_details.append(f"S{i+1}:{cutoff:.0f}Hz({seg_score}pts)")

        if seg_score > 50:
            problematic_segments += 1

    logger.info(f"RULE 10: Segment analysis: {', '.join(segment_details)} | Variance: {variance:.1f} Hz")

    # Apply penalties/bonuses

    # 1. High variance -> Dynamic mastering -> Penalty
    if variance > 1000:
        score -= 20
        reasons.append(
            f"R10: Cutoff variance élevée ({variance:.0f} Hz) -> Mastering dynamique probable (-20pts)"
        )
        logger.info(f"RULE 10: -20 points (High variance {variance:.0f} Hz)")

    # 2. Local artifact (only 1 segment is problematic)
    elif problematic_segments == 1:
        score -= 30
        reasons.append(
            "R10: Anomalie locale détectée (1 seul segment problématique) -> Artefact probable (-30pts)"
        )
        logger.info("RULE 10: -30 points (Local artifact - 1 problematic segment)")

    # 3. Consistent transcoding (all segments problematic or low variance)
    elif variance < 500 and problematic_segments >= 3:
        # No score change, but confirms the diagnosis
        reasons.append(
            f"R10: Anomalie cohérente sur tout le fichier (Variance {variance:.0f} Hz)"
        )
        logger.info(f"RULE 10: 0 points (Consistent anomaly, variance {variance:.0f} Hz)")

    return score, reasons
