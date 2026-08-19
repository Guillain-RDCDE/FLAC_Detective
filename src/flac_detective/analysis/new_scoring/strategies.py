"""Strategy pattern implementation for scoring rules."""

import logging
from abc import ABC, abstractmethod

from .models import ScoringContext
from .rules import (
    apply_rule_1_mp3_bitrate,
    apply_rule_2_cutoff,
    apply_rule_4_24bit_suspect,
    apply_rule_5_high_variance,
    apply_rule_6_variable_bitrate_protection,
    apply_rule_7_silence_analysis,
    apply_rule_8_nyquist_exception,
    apply_rule_10_multi_segment_consistency,
    apply_rule_11_cassette_detection,
    apply_rule_12_ml_classifier,
    apply_rule_13_mdct_alignment,
    apply_rule_14_temporal_seam,
    apply_rule_15_stereo_seam,
)

logger = logging.getLogger(__name__)


class ScoringRule(ABC):
    """Abstract base class for a scoring rule strategy.

    Subclasses implement ``_apply``; the public ``apply`` is a template method
    that marks the context so every ``add_score`` call is attributed to this
    rule (see ``ScoringContext.rule_scores``). Rules that call other rules or
    that are invoked twice (Rule 8's refinement) accumulate, which is the
    intended reading: "what this rule contributed to this file, in total".
    """

    @abstractmethod
    def _apply(self, context: ScoringContext) -> None:
        """Apply the rule and update the context."""

    def apply(self, context: ScoringContext) -> None:
        """Run the rule with per-rule score attribution enabled."""
        previous = context.active_rule
        context.active_rule = self.name
        try:
            self._apply(context)
        finally:
            context.active_rule = previous

    @property
    def name(self) -> str:
        """Return the rule's class name."""
        return self.__class__.__name__


class Rule1MP3Bitrate(ScoringRule):
    """Rule 1 — flag MP3-bitrate spectral signatures (cutoff vs bitrate)."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 1 to ``context``."""
        logger.debug(
            f"Rule 1: real_bitrate={context.bitrate_metrics.real_bitrate:.1f} kbps | "
            f"duration={context.audio_meta.duration:.3f}s"
        )
        (score, reasons), estimated_bitrate = apply_rule_1_mp3_bitrate(
            context.cutoff_freq,
            context.bitrate_metrics.real_bitrate,
            context.cutoff_std,
            context.audio_meta.sample_rate,
            context.energy_ratio,
            residual_floor_db=context.residual_floor_db,
        )
        context.add_score(score, reasons)
        context.mp3_bitrate_detected = estimated_bitrate


class Rule2Cutoff(ScoringRule):
    """Rule 2 — flag a low spectral cutoff relative to the sample rate."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 2 to ``context``."""
        score, reasons = apply_rule_2_cutoff(context.cutoff_freq, context.audio_meta.sample_rate)
        context.add_score(score, reasons)


class Rule424BitSuspect(ScoringRule):
    """Rule 4 — flag suspicious 24-bit files paired with a low cutoff."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 4 to ``context``."""
        score, reasons = apply_rule_4_24bit_suspect(
            context.audio_meta.bit_depth,
            context.mp3_bitrate_detected,
            context.cutoff_freq,
            context.silence_ratio,
        )
        context.add_score(score, reasons)


class Rule5HighVariance(ScoringRule):
    """Rule 5 — flag implausibly high bitrate variance."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 5 to ``context``."""
        score, reasons = apply_rule_5_high_variance(
            context.bitrate_metrics.real_bitrate, context.bitrate_metrics.variance
        )
        context.add_score(score, reasons)


class Rule6HighQualityProtection(ScoringRule):
    """Rule 6 — protect genuine high-quality / variable-bitrate sources."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 6 to ``context``."""
        score, reasons = apply_rule_6_variable_bitrate_protection(
            context.mp3_bitrate_detected,
            context.bitrate_metrics.real_bitrate,
            context.cutoff_freq,
            context.bitrate_metrics.variance,
        )
        context.add_score(score, reasons)


class Rule7SilenceAnalysis(ScoringRule):
    """Rule 7 — analyse HF energy in silent passages."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 7 to ``context``."""
        # Check activation condition locally or rely on the inner function
        # The inner function checks 19k-21.5k range
        score, reasons, ratio = apply_rule_7_silence_analysis(
            str(context.filepath), context.cutoff_freq, context.audio_meta.sample_rate
        )
        context.add_score(score, reasons)
        context.silence_ratio = ratio


class Rule8NyquistException(ScoringRule):
    """Rule 8 — Nyquist exception handling for high-cutoff files."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 8 to ``context``."""
        # This rule might be applied multiple times (initial and refined)
        # The context handles score accumulation, so we need to be careful not to double count
        # if this is called twice.
        # However, the calculator logic handles the "refinement" by removing previous score.
        # Here we just apply what we know.
        score, reasons = apply_rule_8_nyquist_exception(
            context.cutoff_freq,
            context.audio_meta.sample_rate,
            context.mp3_bitrate_detected,
            context.silence_ratio,
        )
        # Note: The caller (calculator) is responsible for managing the "update" logic
        # (subtracting old score) if this is a re-run.
        # Or we can make this rule smart enough to know?
        # For now, let's assume the calculator handles the flow control.
        context.add_score(score, reasons)


class Rule10Consistency(ScoringRule):
    """Rule 10 — check multi-segment score consistency."""

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 10 to ``context``."""
        score, reasons = apply_rule_10_multi_segment_consistency(
            str(context.filepath),
            context.current_score,
            context.audio_meta.sample_rate,
            context.bitrate_metrics.real_bitrate,
        )
        context.add_score(score, reasons)


class Rule11CassetteDetection(ScoringRule):
    """Rule 11 — protect analog cassette transfers from false flags.

    Contributes NOTHING to the transcode score. Its output is evidence that the
    source is an analog transfer, which the calculator turns into protection.
    Adding it to the score — as this did until v1.8 — penalises exactly the
    genuine files it was written to defend (measured AUC 0.321, i.e. inverted).
    """

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 11 to ``context``, recording the signal without scoring it."""
        score, reasons = apply_rule_11_cassette_detection(
            str(context.filepath),
            context.cutoff_freq,
            context.cutoff_std,
            context.audio_meta.sample_rate,
            audio_data=context.audio_data,
        )
        context.cassette_score = score
        # Reasons are kept (they explain the verdict) but carry zero points.
        context.add_score(0, reasons)


class Rule12MLClassifier(ScoringRule):
    """Rule 12 — optional CNN-based transcode detection.

    No-op if the model or torch is not available. See
    ``rules.ml_classifier`` for the scoring logic.
    """

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 12 to ``context``."""
        # Pass the heuristic baseline (R1-R11) so R12 can apply its high-confidence
        # WARNING floor — lifting a confident detection on an otherwise-silent file
        # (high-bitrate AAC/Vorbis) just to WARNING. R12 runs last, so current_score
        # is exactly the heuristic total here.
        score, reasons = apply_rule_12_ml_classifier(context.filepath, context.current_score)
        context.add_score(score, reasons)


class Rule13MDCTAlignment(ScoringRule):
    """Rule 13 — MDCT frame-alignment detection for high-bitrate transcodes.

    The only rule that does not read the spectral cutoff or the band above it,
    which is why it is the only one that still works at 256-320 kbps AAC. See
    ``rules.mdct_alignment``.
    """

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 13 to ``context``."""
        score, reasons, details = apply_rule_13_mdct_alignment(
            str(context.filepath),
            context.cutoff_freq,
            audio_data=context.audio_data,
            sample_rate=context.loaded_sample_rate,
        )
        context.add_score(score, reasons)
        context.mdct_peak_ratio = details.get("mdct_peak_ratio", float("nan"))


class Rule14TemporalSeam(ScoringRule):
    """Rule 14 — the temporal seam, a witness that testifies without scoring.

    The only rule in the engine that declares an evidence family while adding zero
    points. Its statistic reads AUC 0.84 on Opus, where the hole family and the
    lattice family are both dead, and it also fires on ~8 % of real music. Awarding
    it points to make it count was measured first and produced three new false
    convictions on 258 genuine files; awarding none produces zero. See
    ``rules.temporal_seam``.
    """

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 14 to ``context``."""
        score, reasons, details = apply_rule_14_temporal_seam(
            str(context.filepath),
            context.cutoff_freq,
            audio_data=context.audio_data,
            sample_rate=context.loaded_sample_rate,
        )
        context.add_score(score, reasons)
        context.temporal_seam = details.get("temporal_seam", float("nan"))
        if details.get("temporal_witness"):
            context.witness_families.add("temporal")


class Rule15StereoSeam(ScoringRule):
    """Rule 15 — joint-stereo dead runs, a witness that testifies without scoring.

    The strongest independent observable this engine holds: AUC 0.96 on Opus,
    Vorbis and mp3_320, against a genuine fire rate of 11 %. Zero points, for the
    same measured reason as Rule 14 — and it declines to testify entirely on mono
    material, where the absence of a side channel would otherwise manufacture a
    maximal reading. See ``rules.stereo_seam``.
    """

    def _apply(self, context: ScoringContext) -> None:
        """Apply Rule 15 to ``context``."""
        score, reasons, details = apply_rule_15_stereo_seam(
            str(context.filepath),
            context.cutoff_freq,
            audio_data=context.audio_data,
            sample_rate=context.loaded_sample_rate,
        )
        context.add_score(score, reasons)
        context.stereo_dead_run = details.get("stereo_dead_run", float("nan"))
        if details.get("stereo_witness"):
            context.witness_families.add("stereo")
