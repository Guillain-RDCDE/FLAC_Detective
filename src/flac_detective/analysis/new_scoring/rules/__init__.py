"""Rules package exporting all scoring rules."""

from .artifacts import apply_rule_9_compression_artifacts
from .bitrate import (
    apply_rule_3_source_vs_container,
    apply_rule_4_24bit_suspect,
    apply_rule_5_high_variance,
    apply_rule_6_variable_bitrate_protection,
)
from .cassette import apply_rule_11_cassette_detection
from .consistency import apply_rule_10_multi_segment_consistency
from .ml_classifier import apply_rule_12_ml_classifier
from .silence import apply_rule_7_silence_analysis
from .spectral import (
    apply_rule_1_mp3_bitrate,
    apply_rule_2_cutoff,
    apply_rule_8_nyquist_exception,
)

__all__ = [
    "apply_rule_1_mp3_bitrate",
    "apply_rule_2_cutoff",
    "apply_rule_3_source_vs_container",
    "apply_rule_4_24bit_suspect",
    "apply_rule_5_high_variance",
    "apply_rule_6_variable_bitrate_protection",
    "apply_rule_7_silence_analysis",
    "apply_rule_8_nyquist_exception",
    "apply_rule_9_compression_artifacts",
    "apply_rule_10_multi_segment_consistency",
    "apply_rule_11_cassette_detection",
    "apply_rule_12_ml_classifier",
]
