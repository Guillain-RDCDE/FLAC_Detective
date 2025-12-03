"""Scoring rules for FLAC fake detection."""

import logging
from typing import List, Optional, Tuple
from pathlib import Path
import soundfile as sf

from .constants import (
    HIGH_BITRATE_THRESHOLD,
    VARIANCE_THRESHOLD,
    SEUIL_BITRATE_APPARENT_ELEVE,
)
from .bitrate import estimate_mp3_bitrate, get_cutoff_threshold
from .silence import (
    analyze_silence_ratio,
    detect_vinyl_noise,
    detect_clicks_and_pops
)
from ..spectrum import analyze_segment_consistency

logger = logging.getLogger(__name__)


def apply_rule_1_mp3_bitrate(
    cutoff_freq: float, 
    container_bitrate: float,
    cutoff_std: float = 0.0
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

    Returns:
        Tuple of ((score_delta, list_of_reasons), estimated_bitrate)
    """
    score = 0
    reasons: List[str] = []
    
    # Safety check 1: If cutoff > 21 kHz, it's likely an authentic high-quality FLAC
    # MP3s never have cutoffs above 21 kHz (even 320 kbps tops out around 20.5 kHz)
    HIGH_QUALITY_CUTOFF_THRESHOLD = 21000
    
    if cutoff_freq > HIGH_QUALITY_CUTOFF_THRESHOLD:
        logger.debug(
            f"RULE 1: Skipped (cutoff {cutoff_freq:.0f} Hz > {HIGH_QUALITY_CUTOFF_THRESHOLD} Hz, likely authentic FLAC)"
        )
        return (score, reasons), None

    # Safety check 2: Variance check
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
        320: (700, 950),
    }

    if estimated_bitrate in mp3_ranges:
        min_br, max_br = mp3_ranges[estimated_bitrate]
        
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


def apply_rule_7_silence_analysis(
    file_path: str,
    cutoff_freq: float,
    sample_rate: int
) -> Tuple[int, List[str], Optional[float]]:
    """Apply Rule 7: Silence Analysis and Vinyl Noise Detection (IMPROVED - 3 PHASES).

    Analyzes audio to distinguish between:
    - Converted MP3s (artificial dither in silence)
    - Authentic FLACs (natural silence)
    - Authentic vinyl rips (surface noise)

    Only applied if cutoff frequency is in the ambiguous zone (19-21.5 kHz).

    PHASE 1 - Dither Test (existing):
        +50 points if ratio > 0.3 (TRANSCODE - Dither detected)
        -50 points if ratio < 0.15 (AUTHENTIC - Natural silence)
        0 points if 0.15 <= ratio <= 0.3 (UNCERTAIN -> Phase 2)

    PHASE 2 - Vinyl Noise Detection (NEW):
        Activated if Phase 1 gives 0 points (uncertain zone)
        Analyzes noise characteristics above cutoff frequency
        -40 points if vinyl noise detected (AUTHENTIC vinyl)
        +20 points if no noise (DIGITAL upsample suspect)
        0 points if noise with pattern (UNCERTAIN -> Phase 3)

    PHASE 3 - Clicks & Pops (OPTIONAL):
        Activated if vinyl noise detected in Phase 2
        Counts brief transients typical of vinyl
        -10 points if 5-50 clicks/min (CONFIRMS vinyl)
        0 points otherwise

    Total Score Range: -100 to +70 points

    Args:
        file_path: Path to the FLAC file
        cutoff_freq: Detected cutoff frequency in Hz
        sample_rate: Sample rate in Hz

    Returns:
        Tuple of (score_delta, list_of_reasons, silence_ratio)
    """
    score = 0
    reasons = []
    ratio = None

    # 1. Check activation condition
    # Zone ambiguë : 19 kHz à 21.5 kHz
    MIN_AMBIGUOUS_FREQ = 19000
    MAX_AMBIGUOUS_FREQ = 21500

    if not (MIN_AMBIGUOUS_FREQ <= cutoff_freq <= MAX_AMBIGUOUS_FREQ):
        logger.debug(
            f"RULE 7: Skipped (cutoff {cutoff_freq:.0f} Hz outside ambiguous range "
            f"{MIN_AMBIGUOUS_FREQ}-{MAX_AMBIGUOUS_FREQ} Hz)"
        )
        return score, reasons, ratio

    logger.info("RULE 7: Activation - Analyzing silences and vinyl characteristics...")

    # ========== PHASE 1: DITHER TEST ==========
    # ========== PHASE 1: DITHER TEST ==========
    # analyze_silence_ratio is imported at module level
    
    ratio, status, _, _ = analyze_silence_ratio(file_path)

    if ratio is None:
        logger.info(f"RULE 7 Phase 1: Analysis failed or skipped ({status})")
        return score, reasons, ratio

    # Interpret ratio
    if ratio > 0.3:
        score += 50
        reasons.append(
            f"R7-P1: Dither artificiel détecté dans les silences (Ratio {ratio:.2f} > 0.3) (+50pts)"
        )
        logger.info(f"RULE 7 Phase 1: +50 points (TRANSCODE - Ratio {ratio:.2f} > 0.3)")
        return score, reasons, ratio  # Stop here, clear transcode
    
    elif ratio < 0.15:
        score -= 50
        reasons.append(
            f"R7-P1: Silence naturel propre (Ratio {ratio:.2f} < 0.15) (-50pts)"
        )
        logger.info(f"RULE 7 Phase 1: -50 points (AUTHENTIC - Ratio {ratio:.2f} < 0.15)")
        return score, reasons, ratio  # Stop here, clear authentic
    
    else:
        # UNCERTAIN ZONE (0.15 <= ratio <= 0.3) -> Continue to Phase 2
        logger.info(
            f"RULE 7 Phase 1: Ratio {ratio:.2f} in uncertain zone (0.15-0.3) -> Proceeding to Phase 2"
        )

    # ========== PHASE 2: VINYL NOISE DETECTION ==========
    # ========== PHASE 2: VINYL NOISE DETECTION ==========
    # detect_vinyl_noise is imported at module level
    
    try:
        audio_data, sr = sf.read(file_path)
        is_vinyl, vinyl_details = detect_vinyl_noise(audio_data, sr, cutoff_freq)
        
        if is_vinyl:
            # Vinyl noise detected -> Authentic vinyl rip
            score -= 40
            reasons.append(
                f"R7-P2: Bruit vinyle détecté (énergie={vinyl_details['energy_db']:.1f}dB, "
                f"autocorr={vinyl_details['autocorr']:.2f}) (-40pts)"
            )
            logger.info(
                f"RULE 7 Phase 2: -40 points (VINYL DETECTED - "
                f"energy={vinyl_details['energy_db']:.1f}dB)"
            )
            
            # ========== PHASE 3: CLICKS & POPS (OPTIONAL) ==========
            # ========== PHASE 3: CLICKS & POPS (OPTIONAL) ==========
            # detect_clicks_and_pops is imported at module level
            
            num_clicks, clicks_per_min = detect_clicks_and_pops(audio_data, sr)
            
            if 5 <= clicks_per_min <= 50:
                # Typical vinyl click rate -> Confirms vinyl
                score -= 10
                reasons.append(
                    f"R7-P3: Clicks vinyle détectés ({clicks_per_min:.1f} clicks/min) (-10pts)"
                )
                logger.info(
                    f"RULE 7 Phase 3: -10 points (VINYL CONFIRMED - "
                    f"{clicks_per_min:.1f} clicks/min)"
                )
            else:
                logger.debug(
                    f"RULE 7 Phase 3: No vinyl clicks confirmation "
                    f"({clicks_per_min:.1f} clicks/min outside 5-50 range)"
                )
        
        elif vinyl_details['energy_db'] < -70:
            # No noise above cutoff -> Digital upsample suspect
            score += 20
            reasons.append(
                f"R7-P2: Pas de bruit au-dessus du cutoff (énergie={vinyl_details['energy_db']:.1f}dB) "
                f"-> Upsampling digital suspect (+20pts)"
            )
            logger.info(
                f"RULE 7 Phase 2: +20 points (NO NOISE - "
                f"digital upsample suspect, energy={vinyl_details['energy_db']:.1f}dB)"
            )
        
        else:
            # Noise present but with pattern (not vinyl-like)
            reasons.append(
                f"R7-P2: Bruit avec pattern détecté (autocorr={vinyl_details['autocorr']:.2f}) "
                f"-> Incertain (0pts)"
            )
            logger.info(
                f"RULE 7 Phase 2: 0 points (UNCERTAIN - "
                f"noise with pattern, autocorr={vinyl_details['autocorr']:.2f})"
            )
    
    except Exception as e:
        logger.error(f"RULE 7 Phase 2/3: Error during vinyl analysis: {e}")
        # If Phase 2 fails, just return Phase 1 result (0 points)
        reasons.append("R7-P2: Analyse vinyle échouée (0pts)")

    logger.info(f"RULE 7: Total score = {score:+d} points")
    
    return score, reasons, ratio


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


def apply_rule_9_compression_artifacts(
    file_path: str,
    cutoff_freq: float,
    mp3_bitrate_detected: Optional[int]
) -> Tuple[int, List[str], dict]:
    """Apply Rule 9: Psychoacoustic Compression Artifacts Detection.

    Detects lossy compression signatures beyond simple frequency cutoff:
    - Test 9A: Pre-echo artifacts (MDCT ghosting before transients)
    - Test 9B: High-frequency aliasing (filterbank artifacts)
    - Test 9C: MP3 quantization noise patterns

    This rule activates ONLY if:
    - cutoff_freq < 21000 Hz (suspicious zone), OR
    - Rule 1 detected an MP3 signature

    Scoring (cumulative, max +40 points):
        Test 9A (Pre-echo):
            - >10% transients affected: +15 points
            - 5-10% affected: +10 points
            - <5%: 0 points
        
        Test 9B (HF Aliasing):
            - Correlation > 0.5: +15 points (strong aliasing)
            - Correlation 0.3-0.5: +10 points (moderate aliasing)
            - Correlation < 0.3: 0 points
        
        Test 9C (MP3 Noise Pattern):
            - Pattern detected: +10 points
            - No pattern: 0 points

    Args:
        file_path: Path to the FLAC file
        cutoff_freq: Detected cutoff frequency in Hz
        mp3_bitrate_detected: Detected MP3 bitrate from Rule 1 (or None)

    Returns:
        Tuple of (score_delta, list_of_reasons, details_dict)
    """
    # Import here to avoid circular dependencies
    from .artifacts import analyze_compression_artifacts
    
    score, reasons, details = analyze_compression_artifacts(
        file_path,
        cutoff_freq,
        mp3_bitrate_detected
    )
    
    return score, reasons, details


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
        r1_res, _ = apply_rule_1_mp3_bitrate(cutoff, container_bitrate, 0.0)
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
            f"R10: Cutoffs instables (variance {variance:.0f} > 1000 Hz) -> Mastering dynamique (-20pts)"
        )
        logger.info(f"RULE 10: -20 points (High variance {variance:.0f} Hz)")

    # 2. Single problematic segment -> Artifact -> Penalty
    elif problematic_segments == 1:
        score -= 30
        reasons.append(
            "R10: Un seul segment problématique détecté -> Artefact ponctuel (-30pts)"
        )
        logger.info("RULE 10: -30 points (Single problematic segment)")

    # 3. Consistent segments -> Confirmation -> 0 points
    elif variance < 500:
        # No score change, but log confirmation
        logger.info(f"RULE 10: 0 points (Consistent segments, variance {variance:.0f} < 500 Hz)")
        # Optionally add a reason if it confirms a fake
        if current_score > 50:
            reasons.append(f"R10: Cohérence multi-segments confirmée (variance {variance:.0f} Hz)")

    return score, reasons
