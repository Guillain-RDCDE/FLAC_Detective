"""New FLAC fake detection scoring system based on machine specifications.

This package implements a 0-100 point scoring system where:
- Higher score = More likely to be fake
- Score >= 86: FAKE_CERTAIN
- Score >= 61: SUSPICIOUS
- Score >= 31: WARNING
- Score < 31: AUTHENTIC

Range: 0-150 points
"""

from .bitrate import (
    calculate_apparent_bitrate,
    calculate_bitrate_variance,
    calculate_real_bitrate,
    estimate_mp3_bitrate,
    get_cutoff_threshold,
)
from .calculator import new_calculate_score
from .constants import (
    COHERENT_BITRATE_THRESHOLD,
    HIGH_BITRATE_THRESHOLD,
    MP3_SIGNATURES,
    MP3_STANDARD_BITRATES,
    SCORE_FAKE_CERTAIN,
    SCORE_SUSPICIOUS,
    SCORE_WARNING,
    VARIANCE_THRESHOLD,
)
from .metadata import parse_metadata
from .models import AudioMetadata, BitrateMetrics
from .verdict import determine_verdict

__all__ = [
    # Models
    "AudioMetadata",
    "BitrateMetrics",
    # Constants
    "MP3_STANDARD_BITRATES",
    "MP3_SIGNATURES",
    "SCORE_FAKE_CERTAIN",
    "SCORE_SUSPICIOUS",
    "SCORE_WARNING",
    "VARIANCE_THRESHOLD",
    "HIGH_BITRATE_THRESHOLD",
    "COHERENT_BITRATE_THRESHOLD",
    # Functions
    "calculate_real_bitrate",
    "calculate_apparent_bitrate",
    "calculate_bitrate_variance",
    "estimate_mp3_bitrate",
    "get_cutoff_threshold",
    "determine_verdict",
    "parse_metadata",
    "new_calculate_score",
]
