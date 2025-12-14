"""Data models for the new scoring system."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, NamedTuple, Optional


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


@dataclass
class ScoringContext:
    """Context holding all data for the scoring process."""
    filepath: Path
    audio_meta: AudioMetadata
    bitrate_metrics: BitrateMetrics
    cutoff_freq: float
    cutoff_std: float = 0.0
    energy_ratio: float = 0.0

    # State updated during scoring
    mp3_bitrate_detected: Optional[int] = None
    silence_ratio: Optional[float] = None
    mp3_pattern_detected: bool = False
    current_score: int = 0
    reasons: List[str] = field(default_factory=list)
    
    # Cache for heavy rules (Rule 9/11) - Avoids reloading file
    audio_data: Optional[object] = None  # Using object to avoid numpy dependency in models
    loaded_sample_rate: Optional[int] = None

    def add_score(self, score: int, new_reasons: List[str]):
        """Update score and reasons."""
        self.current_score += score
        self.reasons.extend(new_reasons)
        # Ensure score doesn't go below 0
        self.current_score = max(0, self.current_score)
