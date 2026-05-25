"""Main scoring calculator for FLAC analysis."""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

from .audio_loader import load_audio_with_retry
from .bitrate import (
    calculate_apparent_bitrate,
    calculate_bitrate_variance,
    calculate_real_bitrate,
)
from .metadata import parse_metadata
from .models import AudioMetadata, BitrateMetrics, ScoringContext
from .strategies import (
    Rule1MP3Bitrate,
    Rule2Cutoff,
    Rule3SourceVsContainer,
    Rule5HighVariance,
    Rule6HighQualityProtection,
    Rule7SilenceAnalysis,
    Rule8NyquistException,
    Rule9CompressionArtifacts,
    Rule10Consistency,
    Rule11CassetteDetection,
    Rule12MLClassifier,
    Rule424BitSuspect,
    ScoringRule,
)
from .verdict import determine_verdict

logger = logging.getLogger(__name__)


def _calculate_bitrate_metrics(filepath: Path, audio_meta: AudioMetadata) -> BitrateMetrics:
    """Calculate all bitrate-related metrics.

    Args:
        filepath: Path to FLAC file
        audio_meta: Parsed audio metadata

    Returns:
        BitrateMetrics containing all calculated bitrate values
    """
    real_bitrate = calculate_real_bitrate(filepath, audio_meta.duration)
    apparent_bitrate = calculate_apparent_bitrate(
        audio_meta.sample_rate, audio_meta.bit_depth, audio_meta.channels
    )
    variance = calculate_bitrate_variance(filepath, audio_meta.sample_rate)

    logger.info(
        f"Bitrate analysis: real={real_bitrate:.1f} kbps, "
        f"apparent={apparent_bitrate} kbps, "
        f"variance={variance:.1f} kbps"
    )

    return BitrateMetrics(
        real_bitrate=real_bitrate, apparent_bitrate=apparent_bitrate, variance=variance
    )


def _apply_scoring_rules(context: ScoringContext) -> Tuple[int, List[str]]:
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

    # ========== PRIORITY RULE 11: CASSETTE DETECTION ==========
    # R11 must run before R1 to disable MP3-bitrate scoring on authentic cassette rips.
    # Trade-off: R11 is expensive (bandpass filtering) but only triggered when cutoff < 19 kHz.
    rule11 = Rule11CassetteDetection()
    run_rule11_early = context.cutoff_freq < 19000
    cassette_score = 0

    # MEMORY OPTIMIZATION: Manage audio buffer scope
    try:
        if run_rule11_early:
            logger.info("Executing Rule 11 (Cassette) EARLY as priority...")

            # Pre-load audio for R11 (and likely R9 later)
            logger.debug("OPTIMIZATION: Pre-loading full audio for Rule 11...")

            if context.cache is not None:
                # Use shared cache from FLACAnalyzer
                logger.debug("OPTIMIZATION: Using shared AudioCache for Rule 11")
                audio_data, sample_rate = context.cache.get_full_audio()
            else:
                logger.debug("OPTIMIZATION: No shared cache, loading from file")
                audio_data, sample_rate = load_audio_with_retry(str(context.filepath))

            context.audio_data = audio_data
            context.loaded_sample_rate = sample_rate

            rule11.apply(context)

            # Extract the score contribution from R11
            cassette_score = context.current_score - initial_r8_score

        # ========== PHASE 1: FAST RULES (R1-R6) ==========
        # These are cheap (<0.01s total), always execute
        logger.debug("OPTIMIZATION: Executing fast rules (R1-R6)...")

        # Filter rules based on cassette detection
        fast_rules: List[ScoringRule] = []

        if cassette_score >= 30:
            logger.info(f"R11: Signature MP3 annulée (source cassette détectée)")
            logger.info(
                f"CASSETTE DETECTED (Score {cassette_score} >= 30). Disabling Rule 1 (MP3 Bitrate)."
            )
            # Add bonus manually as requested: "score -= 40"
            # The Context.add_score handles addition. To subtract, add negative.
            context.add_score(-40, ["R11: Source cassette audio authentique (Bonus -40pts)"])

            # Skip Rule 1
            fast_rules = [
                Rule2Cutoff(),
                Rule3SourceVsContainer(),
                Rule424BitSuspect(),
                Rule5HighVariance(),
                Rule6HighQualityProtection(),
            ]
        else:
            # Standard execution
            fast_rules = [
                Rule1MP3Bitrate(),
                Rule2Cutoff(),
                Rule3SourceVsContainer(),
                Rule424BitSuspect(),
                Rule5HighVariance(),
                Rule6HighQualityProtection(),
            ]

        for rule in fast_rules:
            rule.apply(context)

        logger.info(f"OPTIMIZATION: Fast rules + R8 (+R11?) score = {context.current_score}")

        # SHORT-CIRCUIT 1: If already FAKE_CERTAIN (≥86), stop here
        if context.current_score >= 86:
            logger.info(
                f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ 86 (FAKE_CERTAIN)"
            )
            context.reasons.append("⚡ Analyse rapide : FAKE_CERTAIN détecté sans règles coûteuses")
            return context.current_score, context.reasons

        # SHORT-CIRCUIT 2: If very low score and no MP3 detected, likely authentic
        if context.current_score < 10 and context.mp3_bitrate_detected is None:
            logger.info(
                f"OPTIMIZATION: Fast path for authentic file (score={context.current_score}, no MP3)"
            )
            context.reasons.append("⚡ Analyse rapide : AUTHENTIC détecté sans règles coûteuses")
            return context.current_score, context.reasons

        # ========== PHASE 2: CONDITIONAL EXPENSIVE RULES ==========
        # Determine which expensive rules to run
        run_rule7 = 19000 <= context.cutoff_freq <= 21500
        run_rule9 = context.cutoff_freq < 21000 or context.mp3_bitrate_detected is not None
        # Logic fix: if R11 already ran early (cutoff < 19000), we don't run it here.
        # Check if R11 needed and NOT ran yet
        run_rule11 = (context.cutoff_freq < 19000) and (not run_rule11_early)

        expensive_rules: List[ScoringRule] = []
        if run_rule7:
            expensive_rules.append(Rule7SilenceAnalysis())
        if run_rule9:
            expensive_rules.append(Rule9CompressionArtifacts())
        if run_rule11 and cassette_score == 0:
            expensive_rules.append(Rule11CassetteDetection())

        if expensive_rules:
            # Check if we need to load audio (if NOT already loaded by R11 early)
            need_full_audio = any(
                isinstance(r, (Rule9CompressionArtifacts, Rule11CassetteDetection))
                for r in expensive_rules
            )

            if need_full_audio and context.audio_data is None:
                logger.debug("OPTIMIZATION: Pre-loading full audio for Rules 9/11 (Phase 2)...")
                if context.cache is not None:
                    logger.debug("OPTIMIZATION: Using shared AudioCache for Phase 2")
                    audio_data, sample_rate = context.cache.get_full_audio()
                else:
                    audio_data, sample_rate = load_audio_with_retry(str(context.filepath))

                context.audio_data = audio_data
                context.loaded_sample_rate = sample_rate

            # Sequential execution: ScoringContext.add_score mutates shared state,
            # so concurrent rules would race without locking. Cost is acceptable.
            for rule in expensive_rules:
                rule.apply(context)
        else:
            logger.info("OPTIMIZATION: Skipping expensive rules (R7/R9/R11)")

        # Rule 8: refine with MP3 detection context if it became available after Phase 2.
        # We rollback the initial R8 contribution by exact-match reason filtering — fragile but
        # acceptable as long as R8's reasons stay deterministic for a given context.
        if context.mp3_bitrate_detected is not None:
            context.current_score -= initial_r8_score
            for reason in initial_r8_reasons:
                if reason in context.reasons:
                    context.reasons.remove(reason)
            rule8.apply(context)
            logger.info("RULE 8 (refined): Score updated")

        # SHORT-CIRCUIT 3: Check again after R7+R8+R9+R11
        if context.current_score >= 86:
            logger.info(
                f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ 86 after expensive rules"
            )
            return context.current_score, context.reasons

        # Rule 10: Only if score > 30 (already suspect)
        if context.current_score > 30:
            logger.info(f"OPTIMIZATION: Activating Rule 10 (score {context.current_score} > 30)")
            Rule10Consistency().apply(context)
        else:
            logger.info(f"OPTIMIZATION: Skipping Rule 10 (score {context.current_score} ≤ 30)")

        # Rule 12: ML-based transcode detection. No-op if torch / model unavailable.
        # Runs after Rule 10 so the heuristic score is established first; the CNN
        # adds an independent signal that boosts confidence on borderline cases
        # (cutoff 19-21 kHz, high-bitrate MP3, AAC source).
        Rule12MLClassifier().apply(context)

        return context.current_score, context.reasons

    finally:
        # CLEANUP MEMORY
        if context.audio_data is not None:
            logger.debug("OPTIMIZATION: Releasing audio buffer memory")
            context.audio_data = None
            context.loaded_sample_rate = None
            # Force GC to avoid bad_alloc in loop
            import gc

            gc.collect()


def new_calculate_score(
    cutoff_freq: float,
    metadata: Dict,
    duration_check: Dict,
    filepath: Path,
    cutoff_std: float = 0.0,
    energy_ratio: float = 0.0,
    cache=None,
) -> Tuple[int, str, str, str]:
    """Calculate score using the new 8-rule system with file caching.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        metadata: File metadata
        duration_check: Duration check results
        filepath: Path to FLAC file
        cutoff_std: Standard deviation of cutoff frequency (default 0.0)
        energy_ratio: High frequency energy ratio (default 0.0)
        cache: Optional AudioCache instance (contains pre-loaded full audio)
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
                    duration=info.duration,
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
            cutoff_std=cutoff_std,
            energy_ratio=energy_ratio,
            cache=cache,  # Pass shared cache to context
        )

        # Apply scoring rules
        score, reasons = _apply_scoring_rules(context)

        # Determine verdict and confidence
        verdict, confidence = determine_verdict(score)

        # Format reasons for output
        reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"

        logger.info(f"Final score: {score}/150 - Verdict: {verdict} - Confidence: {confidence}")
        logger.info(f"Reasons: {reasons_str}")
        logger.info(f"{'='*60}\n")

        return score, verdict, confidence, reasons_str

    finally:
        # PHASE 3 OPTIMIZATION: Cache is managed locally by AudioCache
        pass
