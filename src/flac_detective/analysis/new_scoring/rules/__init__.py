"""Rules package exporting all scoring rules."""

from .bitrate import (
    apply_rule_4_24bit_suspect,
    apply_rule_5_high_variance,
    apply_rule_6_variable_bitrate_protection,
)
from .cassette import apply_rule_11_cassette_detection
from .consistency import apply_rule_10_multi_segment_consistency
from .mdct_alignment import apply_rule_13_mdct_alignment, should_run_rule_13
from .ml_classifier import apply_rule_12_ml_classifier
from .silence import apply_rule_7_silence_analysis
from .spectral import (
    apply_rule_1_mp3_bitrate,
    apply_rule_2_cutoff,
    apply_rule_8_nyquist_exception,
)
from .temporal_seam import apply_rule_14_temporal_seam

__all__ = [
    "apply_rule_1_mp3_bitrate",
    "apply_rule_2_cutoff",
    "apply_rule_4_24bit_suspect",
    "apply_rule_5_high_variance",
    "apply_rule_6_variable_bitrate_protection",
    "apply_rule_7_silence_analysis",
    "apply_rule_8_nyquist_exception",
    "apply_rule_10_multi_segment_consistency",
    "apply_rule_11_cassette_detection",
    "apply_rule_12_ml_classifier",
    "apply_rule_13_mdct_alignment",
    "apply_rule_14_temporal_seam",
    "should_run_rule_13",
]
