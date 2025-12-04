"""Main scoring calculator for FLAC analysis."""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from .models import AudioMetadata, BitrateMetrics
from .metadata import parse_metadata
from .bitrate import (
    calculate_real_bitrate,
    calculate_apparent_bitrate,
    calculate_bitrate_variance,
)
from .rules import (
    apply_rule_1_mp3_bitrate,
    apply_rule_2_cutoff,
    apply_rule_3_source_vs_container,
    apply_rule_4_24bit_suspect,
    apply_rule_5_high_variance,
    apply_rule_6_variable_bitrate_protection,
    apply_rule_7_silence_analysis,
    apply_rule_8_nyquist_exception,
    apply_rule_9_compression_artifacts,
    apply_rule_10_multi_segment_consistency,
)
from .verdict import determine_verdict
from ..audio_cache import AudioCache
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def _calculate_bitrate_metrics(
    filepath: Path,
    audio_meta: AudioMetadata
) -> BitrateMetrics:
    """Calculate all bitrate-related metrics.

    Args:
        filepath: Path to FLAC file
        audio_meta: Parsed audio metadata

    Returns:
        BitrateMetrics containing all calculated bitrate values
    """
    real_bitrate = calculate_real_bitrate(filepath, audio_meta.duration)
    apparent_bitrate = calculate_apparent_bitrate(
        audio_meta.sample_rate,
        audio_meta.bit_depth,
        audio_meta.channels
    )
    variance = calculate_bitrate_variance(filepath, audio_meta.sample_rate)

    logger.info(
        f"Bitrate analysis: real={real_bitrate:.1f} kbps, "
        f"apparent={apparent_bitrate} kbps, "
        f"variance={variance:.1f} kbps"
    )

    return BitrateMetrics(
        real_bitrate=real_bitrate,
        apparent_bitrate=apparent_bitrate,
        variance=variance
    )


def _apply_scoring_rules(
    cutoff_freq: float,
    audio_meta: AudioMetadata,
    bitrate_metrics: BitrateMetrics,
    filepath: Path,
    cutoff_std: float = 0.0
) -> Tuple[int, List[str]]:
    """Apply all scoring rules with optimizations (Phase 1).

    Optimizations:
    1. Short-circuit: Stop early if FAKE_CERTAIN reached
    2. Conditional activation: Skip expensive rules when not needed
    3. Shared audio cache: Avoid multiple file reads

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        audio_meta: Parsed audio metadata
        bitrate_metrics: Calculated bitrate metrics
        filepath: Path to FLAC file
        cutoff_std: Standard deviation of cutoff frequency

    Returns:
        Tuple of (total_score, list_of_reasons)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    total_score = 0
    all_reasons: List[str] = []
    
    # ========== RULE 8: NYQUIST EXCEPTION (ALWAYS FIRST) ==========
    # This rule MUST be calculated first and applied before any short-circuit
    # to protect authentic files with cutoff near Nyquist, even if R1-R6 give high scores
    logger.debug("OPTIMIZATION: Calculating Rule 8 (Nyquist Exception) FIRST...")
    rule8_score, rule8_reasons = apply_rule_8_nyquist_exception(
        cutoff_freq,
        audio_meta.sample_rate,
        None,  # mp3_bitrate_detected not yet available
        None   # silence_ratio not yet available
    )
    logger.info(f"RULE 8 (pre-calculated): {rule8_score} points")
    
    # ========== PHASE 1: FAST RULES (R1-R6) ==========
    # These are cheap (<0.01s total), always execute
    logger.debug("OPTIMIZATION: Executing fast rules (R1-R6)...")
    
    # Apply Rule 1 first to get the detected MP3 bitrate
    rule1_result, mp3_bitrate_detected = apply_rule_1_mp3_bitrate(
        cutoff_freq, 
        bitrate_metrics.real_bitrate,
        cutoff_std,
        audio_meta.sample_rate
    )
    
    # Apply Rules 2-6 (all fast)
    fast_rules = [
        rule1_result,
        apply_rule_2_cutoff(cutoff_freq, audio_meta.sample_rate),
        apply_rule_3_source_vs_container(
            mp3_bitrate_detected,
            bitrate_metrics.real_bitrate
        ),
        apply_rule_4_24bit_suspect(
            audio_meta.bit_depth, 
            mp3_bitrate_detected,
            cutoff_freq,
            None  # silence_ratio not yet available
        ),
        apply_rule_5_high_variance(
            bitrate_metrics.real_bitrate,
            bitrate_metrics.variance
        ),
        apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected,
            bitrate_metrics.real_bitrate,
            cutoff_freq,
            bitrate_metrics.variance
        ),
    ]
    
    # Aggregate fast rules
    for rule_score, rule_reasons in fast_rules:
        total_score += rule_score
        all_reasons.extend(rule_reasons)
    
    # Apply Rule 8 score BEFORE short-circuit
    total_score += rule8_score
    all_reasons.extend(rule8_reasons)
    total_score = max(0, total_score)
    
    logger.info(f"OPTIMIZATION: Fast rules + R8 score = {total_score}")
    
    # SHORT-CIRCUIT 1: If already FAKE_CERTAIN (≥86), stop here
    # Rule 8 has already been applied, so authentic files near Nyquist are protected
    if total_score >= 86:
        logger.info(f"OPTIMIZATION: Short-circuit at {total_score} ≥ 86 (FAKE_CERTAIN, R8 already applied)")
        all_reasons.append("⚡ Analyse rapide : FAKE_CERTAIN détecté sans règles coûteuses")
        return total_score, all_reasons
    
    # SHORT-CIRCUIT 2: If very low score and no MP3 detected, likely authentic
    if total_score < 10 and mp3_bitrate_detected is None:
        logger.info(f"OPTIMIZATION: Fast path for authentic file (score={total_score}, no MP3, R8 already applied)")
        all_reasons.append("⚡ Analyse rapide : AUTHENTIC détecté sans règles coûteuses")
        return total_score, all_reasons
    
    # ========== PHASE 2: CONDITIONAL EXPENSIVE RULES ==========
    # PHASE 3 OPTIMIZATION: Parallelize R7 and R9 if both are needed
    
    # Determine which expensive rules to run
    run_rule7 = 19000 <= cutoff_freq <= 21500
    run_rule9 = cutoff_freq < 21000 or mp3_bitrate_detected is not None
    
    silence_ratio = None
    rule7_score, rule7_reasons = 0, []
    rule9_score, rule9_reasons = 0, []
    
    # PARALLEL EXECUTION: If both R7 and R9 are needed, run them in parallel
    if run_rule7 and run_rule9:
        logger.info("OPTIMIZATION PHASE 3: Running R7 and R9 in PARALLEL")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            future_r7 = executor.submit(
                apply_rule_7_silence_analysis,
                str(filepath),
                cutoff_freq,
                audio_meta.sample_rate
            )
            future_r9 = executor.submit(
                apply_rule_9_compression_artifacts,
                str(filepath),
                cutoff_freq,
                mp3_bitrate_detected
            )
            
            # Wait for results
            rule7_score, rule7_reasons, silence_ratio = future_r7.result()
            rule9_score, rule9_reasons, _ = future_r9.result()
            
        logger.info(f"OPTIMIZATION PHASE 3: Parallel execution completed (R7={rule7_score}, R9={rule9_score})")
        
    # SEQUENTIAL EXECUTION: If only one is needed
    elif run_rule7:
        logger.info(f"OPTIMIZATION: Activating Rule 7 (cutoff {cutoff_freq:.0f} in ambiguous zone)")
        rule7_score, rule7_reasons, silence_ratio = apply_rule_7_silence_analysis(
            str(filepath),
            cutoff_freq,
            audio_meta.sample_rate
        )
    elif run_rule9:
        logger.info(f"OPTIMIZATION: Activating Rule 9 (cutoff={cutoff_freq:.0f} or MP3={mp3_bitrate_detected})")
        rule9_score, rule9_reasons, _ = apply_rule_9_compression_artifacts(
            str(filepath),
            cutoff_freq,
            mp3_bitrate_detected
        )
    else:
        logger.info(f"OPTIMIZATION: Skipping both R7 and R9")
    
    # Apply scores
    total_score += rule7_score + rule9_score
    all_reasons.extend(rule7_reasons)
    all_reasons.extend(rule9_reasons)
    total_score = max(0, total_score)
    
    # Rule 8: Refine with additional context if available
    # We already calculated R8 at the beginning, but now we have mp3_bitrate_detected and silence_ratio
    # Only recalculate if these might change the result (i.e., if MP3 was detected)
    if mp3_bitrate_detected is not None:
        logger.debug("OPTIMIZATION: Refining Rule 8 with mp3_bitrate_detected and silence_ratio...")
        # Remove the previous R8 score
        total_score -= rule8_score
        for reason in rule8_reasons:
            if reason in all_reasons:
                all_reasons.remove(reason)
        
        # Recalculate with full context
        rule8_score, rule8_reasons = apply_rule_8_nyquist_exception(
            cutoff_freq,
            audio_meta.sample_rate,
            mp3_bitrate_detected,
            silence_ratio
        )
        total_score += rule8_score
        all_reasons.extend(rule8_reasons)
        total_score = max(0, total_score)
        logger.info(f"RULE 8 (refined): {rule8_score} points")
    
    # SHORT-CIRCUIT 3: Check again after R7+R8+R9
    if total_score >= 86:
        logger.info(f"OPTIMIZATION: Short-circuit at {total_score} ≥ 86 after R7+R8+R9")
        return total_score, all_reasons
    
    # Rule 10: Only if score > 30 (already suspect)
    # This is already conditional in the rule itself, but we can skip the call
    if total_score > 30:
        logger.info(f"OPTIMIZATION: Activating Rule 10 (score {total_score} > 30)")
        rule10_score, rule10_reasons = apply_rule_10_multi_segment_consistency(
            str(filepath),
            total_score,
            audio_meta.sample_rate,
            bitrate_metrics.real_bitrate
        )
        
        if rule10_score != 0 or rule10_reasons:
            total_score += rule10_score
            all_reasons.extend(rule10_reasons)
            total_score = max(0, total_score)
    else:
        logger.info(f"OPTIMIZATION: Skipping Rule 10 (score {total_score} ≤ 30)")

    return total_score, all_reasons


def new_calculate_score(
    cutoff_freq: float,
    metadata: Dict,
    duration_check: Dict,
    filepath: Path,
    cutoff_std: float = 0.0
) -> Tuple[int, str, str, str]:
    """Calculate score using the new 8-rule system with file caching.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        metadata: File metadata
        duration_check: Duration check results
        filepath: Path to FLAC file
        cutoff_std: Standard deviation of cutoff frequency (default 0.0)
    """
    # PHASE 3 OPTIMIZATION: Enable file read cache for this analysis
    from ..file_cache import enable_cache, clear_cache, get_cache_stats
    
    enable_cache()
    logger.debug("OPTIMIZATION: File read cache ENABLED")
    
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting score calculation for: {filepath.name}")
        logger.info(f"Metadata received: {metadata}")
        logger.info(f"Cutoff frequency: {cutoff_freq:.1f} Hz")
        logger.info(f"{'='*60}")
        
        # Parse and validate metadata
        audio_meta = parse_metadata(metadata)
        
        # Validate duration
        if audio_meta.duration <= 0:
            logger.warning(f"Duration is {audio_meta.duration}, attempting to read from file...")
            try:
                import soundfile as sf
                info = sf.info(filepath)
                audio_meta = AudioMetadata(
                    sample_rate=audio_meta.sample_rate,
                    bit_depth=audio_meta.bit_depth,
                    channels=audio_meta.channels,
                    duration=info.duration
                )
                logger.info(f"Duration corrected to {info.duration:.1f}s from soundfile")
            except Exception as e:
                logger.error(f"Could not read duration from file: {e}")

        # Calculate all bitrate metrics
        bitrate_metrics = _calculate_bitrate_metrics(filepath, audio_meta)

        # Apply scoring rules
        score, reasons = _apply_scoring_rules(cutoff_freq, audio_meta, bitrate_metrics, filepath, cutoff_std)

        # Determine verdict and confidence
        verdict, confidence = determine_verdict(score)

        # Format reasons for output
        reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"

        logger.info(
            f"Final score: {score}/150 - Verdict: {verdict} - Confidence: {confidence}"
        )
        logger.info(f"Reasons: {reasons_str}")
        logger.info(f"{'='*60}\n")

        return score, verdict, confidence, reasons_str
    
    finally:
        # PHASE 3 OPTIMIZATION: Clear cache and log stats
        stats = get_cache_stats()
        logger.info(f"OPTIMIZATION: Cache stats - {stats}")
        clear_cache()
        logger.debug("OPTIMIZATION: File read cache CLEARED")

