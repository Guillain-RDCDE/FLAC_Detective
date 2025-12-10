"""Spectral analysis rules (Rule 1, Rule 2, Rule 8)."""

import logging
from typing import List, Optional, Tuple

from ..bitrate import estimate_mp3_bitrate, get_cutoff_threshold

logger = logging.getLogger(__name__)


def apply_rule_1_mp3_bitrate(
    cutoff_freq: float,
    container_bitrate: float,
    cutoff_std: float = 0.0,
    sample_rate: int = 44100,
    energy_ratio: float = 0.0
) -> Tuple[Tuple[int, List[str]], Optional[int]]:
    """Apply Rule 1: Constant MP3 Bitrate Detection (Spectral Estimation).

    Detects if the file's spectral cutoff matches a standard MP3 bitrate signature.
    This allows detecting MP3s recompressed as FLACs (Fake FLACs).

    Scoring:
        +50 points if estimated spectral bitrate matches a standard MP3 bitrate
        AND container bitrate is within expected range for that MP3 bitrate.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        container_bitrate: Physical bitrate of the FLAC file in kbps
        cutoff_std: Standard deviation of cutoff frequency
        sample_rate: Sample rate in Hz (default: 44100)
        energy_ratio: High frequency energy ratio (default: 0.0)

    Returns:
        Tuple of ((score_delta, list_of_reasons), estimated_bitrate)
    """
    score = 0
    reasons: List[str] = []

    # Safety check 1: Nyquist Exception (OPTIMAL)
    # If cutoff is >= 95% of Nyquist frequency, it's likely the anti-aliasing filter
    # of an authentic FLAC, not an MP3 signature
    nyquist_freq = sample_rate / 2.0
    nyquist_threshold = 0.95 * nyquist_freq

    if cutoff_freq >= nyquist_threshold:
        logger.debug(
            f"RULE 1: Skipped (cutoff {cutoff_freq:.0f} Hz >= 95% Nyquist {nyquist_threshold:.0f} Hz, "
            f"likely anti-aliasing filter)"
        )
        return (score, reasons), None

    # EXCEPTION CRITIQUE : Cutoff exactement 20 kHz (ENHANCED)
    # ==========================================================
    # Problème : FFT peut arrondir 20-21 kHz à 20000 Hz pile
    # Solutions :
    #   1. Test énergie résiduelle > 20 kHz (energy_ratio)
    #   2. Test variance nulle (cutoff_std)
    if cutoff_freq == 20000.0:
        # Test 1 : Énergie résiduelle au-dessus de 20 kHz (HIGH_FREQ_THRESHOLD)
        # Seuil minimal pour détecter présence d'énergie HF
        if energy_ratio > 0.000001:
            logger.info(f"RULE 1: Cutoff 20 kHz mais énergie HF = {energy_ratio:.6f}")
            logger.info("RULE 1: Probablement arrondi FFT, pas MP3 320k - SKIP")
            return (0, []), None

        # Test 2 : Variance nulle + cutoff pile = ambigu
        if cutoff_std == 0.0:
            logger.info("RULE 1: Cutoff exactement 20000 Hz avec variance 0")
            logger.info("RULE 1: Ambigu (peut être arrondi FFT) - SKIP par prudence")
            return (0, []), None

    # Safety check 2: If cutoff > 21.5 kHz, it's likely an authentic high-quality FLAC
    # MP3s never have cutoffs above 21.5 kHz (even 320 kbps tops out around 20.5-21 kHz)
    HIGH_QUALITY_CUTOFF_THRESHOLD = 21500

    if cutoff_freq > HIGH_QUALITY_CUTOFF_THRESHOLD:
        logger.debug(
            f"RULE 1: Skipped (cutoff {cutoff_freq:.0f} Hz > {HIGH_QUALITY_CUTOFF_THRESHOLD} Hz, likely authentic FLAC)"
        )
        return (score, reasons), None

    # Safety check 3: Variance check
    # Authentic FLACs often have variable cutoffs (high variance).
    # CBR MP3s have very stable cutoffs (low variance).
    CUTOFF_VARIANCE_THRESHOLD = 100.0  # Hz

    if cutoff_std > CUTOFF_VARIANCE_THRESHOLD:
        logger.debug(
            f"RULE 1: Skipped (cutoff std {cutoff_std:.1f} > {CUTOFF_VARIANCE_THRESHOLD}, variable spectrum)"
        )
        return (score, reasons), None

    estimated_bitrate = estimate_mp3_bitrate(cutoff_freq)

    if estimated_bitrate == 0:
        return (score, reasons), None

    # Check if container bitrate matches the estimated MP3 bitrate range
    # Plages typiques pour MP3 convertis en FLAC
    mp3_ranges = {
        128: (400, 550),
        160: (450, 650),
        192: (500, 750),
        224: (550, 800),
        256: (600, 850),
        320: (700, 1050),
    }

    if estimated_bitrate in mp3_ranges:
        min_br, max_br = mp3_ranges[estimated_bitrate]

        # EXCEPTION SPÉCIFIQUE 320 kbps : Si cutoff >= 94% Nyquist, c'est probablement légitime
        # Les vrais MP3 320 kbps ont un cutoff autour de 20-20.5 kHz (approx 93% de 22.05kHz)
        # Un cutoff > 94% Nyquist suggère un filtre anti-aliasing naturel
        if estimated_bitrate == 320:
            nyquist_freq = sample_rate / 2.0
            nyquist_limit_percent = 0.94 * nyquist_freq

            if cutoff_freq >= nyquist_limit_percent:
                logger.debug(
                    f"RULE 1: Skipped 320 kbps detection (cutoff {cutoff_freq:.0f} Hz >= 94% Nyquist "
                    f"{nyquist_limit_percent:.0f} Hz, likely legitimate high-quality file)"
                )
                return (score, reasons), None

        # Le bitrate conteneur est-il dans la plage attendue ?
        if min_br <= container_bitrate <= max_br:
            score += 50
            reasons.append(f"Constant MP3 bitrate detected (Spectral): {estimated_bitrate} kbps")
            logger.info(
                f"RULE 1: +50 points (cutoff {cutoff_freq:.0f} Hz ~= {estimated_bitrate} kbps MP3, "
                f"container {container_bitrate:.0f} kbps in range {min_br}-{max_br})"
            )
            return (score, reasons), estimated_bitrate
        else:
            logger.debug(
                f"RULE 1: Skipped (cutoff suggests {estimated_bitrate} kbps MP3, "
                f"but container bitrate {container_bitrate:.0f} kbps outside range {min_br}-{max_br})"
            )

    return (score, reasons), None


def apply_rule_2_cutoff(cutoff_freq: float, sample_rate: int) -> Tuple[int, List[str]]:
    """Apply Rule 2: Cutoff Frequency vs Sample Rate.

    Detects if the frequency cutoff is suspiciously low compared to what the sample
    rate should support. Authentic FLAC files should have frequency content up to
    near the Nyquist frequency (sample_rate / 2).

    Scoring:
        +0 to +30 points based on how far below the threshold the cutoff is
        Formula: min((threshold - cutoff) / 200, 30)

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        sample_rate: Sample rate in Hz

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []
    cutoff_threshold = get_cutoff_threshold(sample_rate)

    if cutoff_freq < cutoff_threshold:
        frequency_deficit = cutoff_threshold - cutoff_freq
        cutoff_penalty = min(frequency_deficit / 200, 30)
        score += int(cutoff_penalty)
        reasons.append(
            f"R2: Cutoff {cutoff_freq:.0f} Hz < {cutoff_threshold:.0f} Hz (+{cutoff_penalty:.0f}pts)"
        )
        logger.debug(
            f"RULE 2: +{cutoff_penalty:.0f} points "
            f"(cutoff {cutoff_freq:.0f} <threshold {cutoff_threshold:.0f})"
        )

    return score, reasons


def apply_rule_8_nyquist_exception(
    cutoff_freq: float,
    sample_rate: int,
    mp3_bitrate_detected: Optional[int],
    silence_ratio: Optional[float] = None
) -> Tuple[int, List[str]]:
    """Apply Rule 8: Nyquist Exception (ALWAYS APPLIED with Safeguards).

    Protects files with cutoff frequency near the theoretical Nyquist limit
    (sample_rate / 2). These are likely authentic FLACs with proper anti-aliasing
    filters or high-quality recordings.

    Scoring (ALWAYS calculated):
        - cutoff >= 0.98 × Nyquist: -50 points base (strong bonus)
        - 0.95 <= cutoff < 0.98 × Nyquist: -30 points base (moderate bonus)
        - cutoff < 0.95 × Nyquist: 0 points (no bonus)

    Safeguards (reduce or cancel bonus):
        - MP3 signature + silence_ratio > 0.2: Bonus CANCELLED (0 points)
        - MP3 signature + silence_ratio > 0.15: Bonus REDUCED to -15 points
        - MP3 signature + silence_ratio <= 0.15: Bonus APPLIED (authentic)
        - No MP3 signature: Bonus APPLIED (always)

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        sample_rate: Sample rate in Hz
        mp3_bitrate_detected: Detected MP3 bitrate from Rule 1 (or None)
        silence_ratio: Ratio from Rule 7 silence analysis (or None)

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Calculate Nyquist frequency
    nyquist_freq = sample_rate / 2.0

    # Calculate cutoff as percentage of Nyquist
    cutoff_ratio = cutoff_freq / nyquist_freq

    # STEP 1: Calculate base bonus based on cutoff ratio
    base_bonus = 0

    if cutoff_ratio >= 0.98:
        base_bonus = -50
        bonus_description = "Très proche limite"
    elif cutoff_ratio >= 0.95:
        base_bonus = -30
        bonus_description = "Probablement authentique"
    else:
        # No bonus for cutoff < 95% of Nyquist
        logger.debug(
            f"RULE 8: No bonus (cutoff {cutoff_freq:.0f} Hz = {cutoff_ratio*100:.1f}% of Nyquist, < 95%)"
        )
        return score, reasons

    # STEP 2: Apply safeguards if MP3 signature detected
    final_bonus = base_bonus

    if mp3_bitrate_detected is not None:
        # MP3 signature detected - check silence ratio
        if silence_ratio is not None and silence_ratio > 0.2:
            # Dither artificiel suspect - CANCEL bonus
            final_bonus = 0
            reasons.append(
                f"R8: Bonus Nyquist annulé (MP3 signature {mp3_bitrate_detected} kbps + "
                f"dither suspect {silence_ratio:.2f} > 0.2)"
            )
            logger.info(
                f"RULE 8: Bonus CANCELLED (MP3 {mp3_bitrate_detected} kbps + "
                f"silence ratio {silence_ratio:.2f} > 0.2)"
            )
        elif silence_ratio is not None and silence_ratio > 0.15:
            # Zone grise - REDUCE bonus
            final_bonus = -15
            reasons.append(
                f"R8: Cutoff à {cutoff_ratio*100:.1f}% de Nyquist "
                f"({cutoff_freq:.0f}/{nyquist_freq:.0f} Hz) → Bonus réduit "
                f"(MP3 signature + zone grise) (-15pts)"
            )
            logger.info(
                f"RULE 8: Bonus REDUCED to -15 points (MP3 {mp3_bitrate_detected} kbps + "
                f"silence ratio {silence_ratio:.2f} in grey zone)"
            )
        else:
            # Silence ratio <= 0.15 or None - APPLY bonus (authentic)
            reasons.append(
                f"R8: Cutoff à {cutoff_ratio*100:.1f}% de Nyquist "
                f"({cutoff_freq:.0f}/{nyquist_freq:.0f} Hz) → {bonus_description} "
                f"({base_bonus}pts, MP3 signature mais silence authentique)"
            )
            logger.info(
                f"RULE 8: {base_bonus} points (cutoff {cutoff_freq:.0f} Hz >= "
                f"{cutoff_ratio*100:.0f}% of Nyquist, MP3 signature but authentic silence)"
            )
    else:
        # No MP3 signature - APPLY bonus unconditionally
        reasons.append(
            f"R8: Cutoff à {cutoff_ratio*100:.1f}% de Nyquist "
            f"({cutoff_freq:.0f}/{nyquist_freq:.0f} Hz) → {bonus_description} ({base_bonus}pts)"
        )
        logger.info(
            f"RULE 8: {base_bonus} points (cutoff {cutoff_freq:.0f} Hz >= "
            f"{cutoff_ratio*100:.0f}% of Nyquist)"
        )

    score = final_bonus

    return score, reasons
