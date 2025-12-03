"""Data models for the new scoring system."""

from typing import NamedTuple


class BitrateMetrics(NamedTuple):
    """Container for bitrate-related metrics."""
    real_bitrate: float
    apparent_bitrate: int
    variance: float


class AudioMetadata(NamedTuple):
    """Container for parsed audio metadata."""
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float
