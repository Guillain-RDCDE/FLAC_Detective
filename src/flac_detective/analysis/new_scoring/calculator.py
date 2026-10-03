"""Main scoring calculator for FLAC analysis."""

import gc
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple

from .audio_loader import load_audio_with_retry
from .bitrate import calculate_apparent_bitrate, calculate_real_bitrate
from .constants import (
    CASSETTE_THRESHOLD,
    CONVICTION_MIN_FAMILIES,
    CONVICTION_MIN_SCORE,
    SCORE_FAKE_CERTAIN,
)
from .evidence import collapse_dependent_families, evidence_families
from .metadata import parse_metadata
from .models import AudioMetadata, BitrateMetrics, ScoringContext
from .rules.mdct_alignment import should_run_rule_13
from .rules.spectral import rule1_may_consult_container
from .rules.temporal_seam import MIN_CUTOFF_HZ as TEMPORAL_MIN_CUTOFF_HZ
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
    Rule16MP3Grid,
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
    measure_compressed_size: Optional[Callable[[], Optional[int]]] = None,
    cutoff_freq: float = 0.0,
    cutoff_std: float = float("nan"),
    edge_step_db: float = float("nan"),
    floor_above_db: float = float("nan"),
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
            measured by ``audio_formats.flac_equivalent_size``. Supplied for EVERY
            source, FLAC included, and it takes precedence over sizing any file on
            disk. Without it a WAV and an AIFF report ~1411 kbps whatever their
            samples hold, and the compression ratio Rule 1 reads stops being a fact
            about the audio and becomes a fact about the packaging (issue #7).
            Supplying it for some containers and not others is no better: two
            rulers that disagree by ~0.6 % straddle a Rule 1 cell edge on 7.5 % of
            corpus files, which was the first attempt at this fix.
        measure_compressed_size: Called to obtain that size, but only when Rule 1
            can still reach its container test at this cutoff — the re-encode costs
            about as much as the whole analysis of a file that would fast-path, and
            at those cutoffs Rule 1 answers 0/None for every container anyway. The
            decision lives HERE rather than in the caller so that it reads the same
            ``sample_rate`` and ``cutoff_std`` the rule will read; deriving them
            twice is how a gate stops mirroring the thing it gates.
        cutoff_freq, cutoff_std, edge_step_db, floor_above_db: passed to that decision.

    Returns:
        BitrateMetrics containing all calculated bitrate values
    """
    if compressed_size_bytes is None and measure_compressed_size is not None:
        if rule1_may_consult_container(
            cutoff_freq, audio_meta.sample_rate, cutoff_std, edge_step_db, floor_above_db
        ):
            compressed_size_bytes = measure_compressed_size()
        else:
            logger.debug(
                f"Compression ratio not measured: Rule 1 cannot consult the container "
                f"at cutoff {cutoff_freq:.0f} Hz ({audio_meta.sample_rate} Hz)"
            )

    # Narrowed on the Optional itself rather than through a bool: a separate
    # ``measured`` flag reads the same to a person and leaves the type checker
    # unable to see that ``compressed_size_bytes`` cannot be None inside the
    # branch. Same behaviour, one fewer thing to reason about.
    if compressed_size_bytes is not None and audio_meta.duration > 0:
        measured = True
        real_bitrate = (compressed_size_bytes * 8) / (audio_meta.duration * 1000)
        logger.debug(
            f"Real bitrate from FLAC-equivalent size: {real_bitrate:.1f} kbps "
            f"({compressed_size_bytes} bytes)"
        )
    else:
        measured = False
        real_bitrate = calculate_real_bitrate(source_path or filepath, audio_meta.duration)
    apparent_bitrate = calculate_apparent_bitrate(
        audio_meta.sample_rate, audio_meta.bit_depth, audio_meta.channels
    )
    # NOT MEASURED, ON PURPOSE, and this is the honest half of a defect found on
    # 2026-09-05. ``calculate_bitrate_variance`` used to divide the file size by ten,
    # ten times, and return the standard deviation of ten identical numbers: 0.0 for
    # every file this tool has ever analysed, produced silently, as if it had looked.
    # Rule 5 needs > 100 and Rule 6 needs > 50, so both have been inert since they
    # were written, and their unit tests passed by handing them a variance by hand.
    #
    # The measurement now exists and is correct (``flac_segment_bitrates``: each slice
    # actually compressed, ~1 s per track). Feeding it to the rules was written,
    # wired, and measured — and it is not shipped, because switching on two rules that
    # have never once executed turns out to switch on their unvalidated conditions
    # too:
    #
    #   * Rule 5's bar is 100 kbps. Across 40 corpus files the real statistic runs
    #     15.1 to 86.7. The threshold sits above the range of the thing it thresholds,
    #     so repairing the input does not revive the rule.
    #   * Rule 6 fires, and misfires. Its "substantial HF content" test is the literal
    #     constant 19000, applied at every sample rate. On a 96 kHz file with a
    #     31,226 Hz cutoff, Rule 2 scores +30 for a cutoff BELOW that rate's 44 kHz
    #     threshold while Rule 6 grants -30 for the same cutoff being "high" — the two
    #     read one number and disagree because only one of them scales. Measured on
    #     fd-exchange-2026-08-0019: FAKE_CERTAIN 95 becomes AUTHENTIC 0, the total
    #     falls under the fast path and rules 7 and 12 through 15 never run. Provir's
    #     independent return flags that file.
    #
    # Zero effect on the labelled exchange set, which is 44.1 kHz throughout, and one
    # conviction destroyed on the blind corpus. So the rules keep abstaining — None,
    # never a fabricated zero — the engine stops claiming a reading it never took, and
    # giving these two their votes back gets the measured release it needs. Turning
    # them on inside a bug fix is how an unvalidated threshold ships.
    variance = None

    logger.info(
        f"Bitrate analysis: real={real_bitrate:.1f} kbps, "
        f"apparent={apparent_bitrate} kbps, "
        f"variance={'not measured' if variance is None else format(variance, '.1f') + ' kbps'}"
    )

    return BitrateMetrics(
        real_bitrate=real_bitrate,
        apparent_bitrate=apparent_bitrate,
        variance=variance,
        ratio_measured=measured,
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


def _run_rule_16_if_decisive(context: ScoringContext) -> None:
    """Run Rule 16 only where its witness can change the verdict.

    Rule 16 scores nothing; its reading matters only to a file that already
    has the points to convict and lacks a second family. Anywhere else it could
    not move the verdict, and the Layer III filterbank pass costs seconds, so it
    is not taken. See ``rules.mp3_grid``.
    """
    if context.current_score < CONVICTION_MIN_SCORE or _is_corroborated(context):
        return
    _ensure_audio(context)
    Rule16MP3Grid().apply(context)


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


# The pipeline's own gates, named once. Values are the engine's and do not move
# here: every one of them was calibrated on labelled files (see CHANGELOG).
_SILENT_HEURISTICS_MAX_SCORE = 10
"""Below this, with Rule 1 silent, the cheap rules are said to have found nothing."""

_RULE10_MIN_SCORE = 30
"""Rule 10 is asked only once a file is already suspect (also checked inside the rule)."""

_UNCOMPRESSED_RATIO = 0.92
"""real/apparent bitrate above this means a PCM container (WAV): no lossless-compression signal."""

_CASSETTE_BONUS = -40
"""Credited to Rule 11 when its evidence reaches CASSETTE_THRESHOLD."""

_RULE11_MAX_CUTOFF_HZ = 19000
_RULE7_CUTOFF_RANGE_HZ = (19000, 21500)

# Rule 15's own gate is stereo_seam.MIN_CUTOFF_HZ (17 kHz) and the rule enforces
# it internally; this older 12 kHz figure only decides whether the audio is
# LOADED before the rule is asked. Raising it would change which files raise
# on a failed load, not any score, so it is kept as is and named for what it is.
_RULE15_LOAD_CUTOFF_HZ = 12000.0


def _is_uncompressed_input(bm: BitrateMetrics) -> bool:
    """True for a PCM container (e.g. WAV): real ≈ apparent bitrate.

    The ratio is only allowed to decide anything when it was MEASURED on the
    audio (the reference re-encode). When it was not — the analyzer skips that
    measurement at cutoffs where Rule 1 cannot reach its container test — the
    number on hand is the size of the file on disk, which is a fact about the
    wrapper: 0.60 for a FLAC and 1.00 for the WAV holding the same samples.
    Letting that through is issue #7 itself, so an unmeasured ratio reads as
    "not uncompressed" for every container alike.
    """
    return bool(
        bm.ratio_measured
        and bm.apparent_bitrate > 0
        and (bm.real_bitrate / bm.apparent_bitrate) > _UNCOMPRESSED_RATIO
    )


def _credit_cassette_bonus(context: ScoringContext, rule11: ScoringRule) -> None:
    """Apply the cassette bonus, credited to Rule 11 rather than to the calculator.

    The -40 is Rule 11's verdict acted upon, and a "why" line reading "offset by
    _calculator -40" (issue #8's screenshot, 2026-09-08) names nothing.
    """
    logger.info("R11: MP3 signature cancelled (cassette source detected)")
    logger.info(
        f"CASSETTE DETECTED (evidence {context.cassette_score} >= {CASSETTE_THRESHOLD}). "
        f"Disabling Rule 1 (MP3 Bitrate)."
    )
    previous_rule = context.active_rule
    context.active_rule = rule11.name
    try:
        context.add_score(_CASSETTE_BONUS, ["R11: Authentic cassette audio source (bonus -40pts)"])
    finally:
        context.active_rule = previous_rule


def _fast_rules(context: ScoringContext, is_uncompressed: bool) -> List[ScoringRule]:
    """The cheap rules (<0.01 s together), in the order they are asked.

    Rule 1 is left out only for a detected cassette source. On uncompressed input
    it RUNS: gate D (v1.12) used to remove it here ("no lossless-compression
    signal"), which put every WAV structurally beyond the rule's reach and was one
    of the four mechanisms behind the engine reading 8.8 % on the owner-attested
    wild 53 (all WAV). Gate C inside the rule now treats a PCM-level container
    bitrate as uninformative rather than as a failure, and the rule's other guards
    (variance, residual floor, Nyquist) are container-agnostic.
    """
    rules: List[ScoringRule] = []
    if context.cassette_score < CASSETTE_THRESHOLD:
        if is_uncompressed:
            logger.info(
                "UNCOMPRESSED input (e.g. WAV): Rule 1 runs with the container "
                "bitrate treated as uninformative (v1.12 gates C+D)."
            )
        rules.append(Rule1MP3Bitrate())
    rules += [
        Rule2Cutoff(),
        Rule424BitSuspect(),
        Rule5HighVariance(),
        Rule6HighQualityProtection(),
    ]
    return rules


def _run_rules_14_and_15(context: ScoringContext) -> None:
    """The temporal and stereo witnesses, each behind its cutoff gate.

    Both run BEFORE the gate they should inform (short-circuit 3), and on both
    paths through the pipeline — a witness that arrives after the gate it should
    have informed is what Provir calls dressing.
    """
    if context.cutoff_freq >= TEMPORAL_MIN_CUTOFF_HZ:
        _ensure_audio(context)
        Rule14TemporalSeam().apply(context)
    if context.cutoff_freq >= _RULE15_LOAD_CUTOFF_HZ:
        _ensure_audio(context)
        Rule15StereoSeam().apply(context)


def _silent_heuristics_path(context: ScoringContext, deep: bool) -> Tuple[int, List[str]]:
    """Finish a file whose cheap rules found nothing (gate E, issue #7).

    This branch does not merely skip some rules, it ACQUITS: Rules 7 and 10 and
    the Rule 8 refinement never run. It must not be entered on uncompressed input,
    where Rule 1's silence is an absence of measurement, not a negative result
    (the caller checks that).

    Default scan: Rule 13 before the acquittal (v1.20.0). A silent full-band file
    is exactly where a high-bitrate AAC or Vorbis transcode hides, and this branch
    used to acquit it without asking the one rule that reads it: on 33 loud CD
    tracks encoded at AAC 256 and Vorbis q6 the default scan caught 0 of 66,
    --deep 66, Rule 13 alone 63. When Rule 13 scores the file is not acquitted:
    it goes on to the witnesses deep mode runs (14, 15, 12, 16), exactly as
    --deep would take it. See ml/exchange/R13_DEFAULT_REGISTRATION_2026-10-01.md.

    Deep scan: the heuristics are silent, but that is precisely the 256-320 kbps
    AAC blind spot, so Rule 13 and the witnesses run regardless.
    """
    if not deep:
        r13_before = context.rule_scores.get("Rule13MDCTAlignment", 0)
        r13_ran = should_run_rule_13(context.cutoff_freq, context.current_score)
        if r13_ran:
            _ensure_audio(context)
            _run_rule_13(context)
        if context.rule_scores.get("Rule13MDCTAlignment", 0) <= r13_before:
            logger.info(
                f"OPTIMIZATION: Fast path for authentic file "
                f"(score={context.current_score}, no MP3"
                + (", Rule 13 read no grid)" if r13_ran else ")")
            )
            context.reasons.append(
                "⚡ Fast analysis: AUTHENTIC — heuristics silent, Rule 13 reads no MDCT grid"
                if r13_ran
                else "⚡ Fast analysis: AUTHENTIC detected without expensive rules"
            )
            return context.current_score, context.reasons
        logger.info(
            f"Rule 13 read an MDCT grid on a file the heuristics left silent "
            f"(score={context.current_score}): running the witnesses"
        )
    else:
        logger.info(
            f"DEEP: heuristics silent (score={context.current_score}), running "
            f"Rules 12/13 anyway (fast path bypassed)"
        )
        if should_run_rule_13(context.cutoff_freq, context.current_score):
            _ensure_audio(context)
            _run_rule_13(context)
    # Rule 14 must run on THIS path too: it is the branch for files whose
    # heuristics found nothing — high-bitrate AAC, Vorbis, every Opus transcode —
    # which is precisely the population the temporal witness exists for
    # (test_verdict_reachability).
    _run_rules_14_and_15(context)
    Rule12MLClassifier().apply(context)
    _run_rule_16_if_decisive(context)
    return context.current_score, context.reasons


def _refine_rule_8(
    context: ScoringContext,
    rule8: ScoringRule,
    initial_score: int,
    initial_reasons: List[str],
) -> None:
    """Re-run Rule 8 now that Rule 1's MP3 bitrate is known.

    The initial contribution is rolled back by exact-match reason filtering —
    fragile but acceptable as long as Rule 8's reasons stay deterministic for a
    given context. In practice this moves no score (Rule 1 only sets a bitrate
    below 0.95·Nyquist, Rule 8 only scores at or above it), but at that boundary
    the two can disagree by one float ulp, so it is kept exactly as it was.
    """
    context.current_score -= initial_score
    context.rule_scores["Rule8NyquistException"] = (
        context.rule_scores.get("Rule8NyquistException", 0) - initial_score
    )
    for reason in initial_reasons:
        if reason in context.reasons:
            context.reasons.remove(reason)
    rule8.apply(context)
    logger.info("RULE 8 (refined): Score updated")


def _release_audio(context: ScoringContext) -> None:
    """Drop the decoded audio held by the context and collect at once.

    The buffer is the largest allocation of the run; releasing it eagerly (and
    collecting) avoided bad_alloc in long loops. With a shared AudioCache the
    cache still holds its own copy until the analyzer clears it.
    """
    if context.audio_data is not None:
        logger.debug("OPTIMIZATION: Releasing audio buffer memory")
        context.audio_data = None
        context.loaded_sample_rate = None
        gc.collect()


def _apply_scoring_rules(context: ScoringContext, deep: bool = False) -> Tuple[int, List[str]]:
    """Apply the scoring rules, in the one order the engine was calibrated in.

    The order is load-bearing, not incidental: several gates read the CURRENT
    score and evidence families at the moment they are reached, and the list of
    reasons is output in the order the rules append to it.

    1. Rule 8 first (its protection is snapshotted for a later refinement).
    2. Rule 11 early, below 19 kHz, so a cassette source can disable Rule 1.
    3. The cheap rules (1, 2, 4, 5, 6).
    4. Short-circuit 1: convicted and corroborated.
    5. Short-circuit 2: the cheap rules found nothing — ``_silent_heuristics_path``.
    6. Rule 7 (19-21.5 kHz), the Rule 8 refinement, Rule 13, Rules 14 and 15.
    7. Short-circuit 3: convicted and corroborated.
    8. Rule 10 (once suspect), Rule 12, Rule 16 where it can decide.

    Args:
        context: The scoring context containing all necessary data.
        deep: If True, run Rule 12 even when the authentic fast path would otherwise
            short-circuit — so the high-confidence WARNING floor can catch silent
            AAC/Vorbis transcodes. See the ``--deep`` flag.

    Returns:
        Tuple of (total_score, list_of_reasons)
    """
    # Rule 8 MUST be calculated first and applied before any short-circuit.
    logger.debug("OPTIMIZATION: Calculating Rule 8 (Nyquist Exception) FIRST...")
    rule8 = Rule8NyquistException()
    rule8.apply(context)
    initial_r8_score = context.current_score
    initial_r8_reasons = list(context.reasons)
    logger.info(f"RULE 8 (pre-calculated): {initial_r8_score} points")

    try:
        # Rule 11 before Rule 1, so an authentic cassette rip can switch MP3-bitrate
        # scoring off. Expensive (bandpass filtering), hence the cutoff gate.
        rule11 = Rule11CassetteDetection()
        if context.cutoff_freq < _RULE11_MAX_CUTOFF_HZ:
            logger.info("Executing Rule 11 (Cassette) EARLY as priority...")
            logger.debug("OPTIMIZATION: Pre-loading full audio for Rule 11...")
            _ensure_audio(context)
            rule11.apply(context)

        logger.debug("OPTIMIZATION: Executing fast rules (R1-R6)...")
        is_uncompressed = _is_uncompressed_input(context.bitrate_metrics)
        # Threshold lowered 30 -> 15 in v1.8, purely to preserve behaviour: test 11C
        # was a constant +15 (it keyed off Rule 9C, which measured at chance) and has
        # been removed, so every remaining test keeps the weight it always had.
        if context.cassette_score >= CASSETTE_THRESHOLD:
            _credit_cassette_bonus(context, rule11)
        for rule in _fast_rules(context, is_uncompressed):
            rule.apply(context)
        logger.info(f"OPTIMIZATION: Fast rules + R8 (+R11?) score = {context.current_score}")

        # SHORT-CIRCUIT 1: already convicted — but only if the conviction is
        # CORROBORATED. Stopping here on a single-family score would be
        # self-defeating: the rules that could corroborate it (12 and 13) live
        # further down, so an early exit guarantees the file can never reach two
        # families, and the corroboration gate would end up measuring this
        # short-circuit rather than the evidence. (The two gates are written
        # inline on purpose: test_verdict_reachability reads them from this
        # function's source.)
        if context.current_score >= SCORE_FAKE_CERTAIN and _is_corroborated(context):
            logger.info(
                f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ "
                f"{SCORE_FAKE_CERTAIN} (corroborated)"
            )
            context.reasons.append(
                "⚡ Fast analysis: FAKE_CERTAIN detected without expensive rules"
            )
            return context.current_score, context.reasons

        # SHORT-CIRCUIT 2: the cheap rules found nothing (gate E, issue #7).
        # `mp3_bitrate_detected is None` reads as "Rule 1 looked and found nothing";
        # on uncompressed input Rule 1's container window has nothing to read, so
        # None is an absence of measurement and the engine has no standing to
        # acquit on it — the principle assessability.py applies at the verdict,
        # applied here, where the rules are chosen.
        if (
            context.current_score < _SILENT_HEURISTICS_MAX_SCORE
            and context.mp3_bitrate_detected is None
            and not is_uncompressed
        ):
            return _silent_heuristics_path(context, deep)

        # PHASE 2: Rule 7 in the 19-21.5 kHz band. (Rule 11 cannot be due here:
        # below 19 kHz it has already run above.)
        low, high = _RULE7_CUTOFF_RANGE_HZ
        if low <= context.cutoff_freq <= high:
            Rule7SilenceAnalysis().apply(context)
        else:
            logger.info("OPTIMIZATION: Skipping expensive rules (R7/R11)")

        # Rule 8 refined with the MP3 bitrate Rule 1 may have set.
        if context.mp3_bitrate_detected is not None:
            _refine_rule_8(context, rule8, initial_r8_score, initial_r8_reasons)

        # Rule 13: MDCT frame alignment. Gated on the file not being convicted
        # already; since v1.20.1 not on the cutoff (issue #12: a Vorbis -q1 file at
        # 16,750 Hz that every cheap rule let go). It runs AFTER the Rule 8
        # refinement so that the refinement cannot re-apply a protection Rule 13
        # has just withdrawn. See _run_rule_13.
        if should_run_rule_13(context.cutoff_freq, context.current_score):
            _ensure_audio(context)
            _run_rule_13(context)

        _run_rules_14_and_15(context)

        # SHORT-CIRCUIT 3: an uncorroborated score must not skip Rule 12, which is
        # one of the few rules that can corroborate it.
        if context.current_score >= SCORE_FAKE_CERTAIN and _is_corroborated(context):
            logger.info(
                f"OPTIMIZATION: Short-circuit at {context.current_score} ≥ "
                f"{SCORE_FAKE_CERTAIN} after expensive rules"
            )
            return context.current_score, context.reasons

        if context.current_score > _RULE10_MIN_SCORE:
            logger.info(
                f"OPTIMIZATION: Activating Rule 10 (score {context.current_score} > "
                f"{_RULE10_MIN_SCORE})"
            )
            Rule10Consistency().apply(context)
        else:
            logger.info(
                f"OPTIMIZATION: Skipping Rule 10 (score {context.current_score} ≤ "
                f"{_RULE10_MIN_SCORE})"
            )

        # Rule 12 after Rule 10 so the heuristic score is established first; the
        # CNN adds an independent signal on borderline cases. Rule 16 last, because
        # it can only complete a corroboration for a file carried to the bar on one
        # family.
        Rule12MLClassifier().apply(context)
        _run_rule_16_if_decisive(context)
        return context.current_score, context.reasons

    finally:
        _release_audio(context)


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
    measure_compressed_size: Optional[Callable[[], Optional[int]]] = None,
    deep: bool = False,
    residual_floor_db: float = float("nan"),
    edge_step_db: float = float("nan"),
    floor_above_db: float = float("nan"),
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
        compressed_size_bytes: Size of the audio once losslessly compressed, for any
            container. Takes precedence over sizing a file on disk, so the
            compression ratio Rule 1 reads describes the samples rather than the
            container they arrived in. See _calculate_bitrate_metrics.
        measure_compressed_size: A callable producing that size on demand, and the
            preferred form: it is invoked only at cutoffs where Rule 1 can still
            consult the container, which keeps the re-encode off the files that
            would take the authentic fast path. See _calculate_bitrate_metrics.
        deep: Run Rule 12 on every file, bypassing the authentic fast path (slower;
            catches silent-heuristic AAC/Vorbis transcodes). See the ``--deep`` flag.
        residual_floor_db: Spectral floor above the ~20.5 kHz wall (NaN = unknown).
            Drives Rule 1's near-Nyquist 320 kbps wall-hardness gate.
        edge_step_db: How far the spectrum falls across the detected edge, in dB
            over 500 Hz (NaN = no edge found). Drives Rule 1's gate D: an edge
            that does not step is a slope, and a slope is not an MP3 signature.
        floor_above_db: What is left above the detected edge, in dB relative to
            the reference (NaN = unknown). Drives Rule 1's depth gate: digital
            silence above the edge is a codec low-pass, whatever the step reads
            and whatever the container says.
        witnesses_out: Optional set, updated in place with the families that
            testify WITHOUT scoring (Rule 14). A points breakdown cannot carry
            them — that is the whole reason they exist — so callers that need to
            reconstruct the evidence set must be handed them separately, or they
            will silently recompute a smaller one.
        breakdown_out: Optional dict, updated in place with the per-rule score
            attribution for this file (``{"Rule2Cutoff": 25, …}``). Used by
            ml/rule_audit.py to measure each rule's discriminative power in
            isolation. A rule that ran is listed even when it added 0; a rule
            the gates never asked is absent.
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
            measure_compressed_size=measure_compressed_size,
            cutoff_freq=cutoff_freq,
            cutoff_std=cutoff_std,
            edge_step_db=edge_step_db,
            floor_above_db=floor_above_db,
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
            edge_step_db=edge_step_db,
            floor_above_db=floor_above_db,
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
