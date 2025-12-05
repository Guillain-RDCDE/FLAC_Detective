"""Main scoring calculator for FLAC analysis."""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from .models import AudioMetadata, BitrateMetrics, ScoringContext
from .metadata import parse_metadata
from .bitrate import (
    calculate_real_bitrate,
    calculate_apparent_bitrate,
    calculate_bitrate_variance,
)
from .strategies import (
    ScoringRule,
    Rule1MP3Bitrate,
    Rule2Cutoff,
    Rule3SourceVsContainer,
    Rule424BitSuspect,
    Rule5HighVariance,
    Rule6HighQualityProtection,
    Rule7SilenceAnalysis,
    Rule8NyquistException,
    Rule9CompressionArtifacts,
    Rule10Consistency,
)
from .verdict import determine_verdict

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
    context: ScoringContext
) -> Tuple[int, List[str]]:
    """Apply all scoring rules using the Strategy pattern.

    Args:
        context: The scoring context containing all necessary data.

    Returns:
        Tuple of (total_score, list_of_reasons)
    """

    # ========== RULE 8: NYQUIST EXCEPTION (ALWAYS FIRST) ==========
    # This rule MUST be calculated first and applied before any short-circuit
    logger.debug("OPTIMIZATION: Calculating Rule 8 (Nyquist Exception) FIRST...")
    rule8 = Rule8NyquistException()
    rule8.apply(context)

    # Store initial R8 score/reasons to allow refinement later
    initial_r8_score = context.current_score
    initial_r8_reasons = list(context.reasons)

    logger.info(f"RULE 8 (pre-calculated): {initial_r8_score} points")

    # ========== PHASE 1: FAST RULES (R1-R6) ==========
    # These are cheap (<0.01s total), always execute
    logger.debug("OPTIMIZATION: Executing fast rules (R1-R6)...")

    fast_rules: List[ScoringRule] = [
        Rule1MP3Bitrate(),
        Rule2Cutoff(),
        Rule3SourceVsContainer(),
        Rule424BitSuspect(),
        Rule5HighVariance(),
        Rule6HighQualityProtection(),
    ]

    for rule in fast_rules:
        rule.apply(context)

    logger.info(f"OPTIMIZATION: Fast rules + R8 score = {context.current_score}")

    # SHORT-CIRCUIT 1: If already FAKE_CERTAIN (≥86), stop here
    if context.current_score >= 86:
        logger.info(f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ 86 (FAKE_CERTAIN)")
        context.reasons.append("⚡ Analyse rapide : FAKE_CERTAIN détecté sans règles coûteuses")
        return context.current_score, context.reasons

    # SHORT-CIRCUIT 2: If very low score and no MP3 detected, likely authentic
    if context.current_score < 10 and context.mp3_bitrate_detected is None:
        logger.info(f"OPTIMIZATION: Fast path for authentic file (score={context.current_score}, no MP3)")
        context.reasons.append("⚡ Analyse rapide : AUTHENTIC détecté sans règles coûteuses")
        return context.current_score, context.reasons

    # ========== PHASE 2: CONDITIONAL EXPENSIVE RULES ==========
    # Determine which expensive rules to run
    run_rule7 = 19000 <= context.cutoff_freq <= 21500
    run_rule9 = context.cutoff_freq < 21000 or context.mp3_bitrate_detected is not None

    expensive_rules: List[ScoringRule] = []
    if run_rule7:
        expensive_rules.append(Rule7SilenceAnalysis())
    if run_rule9:
        expensive_rules.append(Rule9CompressionArtifacts())

    if expensive_rules:
        if len(expensive_rules) > 1:
            logger.info("OPTIMIZATION PHASE 3: Running R7 and R9 in PARALLEL")
            # Note: Since context is not thread-safe for concurrent writes,
            # we need to be careful. However, R7 updates silence_ratio and R9 updates nothing in context except score.
            # But "add_score" modifies shared state.
            # So true parallel execution with a shared mutable context is risky without locks.
            # Let's revert to sequential execution for safety with the Strategy pattern,
            # OR use temporary contexts/results.

            # For simplicity and safety with the new pattern, we'll run them sequentially.
            # The performance hit is acceptable for readability unless profiling shows otherwise.
            logger.info("Running expensive rules sequentially for safety...")
            for rule in expensive_rules:
                rule.apply(context)
        else:
            for rule in expensive_rules:
                rule.apply(context)
    else:
        logger.info("OPTIMIZATION: Skipping both R7 and R9")

    # Rule 8: Refine with additional context if available
    # Only recalculate if MP3 was detected (which changes R8 logic)
    if context.mp3_bitrate_detected is not None:
        logger.debug("OPTIMIZATION: Refining Rule 8 with mp3_bitrate_detected and silence_ratio...")

        # Backtrack: Remove the previous R8 score/reasons
        context.current_score -= initial_r8_score
        # We need to be careful removing reasons.
        # Ideally, we'd tag them, but for now we just filter them out if they match exactly.
        # This is a bit brittle. A better way is to not apply R8 first, but R8 logic says "ALWAYS FIRST".
        # Actually, R8 depends on MP3 detection.
        # The original code applied R8 first with None/None, then refined.

        # Let's just re-apply R8. The context will add the new score.
        # We need to subtract the old score first.
        # Since we know R8 was the FIRST thing applied, we can't easily isolate its contribution
        # unless we stored it (which we did in initial_r8_score).

        # Remove old reasons
        for reason in initial_r8_reasons:
            if reason in context.reasons:
                context.reasons.remove(reason)

        # Re-apply R8
        rule8.apply(context)
        logger.info("RULE 8 (refined): Score updated")

    # SHORT-CIRCUIT 3: Check again after R7+R8+R9
    if context.current_score >= 86:
        logger.info(f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ 86 after R7+R8+R9")
        return context.current_score, context.reasons

    # Rule 10: Only if score > 30 (already suspect)
    if context.current_score > 30:
        logger.info(f"OPTIMIZATION: Activating Rule 10 (score {context.current_score} > 30)")
        Rule10Consistency().apply(context)
    else:
        logger.info(f"OPTIMIZATION: Skipping Rule 10 (score {context.current_score} ≤ 30)")

    return context.current_score, context.reasons


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
    logger.debug("OPTIMIZATION: File read cache ENABLED (via AudioCache)")

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

        # Initialize Context
        context = ScoringContext(
            filepath=filepath,
            audio_meta=audio_meta,
            bitrate_metrics=bitrate_metrics,
            cutoff_freq=cutoff_freq,
            cutoff_std=cutoff_std
        )

        # Apply scoring rules
        score, reasons = _apply_scoring_rules(context)

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
        # PHASE 3 OPTIMIZATION: Cache is managed locally by AudioCache
        pass
