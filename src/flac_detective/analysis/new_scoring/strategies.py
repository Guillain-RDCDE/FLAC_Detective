"""Strategy pattern implementation for scoring rules."""

import logging
from abc import ABC, abstractmethod

from .models import ScoringContext
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
    apply_rule_11_cassette_detection,
)

logger = logging.getLogger(__name__)


class ScoringRule(ABC):
    """Abstract base class for a scoring rule strategy."""

    @abstractmethod
    def apply(self, context: ScoringContext) -> None:
        """Apply the rule and update the context."""

    @property
    def name(self) -> str:
        return self.__class__.__name__


class Rule1MP3Bitrate(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        (score, reasons), estimated_bitrate = apply_rule_1_mp3_bitrate(
            context.cutoff_freq,
            context.bitrate_metrics.real_bitrate,
            context.cutoff_std,
            context.audio_meta.sample_rate,
            context.energy_ratio
        )
        context.add_score(score, reasons)
        context.mp3_bitrate_detected = estimated_bitrate


class Rule2Cutoff(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_2_cutoff(
            context.cutoff_freq,
            context.audio_meta.sample_rate
        )
        context.add_score(score, reasons)


class Rule3SourceVsContainer(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_3_source_vs_container(
            context.mp3_bitrate_detected,
            context.bitrate_metrics.real_bitrate
        )
        context.add_score(score, reasons)


class Rule424BitSuspect(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_4_24bit_suspect(
            context.audio_meta.bit_depth,
            context.mp3_bitrate_detected,
            context.cutoff_freq,
            context.silence_ratio
        )
        context.add_score(score, reasons)


class Rule5HighVariance(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_5_high_variance(
            context.bitrate_metrics.real_bitrate,
            context.bitrate_metrics.variance
        )
        context.add_score(score, reasons)


class Rule6HighQualityProtection(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_6_variable_bitrate_protection(
            context.mp3_bitrate_detected,
            context.bitrate_metrics.real_bitrate,
            context.cutoff_freq,
            context.bitrate_metrics.variance
        )
        context.add_score(score, reasons)


class Rule7SilenceAnalysis(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        # Check activation condition locally or rely on the inner function
        # The inner function checks 19k-21.5k range
        score, reasons, ratio = apply_rule_7_silence_analysis(
            str(context.filepath),
            context.cutoff_freq,
            context.audio_meta.sample_rate
        )
        context.add_score(score, reasons)
        context.silence_ratio = ratio


class Rule8NyquistException(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        # This rule might be applied multiple times (initial and refined)
        # The context handles score accumulation, so we need to be careful not to double count
        # if this is called twice.
        # However, the calculator logic handles the "refinement" by removing previous score.
        # Here we just apply what we know.
        score, reasons = apply_rule_8_nyquist_exception(
            context.cutoff_freq,
            context.audio_meta.sample_rate,
            context.mp3_bitrate_detected,
            context.silence_ratio
        )
        # Note: The caller (calculator) is responsible for managing the "update" logic
        # (subtracting old score) if this is a re-run.
        # Or we can make this rule smart enough to know?
        # For now, let's assume the calculator handles the flow control.
        context.add_score(score, reasons)


class Rule9CompressionArtifacts(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        # Check activation condition
        run_rule9 = context.cutoff_freq < 21000 or context.mp3_bitrate_detected is not None

        if run_rule9:
            score, reasons, details = apply_rule_9_compression_artifacts(
                str(context.filepath),
                context.cutoff_freq,
                context.mp3_bitrate_detected,
                audio_data=context.audio_data,
                sample_rate=context.loaded_sample_rate
            )
            context.add_score(score, reasons)
            context.mp3_pattern_detected = details.get('mp3_noise_pattern', False)
        else:
            logger.debug("RULE 9: Skipped (cutoff >= 21000 and no MP3 detected)")


class Rule10Consistency(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_10_multi_segment_consistency(
            str(context.filepath),
            context.current_score,
            context.audio_meta.sample_rate,
            context.bitrate_metrics.real_bitrate
        )
        context.add_score(score, reasons)


class Rule11CassetteDetection(ScoringRule):
    def apply(self, context: ScoringContext) -> None:
        score, reasons = apply_rule_11_cassette_detection(
            str(context.filepath),
            context.cutoff_freq,
            context.cutoff_std,
            context.mp3_pattern_detected,
            context.audio_meta.sample_rate,
            audio_data=context.audio_data
        )
        context.add_score(score, reasons)
