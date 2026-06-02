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
    apply_rule_12_ml_classifier,
)

logger = logging.getLogger(__name__)


class ScoringRule(ABC):
    """Abstract base class for a scoring rule strategy."""

    @abstractmethod
    def apply(self, context: ScoringContext) -> None:
        """Apply the rule and update the context."""

    @property
    def name(self) -> str:
        """Return the rule's class name."""
        return self.__class__.__name__


class Rule1MP3Bitrate(ScoringRule):
    """Rule 1 — flag MP3-bitrate spectral signatures (cutoff vs bitrate)."""

    def apply(self, context: ScoringContext) -> None:
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
        )
        context.add_score(score, reasons)
        context.mp3_bitrate_detected = estimated_bitrate


class Rule2Cutoff(ScoringRule):
    """Rule 2 — flag a low spectral cutoff relative to the sample rate."""

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 2 to ``context``."""
        score, reasons = apply_rule_2_cutoff(context.cutoff_freq, context.audio_meta.sample_rate)
        context.add_score(score, reasons)


class Rule3SourceVsContainer(ScoringRule):
    """Rule 3 — compare the detected source bitrate against the container."""

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 3 to ``context``."""
        score, reasons = apply_rule_3_source_vs_container(
            context.mp3_bitrate_detected, context.bitrate_metrics.real_bitrate
        )
        context.add_score(score, reasons)


class Rule424BitSuspect(ScoringRule):
    """Rule 4 — flag suspicious 24-bit files paired with a low cutoff."""

    def apply(self, context: ScoringContext) -> None:
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

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 5 to ``context``."""
        score, reasons = apply_rule_5_high_variance(
            context.bitrate_metrics.real_bitrate, context.bitrate_metrics.variance
        )
        context.add_score(score, reasons)


class Rule6HighQualityProtection(ScoringRule):
    """Rule 6 — protect genuine high-quality / variable-bitrate sources."""

    def apply(self, context: ScoringContext) -> None:
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

    def apply(self, context: ScoringContext) -> None:
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

    def apply(self, context: ScoringContext) -> None:
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


class Rule9CompressionArtifacts(ScoringRule):
    """Rule 9 — detect lossy compression artefacts (pre-echo, aliasing)."""

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 9 to ``context``."""
        # Check activation condition
        run_rule9 = context.cutoff_freq < 21000 or context.mp3_bitrate_detected is not None

        if run_rule9:
            score, reasons, details = apply_rule_9_compression_artifacts(
                str(context.filepath),
                context.cutoff_freq,
                context.mp3_bitrate_detected,
                audio_data=context.audio_data,
                sample_rate=context.loaded_sample_rate,
            )
            context.add_score(score, reasons)
            context.mp3_pattern_detected = details.get("mp3_noise_pattern", False)
        else:
            logger.debug("RULE 9: Skipped (cutoff >= 21000 and no MP3 detected)")


class Rule10Consistency(ScoringRule):
    """Rule 10 — check multi-segment score consistency."""

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 10 to ``context``."""
        score, reasons = apply_rule_10_multi_segment_consistency(
            str(context.filepath),
            context.current_score,
            context.audio_meta.sample_rate,
            context.bitrate_metrics.real_bitrate,
        )
        context.add_score(score, reasons)


class Rule11CassetteDetection(ScoringRule):
    """Rule 11 — protect analog cassette transfers from false flags."""

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 11 to ``context``."""
        score, reasons = apply_rule_11_cassette_detection(
            str(context.filepath),
            context.cutoff_freq,
            context.cutoff_std,
            context.mp3_pattern_detected,
            context.audio_meta.sample_rate,
            audio_data=context.audio_data,
        )
        context.add_score(score, reasons)


class Rule12MLClassifier(ScoringRule):
    """Rule 12 — optional CNN-based transcode detection.

    No-op if the model or torch is not available. See
    ``rules.ml_classifier`` for the scoring logic.
    """

    def apply(self, context: ScoringContext) -> None:
        """Apply Rule 12 to ``context``."""
        score, reasons = apply_rule_12_ml_classifier(context.filepath)
        context.add_score(score, reasons)
