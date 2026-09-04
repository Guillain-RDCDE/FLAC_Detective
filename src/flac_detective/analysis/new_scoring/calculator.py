"""Main scoring calculator for FLAC analysis."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from .audio_loader import load_audio_with_retry
from .bitrate import (
    calculate_apparent_bitrate,
    calculate_bitrate_variance,
    calculate_real_bitrate,
)
from .constants import CASSETTE_THRESHOLD, CONVICTION_MIN_FAMILIES
from .evidence import collapse_dependent_families, evidence_families
from .metadata import parse_metadata
from .models import AudioMetadata, BitrateMetrics, ScoringContext
from .rules.mdct_alignment import should_run_rule_13
from .strategies import (
    Rule1MP3Bitrate,
    Rule2Cutoff,
    Rule5HighVariance,
    Rule6HighQualityProtection,
    Rule7SilenceAnalysis,
    Rule8NyquistException,
    Rule10Consistency,
    Rule11CassetteDetection,
    Rule12MLClassifier,
    Rule13MDCTAlignment,
    Rule14TemporalSeam,
    Rule15StereoSeam,
    Rule424BitSuspect,
    ScoringRule,
)
from .verdict import determine_verdict, uncorroborated_conviction_blocked

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


def _calculate_bitrate_metrics(
    filepath: Path,
    audio_meta: AudioMetadata,
    source_path: Optional[Path] = None,
    compressed_size_bytes: Optional[int] = None,
) -> BitrateMetrics:
    """Calculate all bitrate-related metrics.

    Args:
        filepath: Path to the readable audio used for analysis (the temp copy /
            decoded WAV).
        audio_meta: Parsed audio metadata
        source_path: Original on-disk file to size for the *real* bitrate. For a
            lossless-COMPRESSED source decoded to a temp WAV (ALAC/APE), this MUST
            be the original compressed file — sizing the decoded WAV would yield a
            ~uncompressed bitrate (ratio ≈ 1), wrongly tripping the "uncompressed"
            gate and disabling Rules 1 & 3. Defaults to ``filepath`` (FLAC: the
            temp is a same-size copy, so it makes no difference).
        compressed_size_bytes: Size the audio occupies once losslessly compressed,
            measured by ``audio_formats.flac_equivalent_size``. Supplied for every
            non-FLAC source, and it takes precedence over sizing any file on disk.
            Without it a WAV and an AIFF report ~1411 kbps whatever their samples
            hold, and the compression ratio Rule 1 reads stops being a fact about
            the audio and becomes a fact about the packaging (issue #7).

    Returns:
        BitrateMetrics containing all calculated bitrate values
    """
    if compressed_size_bytes is not None and audio_meta.duration > 0:
        real_bitrate = (compressed_size_bytes * 8) / (audio_meta.duration * 1000)
        logger.debug(
            f"Real bitrate from FLAC-equivalent size: {real_bitrate:.1f} kbps "
            f"({compressed_size_bytes} bytes)"
        )
    else:
        real_bitrate = calculate_real_bitrate(source_path or filepath, audio_meta.duration)
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


def _ensure_audio(context: ScoringContext) -> None:
    """Load the full audio into ``context`` once, if a rule needs it.

    Rules 11 and 13 both want the decoded signal. Loading it is the single most
    expensive step in the pipeline, so it happens at most once per file and is
    shared — via the AudioCache when the analyzer provides one.
    """
    if context.audio_data is not None:
        return
    audio_data: Optional["np.ndarray"]
    sample_rate: Optional[int]
    if context.cache is not None:
        logger.debug("OPTIMIZATION: Using shared AudioCache")
        audio_data, sample_rate = context.cache.get_full_audio()
    else:
        logger.debug("OPTIMIZATION: No shared cache, loading from file")
        audio_data, sample_rate = load_audio_with_retry(str(context.filepath))
    context.audio_data = audio_data
    context.loaded_sample_rate = sample_rate


def _run_rule_13(context: ScoringContext) -> None:
    """Run Rule 13 and, if it found evidence, withdraw Rule 8's protection.

    These two rules disagree by construction, and Rule 13 is right.

    Rule 8 grants −50 to a file whose spectrum runs up to Nyquist, on the
    reasoning that a transcode would have left a cliff. That reasoning is exactly
    what stops being true at 256–320 kbps: a modern encoder at those rates keeps
    the whole band, so "no cliff" stops being evidence of anything. Rule 8 is an
    *absence of evidence* argument; Rule 13 produces direct positive evidence —
    the encoder's own quantisation grid, at one sample-exact frame alignment,
    ~10x above the file's own baseline. Direct evidence has to win.

    The conflict was invisible until v1.8 because the score accumulator clamped
    at zero on every addition, which silently erased Rule 8's −50 before anything
    could be offset against it. Fixing that clamp made Rule 8 real, and Rule 8
    immediately swallowed Rule 13: 320 kbps AAC detection fell from 97.5 % to
    26.2 % in the audit. Hence this explicit precedence rule rather than a
    points arms race between the two.
    """
    before = context.rule_scores.get("Rule13MDCTAlignment", 0)
    Rule13MDCTAlignment().apply(context)
    gained = context.rule_scores.get("Rule13MDCTAlignment", 0) - before
    if gained <= 0:
        return

    protection = context.rule_scores.get("Rule8NyquistException", 0)
    if protection < 0:
        context.add_score(
            -protection,
            [
                "R8 protection withdrawn: R13 found a positive MDCT quantisation "
                "signature, so a full-range spectrum is no longer evidence of authenticity"
            ],
        )
        logger.info(
            "RULE 8: protection withdrawn (%+d) — Rule 13 found direct evidence", -protection
        )


def _is_corroborated(context: ScoringContext) -> bool:
    """True if enough independent evidence families already accuse this file.

    Used to decide whether an early exit is safe. A high score from one family is
    exactly the case that still needs the remaining rules to run.

    The dependency guard is applied HERE too, not only at the verdict: a file that
    exits early believing it has two witnesses would never reach the collapse, and
    the guard would silently stop working on exactly the files that exit fastest.
    """
    families = collapse_dependent_families(
        evidence_families(context.rule_scores, witnesses=context.witness_families),
        context.cutoff_freq,
    )
    return len(families) >= CONVICTION_MIN_FAMILIES


def _apply_scoring_rules(  # noqa: C901
    context: ScoringContext, deep: bool = False
) -> Tuple[int, List[str]]:
    """Apply all scoring rules using the Strategy pattern.

    Args:
        context: The scoring context containing all necessary data.
        deep: If True, run Rule 12 even when the authentic fast path would otherwise
            short-circuit — so the high-confidence WARNING floor can catch silent
            AAC/Vorbis transcodes. See the ``--deep`` flag.

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

    # MEMORY OPTIMIZATION: Manage audio buffer scope
    try:
        if run_rule11_early:
            logger.info("Executing Rule 11 (Cassette) EARLY as priority...")

            # Pre-load audio for R11 (and Rule 13 later)
            logger.debug("OPTIMIZATION: Pre-loading full audio for Rule 11...")
            _ensure_audio(context)
            rule11.apply(context)

        # ========== PHASE 1: FAST RULES (R1-R6) ==========
        # These are cheap (<0.01s total), always execute
        logger.debug("OPTIMIZATION: Executing fast rules (R1-R6)...")

        # Filter rules based on cassette detection
        fast_rules: List[ScoringRule] = []

        # Uncompressed input (e.g. WAV): real ≈ apparent bitrate, so there is no
        # lossless-compression signal for the container-bitrate rules to read.
        # Rules 1 (MP3-bitrate signature) and 3 (source-vs-container) become
        # meaningless and would misfire; the spectral rules still see the MP3
        # cliff, so we gate 1 & 3 off (same idea as the cassette gate below).
        bm = context.bitrate_metrics
        is_uncompressed = bm.apparent_bitrate > 0 and (bm.real_bitrate / bm.apparent_bitrate) > 0.92

        # Threshold lowered 30 -> 15 in v1.8, purely to preserve behaviour: test 11C
        # was a constant +15 (it keyed off Rule 9C, which measured at chance) and has
        # been removed, so every remaining test keeps the weight it always had.
        if context.cassette_score >= CASSETTE_THRESHOLD:
            logger.info("R11: MP3 signature cancelled (cassette source detected)")
            logger.info(
                f"CASSETTE DETECTED (evidence {context.cassette_score} >= {CASSETTE_THRESHOLD}). "
                f"Disabling Rule 1 (MP3 Bitrate)."
            )
            context.add_score(-40, ["R11: Authentic cassette audio source (bonus -40pts)"])

            # Skip Rule 1
            fast_rules = [
                Rule2Cutoff(),
                Rule424BitSuspect(),
                Rule5HighVariance(),
                Rule6HighQualityProtection(),
            ]
        elif is_uncompressed:
            # GATE D, repaired in v1.12. Rule 1 used to be removed here entirely
            # ("no lossless-compression signal") — which put every WAV
            # structurally beyond the rule's reach and was one of the four
            # mechanisms behind the engine reading 8.8 % on the owner-attested
            # wild 53 (all WAV). Gate C inside the rule now treats a PCM-level
            # container bitrate as uninformative rather than as a failure, and
            # the rule's other guards (variance, residual floor, Nyquist) are
            # container-agnostic, so the rule runs. Found by G4's first
            # end-to-end firing: the offline G-series called the rule function
            # and could not see the dispatch. (Rule 3 no longer exists.)
            logger.info(
                "UNCOMPRESSED input (e.g. WAV): Rule 1 runs with the container "
                "bitrate treated as uninformative (v1.12 gates C+D)."
            )
            fast_rules = [
                Rule1MP3Bitrate(),
                Rule2Cutoff(),
                Rule424BitSuspect(),
                Rule5HighVariance(),
                Rule6HighQualityProtection(),
            ]
        else:
            # Standard execution
            fast_rules = [
                Rule1MP3Bitrate(),
                Rule2Cutoff(),
                Rule424BitSuspect(),
                Rule5HighVariance(),
                Rule6HighQualityProtection(),
            ]

        for rule in fast_rules:
            rule.apply(context)

        logger.info(f"OPTIMIZATION: Fast rules + R8 (+R11?) score = {context.current_score}")

        # SHORT-CIRCUIT 1: already convicted — but only if the conviction is
        # CORROBORATED. Stopping here on a single-family score would be
        # self-defeating: the rules that could corroborate it (12 and 13) live
        # further down, so an early exit guarantees the file can never reach two
        # families, and the corroboration gate would end up measuring this
        # short-circuit rather than the evidence.
        if context.current_score >= 86 and _is_corroborated(context):
            logger.info(
                f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ 86 (corroborated)"
            )
            context.reasons.append(
                "⚡ Fast analysis: FAKE_CERTAIN detected without expensive rules"
            )
            return context.current_score, context.reasons

        # SHORT-CIRCUIT 2: If very low score and no MP3 detected, likely authentic
        #
        # GATE E, added for issue #7. This branch does not merely skip some rules,
        # it ACQUITS: everything after it — 7, 10, 12, 13, 14, 15 — never runs, and
        # the file leaves as AUTHENTIC. It reads `mp3_bitrate_detected is None` as
        # "Rule 1 looked and found nothing". On uncompressed input that is not what
        # it means: Rule 1's container window has nothing to read there, so None is
        # an absence of measurement, not a negative result. The engine has no
        # standing to acquit on it — the same principle assessability.py already
        # applies at the verdict, applied here, where the rules are chosen.
        #
        # With the container-independent sizing upstream this is now rare (it takes
        # audio that is genuinely incompressible), and it costs those files the full
        # rule set instead of an unearned pass. That is the right way round.
        if (
            context.current_score < 10
            and context.mp3_bitrate_detected is None
            and not is_uncompressed
        ):
            if not deep:
                logger.info(
                    f"OPTIMIZATION: Fast path for authentic file "
                    f"(score={context.current_score}, no MP3)"
                )
                context.reasons.append(
                    "⚡ Fast analysis: AUTHENTIC detected without expensive rules"
                )
                return context.current_score, context.reasons
            # Deep mode: the heuristics are silent, but a silent file is exactly where a
            # high-bitrate AAC/Vorbis transcode hides. Skip the expensive heuristic rules
            # (they can't help here) and run the two that can: the CNN's high-confidence
            # WARNING floor, and Rule 13 — which reads MDCT frame alignment and is the
            # ONLY rule with signal left once the encoder keeps the whole band. This
            # branch is precisely the 256-320 kbps AAC blind spot.
            logger.info(
                f"DEEP: heuristics silent (score={context.current_score}), running Rules 12/13 "
                f"anyway (fast path bypassed)"
            )
            if should_run_rule_13(context.cutoff_freq, context.current_score):
                _ensure_audio(context)
                _run_rule_13(context)
            # Rule 14 must run on THIS path too. It is the branch for files whose
            # heuristics found nothing — high-bitrate AAC, Vorbis, and every Opus
            # transcode in the corpus — which is precisely the population the
            # temporal witness exists for. Wiring it only into the main path left
            # it unreachable for its own target, exactly the failure this
            # repository has a test for (test_verdict_reachability): a witness
            # that arrives after the branch it was meant to inform.
            if context.cutoff_freq >= 15000.0:
                _ensure_audio(context)
                Rule14TemporalSeam().apply(context)
            if context.cutoff_freq >= 12000.0:
                _ensure_audio(context)
                Rule15StereoSeam().apply(context)
            Rule12MLClassifier().apply(context)
            return context.current_score, context.reasons

        # ========== PHASE 2: CONDITIONAL EXPENSIVE RULES ==========
        # Determine which expensive rules to run
        run_rule7 = 19000 <= context.cutoff_freq <= 21500
        # Logic fix: if R11 already ran early (cutoff < 19000), we don't run it here.
        # Check if R11 needed and NOT ran yet
        run_rule11 = (context.cutoff_freq < 19000) and (not run_rule11_early)

        expensive_rules: List[ScoringRule] = []
        if run_rule7:
            expensive_rules.append(Rule7SilenceAnalysis())
        if run_rule11:
            expensive_rules.append(Rule11CassetteDetection())

        if expensive_rules:
            # Check if we need to load audio (if NOT already loaded by R11 early)
            need_full_audio = any(isinstance(r, Rule11CassetteDetection) for r in expensive_rules)

            if need_full_audio:
                _ensure_audio(context)

            # Sequential execution: ScoringContext.add_score mutates shared state,
            # so concurrent rules would race without locking. Cost is acceptable.
            for rule in expensive_rules:
                rule.apply(context)
        else:
            logger.info("OPTIMIZATION: Skipping expensive rules (R7/R11)")

        # Rule 8: refine with MP3 detection context if it became available after Phase 2.
        # We rollback the initial R8 contribution by exact-match reason filtering — fragile but
        # acceptable as long as R8's reasons stay deterministic for a given context.
        if context.mp3_bitrate_detected is not None:
            context.current_score -= initial_r8_score
            context.rule_scores["Rule8NyquistException"] = (
                context.rule_scores.get("Rule8NyquistException", 0) - initial_r8_score
            )
            for reason in initial_r8_reasons:
                if reason in context.reasons:
                    context.reasons.remove(reason)
            rule8.apply(context)
            logger.info("RULE 8 (refined): Score updated")

        # Rule 13: MDCT frame alignment. Gated on cutoff (below ~18 kHz the cheap
        # spectral rules already have signal) and on the file not being convicted
        # already. It is the only rule that survives a high-bitrate encode, and it
        # runs AFTER the Rule 8 refinement so that the refinement cannot re-apply a
        # protection Rule 13 has just withdrawn. See _run_rule_13.
        if should_run_rule_13(context.cutoff_freq, context.current_score):
            _ensure_audio(context)
            _run_rule_13(context)

        # Rule 14: the temporal seam. Runs beside Rule 13 because the audio is
        # already in hand, and BEFORE short-circuit 3 so its witness is available
        # to the same gate — a witness that arrives after the gate it should have
        # informed is what Provir calls dressing.
        if context.cutoff_freq >= 15000.0:
            _ensure_audio(context)
            Rule14TemporalSeam().apply(context)

        # Rule 15: the stereo image. Same placement reasoning as Rule 14 — before
        # the gate it should inform, and on BOTH paths, since the early-return
        # branch carries the silent-heuristic files this family reads best.
        if context.cutoff_freq >= 12000.0:
            _ensure_audio(context)
            Rule15StereoSeam().apply(context)

        # SHORT-CIRCUIT 3: same rule as above — an uncorroborated score must not
        # skip Rule 12, which is one of the few rules that can corroborate it.
        if context.current_score >= 86 and _is_corroborated(context):
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
    cutoff_std: float = float("nan"),
    energy_ratio: float = 0.0,
    cache=None,
    source_path: Optional[Path] = None,
    compressed_size_bytes: Optional[int] = None,
    deep: bool = False,
    residual_floor_db: float = float("nan"),
    breakdown_out: Optional[Dict[str, int]] = None,
    witnesses_out: Optional[Set[str]] = None,
) -> Tuple[int, str, str, str]:
    """Calculate score using the new 8-rule system with file caching.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        metadata: File metadata
        duration_check: Duration check results
        filepath: Path to the readable audio analysed (temp copy / decoded WAV)
        cutoff_std: Cutoff wander across the sampled windows; NaN when it was
            not computable (a single window) — never 0.0 for absence
        energy_ratio: High frequency energy ratio (default 0.0)
        cache: Optional AudioCache instance (contains pre-loaded full audio)
        source_path: Original on-disk file, used for the *real* bitrate when the
            analysed audio is a decoded WAV (ALAC/APE). See _calculate_bitrate_metrics.
        compressed_size_bytes: Size of the audio once losslessly compressed, for
            non-FLAC sources. Takes precedence over sizing a file on disk, so the
            compression ratio Rule 1 reads describes the samples rather than the
            container they arrived in. See _calculate_bitrate_metrics.
        deep: Run Rule 12 on every file, bypassing the authentic fast path (slower;
            catches silent-heuristic AAC/Vorbis transcodes). See the ``--deep`` flag.
        residual_floor_db: Spectral floor above the ~20.5 kHz wall (NaN = unknown).
            Drives Rule 1's near-Nyquist 320 kbps wall-hardness gate.
        witnesses_out: Optional set, updated in place with the families that
            testify WITHOUT scoring (Rule 14). A points breakdown cannot carry
            them — that is the whole reason they exist — so callers that need to
            reconstruct the evidence set must be handed them separately, or they
            will silently recompute a smaller one.
        breakdown_out: Optional dict, updated in place with the per-rule score
            attribution for this file (``{"Rule2Cutoff": 25, …}``). Used by
            ml/rule_audit.py to measure each rule's discriminative power in
            isolation. Rules that contributed nothing are omitted.
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
        bitrate_metrics = _calculate_bitrate_metrics(
            filepath,
            audio_meta,
            source_path=source_path,
            compressed_size_bytes=compressed_size_bytes,
        )

        # Initialize Context
        context = ScoringContext(
            filepath=filepath,
            audio_meta=audio_meta,
            bitrate_metrics=bitrate_metrics,
            cutoff_freq=cutoff_freq,
            cutoff_std=cutoff_std,
            energy_ratio=energy_ratio,
            residual_floor_db=residual_floor_db,
            cache=cache,  # Pass shared cache to context
        )

        # Apply scoring rules
        raw_score, reasons = _apply_scoring_rules(context, deep=deep)

        if breakdown_out is not None:
            breakdown_out.update(context.rule_scores)
        if witnesses_out is not None:
            witnesses_out.update(context.witness_families)

        # Clamp ONCE, here, on the final total. Clamping inside add_score (the
        # pre-v1.8 behaviour) destroyed every protection that ran before a
        # penalty — including Rule 8's −50, which by design runs first. See
        # ScoringContext.add_score.
        score = max(0, raw_score)

        # Conviction needs independent sources, not just a big number — and
        # independence is a property of THIS file, not of the rule grouping.
        families = collapse_dependent_families(
            evidence_families(context.rule_scores, witnesses=context.witness_families),
            context.cutoff_freq,
        )
        verdict, confidence = determine_verdict(score, families)

        if uncorroborated_conviction_blocked(score, families):
            only = ", ".join(sorted(families)) or "none"
            reasons.append(
                f"⚖ Held below FAKE_CERTAIN: score {score} comes from a single "
                f"evidence family ({only}); a conviction requires two independent ones"
            )
            logger.info(
                "CONVICTION WITHHELD: score %d but only %d evidence family (%s)",
                score,
                len(families),
                only,
            )

        # Format reasons for output
        reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"

        logger.info(
            f"Final score: {score}/150 - Verdict: {verdict} - "
            f"Evidence families: {sorted(families) or 'none'}"
        )
        logger.info(f"Reasons: {reasons_str}")
        logger.info(f"{'='*60}\n")

        return score, verdict, confidence, reasons_str

    finally:
        # PHASE 3 OPTIMIZATION: Cache is managed locally by AudioCache
        pass
