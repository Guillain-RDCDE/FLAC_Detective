"""Bitrate analysis rules (Rule 3, Rule 4, Rule 5, Rule 6)."""

import logging
from typing import List, Optional, Tuple

from ..constants import (
    HIGH_BITRATE_THRESHOLD,
    VARIANCE_THRESHOLD,
    SEUIL_BITRATE_APPARENT_ELEVE,
)

logger = logging.getLogger(__name__)


def apply_rule_3_source_vs_container(
    mp3_bitrate_detected: Optional[int], bitrate_conteneur: float
) -> Tuple[int, List[str]]:
    """Apply Rule 3: Source Bitrate vs Container Bitrate.

    Detects files where the detected MP3 source bitrate is much lower than
    the FLAC container bitrate, proving it's a converted MP3.

    Scoring:
        +50 points if mp3_bitrate_detected exists AND bitrate_conteneur > 600 kbps

    Args:
        mp3_bitrate_detected: Detected MP3 bitrate from spectral analysis (or None)
        bitrate_conteneur: Physical bitrate of the FLAC file in kbps

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Container bitrate threshold
    # Using the constant defined in constants.py
    CONTAINER_THRESHOLD = SEUIL_BITRATE_APPARENT_ELEVE

    if mp3_bitrate_detected is not None and bitrate_conteneur > CONTAINER_THRESHOLD:
        score += 50
        reasons.append(
            f"R3: Source {mp3_bitrate_detected} kbps vs conteneur {bitrate_conteneur:.0f} kbps"
        )
        logger.info(
            f"RULE 3: +50 points (source {mp3_bitrate_detected} kbps vs container {bitrate_conteneur:.0f} kbps)"
        )

    return score, reasons


def apply_rule_4_24bit_suspect(
    bit_depth: int,
    mp3_bitrate_detected: Optional[int],
    cutoff_freq: float = 0.0,
    silence_ratio: Optional[float] = None
) -> Tuple[int, List[str]]:
    """Apply Rule 4: 24-bit Suspicious Files (MODIFIED WITH SAFEGUARDS).

    Detects 24-bit files with suspiciously low MP3 source bitrate.
    Authentic 24-bit FLAC files should have high bitrates (> 500 kbps) and
    high cutoff frequencies (> 19 kHz).

    Scoring:
        +30 points if ALL conditions are met:
        1. Bit depth = 24-bit
        2. MP3 source detected with bitrate < 500 kbps (Rule 1)
        3. Cutoff frequency < 19000 Hz (truly low for 24-bit)

    EXCEPTION (safeguard against false positives):
        If silence_ratio < 0.15 (vinyl noise detected by Rule 7): 0 points
        Reason: May be an authentic 24-bit vinyl rip with natural cutoff

    Args:
        bit_depth: Bits per sample (16 or 24)
        mp3_bitrate_detected: Detected MP3 bitrate from spectral analysis (or None)
        cutoff_freq: Detected cutoff frequency in Hz (default: 0.0)
        silence_ratio: Ratio from Rule 7 silence analysis (or None)

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Minimum expected bitrate for 24-bit files
    MIN_24BIT_BITRATE = 500

    # Maximum cutoff for suspicious 24-bit upscaling
    # Authentic 24-bit files typically have cutoff > 19 kHz
    MAX_SUSPICIOUS_CUTOFF = 19000

    is_24bit = bit_depth == 24
    has_low_mp3_source = mp3_bitrate_detected is not None and mp3_bitrate_detected < MIN_24BIT_BITRATE
    has_low_cutoff = cutoff_freq < MAX_SUSPICIOUS_CUTOFF

    # SAFEGUARD: Protect authentic vinyl rips
    # If Rule 7 detected vinyl noise (ratio < 0.15), skip this rule
    is_vinyl_rip = silence_ratio is not None and silence_ratio < 0.15

    if is_vinyl_rip:
        logger.debug(
            f"RULE 4: Skipped (vinyl rip detected: silence_ratio {silence_ratio:.2f} < 0.15)"
        )
        return score, reasons

    # Apply rule only if all conditions are met
    if is_24bit and has_low_mp3_source and has_low_cutoff:
        score += 30
        reasons.append(
            f"R4: 24-bit avec bitrate source {mp3_bitrate_detected} kbps et cutoff {cutoff_freq:.0f} Hz (upscale suspect)"
        )
        logger.info(
            f"RULE 4: +30 points (24-bit with MP3 source {mp3_bitrate_detected} kbps < {MIN_24BIT_BITRATE} "
            f"and cutoff {cutoff_freq:.0f} Hz < {MAX_SUSPICIOUS_CUTOFF})"
        )
    else:
        # Log why the rule didn't trigger
        if not is_24bit:
            logger.debug("RULE 4: Skipped (not 24-bit)")
        elif not has_low_mp3_source:
            logger.debug("RULE 4: Skipped (no low MP3 source detected)")
        elif not has_low_cutoff:
            logger.debug(
                f"RULE 4: Skipped (cutoff {cutoff_freq:.0f} Hz >= {MAX_SUSPICIOUS_CUTOFF} Hz, "
                f"acceptable for 24-bit)"
            )

    return score, reasons


def apply_rule_5_high_variance(
    real_bitrate: float, bitrate_variance: float
) -> Tuple[int, List[str]]:
    """Apply Rule 5: Avoid False Positives - High Variable Bitrate.

    Reduces score for files with high bitrate and high variance, which are
    characteristics of authentic FLAC files. FLAC uses variable bitrate encoding,
    so authentic files should show variance.

    Scoring:
        -40 points if bitrate > 1000 kbps AND variance > 100 kbps

    Args:
        real_bitrate: Actual file bitrate in kbps
        bitrate_variance: Standard deviation of bitrate across segments

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    is_high_bitrate = real_bitrate > HIGH_BITRATE_THRESHOLD
    is_high_variance = bitrate_variance > VARIANCE_THRESHOLD

    if is_high_bitrate and is_high_variance:
        score -= 40
        reasons.append(
            f"Authentic high variable bitrate: {real_bitrate:.0f} kbps, "
            f"variance {bitrate_variance:.0f} kbps (-40 pts)"
        )
        logger.debug(
            f"RULE 5: -40 points (bitrate {real_bitrate:.0f} > {HIGH_BITRATE_THRESHOLD} "
            f"and variance {bitrate_variance:.0f} > {VARIANCE_THRESHOLD})"
        )

    return score, reasons


def apply_rule_6_variable_bitrate_protection(
    mp3_bitrate_detected: Optional[int],
    bitrate_conteneur: float,
    cutoff_freq: float,
    bitrate_variance: float
) -> Tuple[int, List[str]]:
    """Apply Rule 6: Avoid False Positives - High Quality Protection (REINFORCED).

    Protects authentic high-quality FLAC files with multiple quality indicators.
    This rule is now more selective to avoid false negatives.

    Scoring:
        -30 points if ALL conditions are met:
        1. No MP3 signature detected
        2. bitrate_conteneur > 700 kbps (raised from 600)
        3. cutoff_freq >= 19000 Hz (substantial HF content)
        4. bitrate_variance > 50 kbps (natural VBR)

    Args:
        mp3_bitrate_detected: Detected MP3 bitrate from spectral analysis (or None)
        bitrate_conteneur: Physical bitrate of the FLAC file in kbps
        cutoff_freq: Detected cutoff frequency in Hz
        bitrate_variance: Standard deviation of bitrate across segments

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Thresholds for high-quality FLAC protection
    BITRATE_THRESHOLD = 700  # Raised from 600 kbps
    CUTOFF_THRESHOLD = 19000  # Minimum HF content
    VARIANCE_THRESHOLD = 50  # Minimum variance for natural VBR

    # Check all conditions
    is_variable_bitrate = mp3_bitrate_detected is None
    is_high_bitrate = bitrate_conteneur > BITRATE_THRESHOLD
    has_hf_content = cutoff_freq >= CUTOFF_THRESHOLD
    has_variance = bitrate_variance > VARIANCE_THRESHOLD

    # All conditions must be true
    if is_variable_bitrate and is_high_bitrate and has_hf_content and has_variance:
        score -= 30
        reasons.append(
            f"R6: Haute qualité confirmée (bitrate {bitrate_conteneur:.0f} kbps, "
            f"cutoff {cutoff_freq:.0f} Hz, variance {bitrate_variance:.0f} kbps) → Authentique (-30pts)"
        )
        logger.info(
            f"RULE 6: -30 points (high quality: bitrate {bitrate_conteneur:.0f} > {BITRATE_THRESHOLD}, "
            f"cutoff {cutoff_freq:.0f} >= {CUTOFF_THRESHOLD}, variance {bitrate_variance:.0f} > {VARIANCE_THRESHOLD})"
        )
    else:
        # Log why the rule didn't trigger
        if not is_variable_bitrate:
            logger.debug("RULE 6: Skipped (MP3 signature detected)")
        elif not is_high_bitrate:
            logger.debug(f"RULE 6: Skipped (bitrate {bitrate_conteneur:.0f} <= {BITRATE_THRESHOLD})")
        elif not has_hf_content:
            logger.debug(f"RULE 6: Skipped (cutoff {cutoff_freq:.0f} < {CUTOFF_THRESHOLD})")
        elif not has_variance:
            logger.debug(f"RULE 6: Skipped (variance {bitrate_variance:.0f} <= {VARIANCE_THRESHOLD})")

    return score, reasons
