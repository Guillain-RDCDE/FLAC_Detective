"""Silence analysis rules (Rule 7)."""

import logging
from typing import List, Optional, Tuple
import soundfile as sf

from ..silence import (
    analyze_silence_ratio,
    detect_vinyl_noise,
    detect_clicks_and_pops
)

logger = logging.getLogger(__name__)


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
