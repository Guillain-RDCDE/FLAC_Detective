"""Centralized configuration for FLAC Detective."""

import os
from dataclasses import dataclass


@dataclass
class AnalysisConfig:
    """Configuration for spectral analysis."""

    # Sample duration to analyze (seconds)
    SAMPLE_DURATION: float = 30.0

    # Number of workers for multi-processing (defaults to CPU count)
    MAX_WORKERS: int = os.cpu_count() or 4

    # Auto-save interval (number of files)
    SAVE_INTERVAL: int = 50


@dataclass
class ScoringConfig:
    """Configuration for the scoring system."""

    # Score thresholds
    AUTHENTIC_THRESHOLD: int = 90  # >= 90% = Authentic
    PROBABLY_AUTHENTIC_THRESHOLD: int = 70  # >= 70% = Probably authentic
    SUSPECT_THRESHOLD: int = 50  # >= 50% = Suspect
    # < 50% = Fake

    # Penalties
    PENALTY_LOW_ENERGY: int = 30
    PENALTY_DURATION_MISMATCH: int = 20
    PENALTY_SUSPICIOUS_METADATA: int = 10


@dataclass
class SpectralConfig:
    """Configuration for spectral analysis."""

    # Reference zone for energy calculation (Hz)
    REFERENCE_FREQ_LOW: int = 10000
    REFERENCE_FREQ_HIGH: int = 14000

    # Start of cutoff scan (Hz)
    CUTOFF_SCAN_START: int = 14000

    # Analysis slice size (Hz)
    TRANCHE_SIZE: int = 250

    # Cutoff threshold (dB below reference)
    CUTOFF_THRESHOLD_DB: int = 30

    # Number of consecutive low slices to confirm a cutoff
    CONSECUTIVE_LOW_THRESHOLD: int = 2

    # Minimum frequency for high-frequency energy (Hz)
    HIGH_FREQ_THRESHOLD: int = 16000


@dataclass
class RepairConfig:
    """Configuration for the repair module."""

    # FLAC compression level (0-8, 8 = best)
    FLAC_COMPRESSION_LEVEL: int = 5

    # Create backup automatically
    BACKUP_ENABLED: bool = True

    # Tolerance for duration difference (samples)
    DURATION_TOLERANCE_SAMPLES: int = 588  # ~1 MP3 frame at 44.1kHz

    # Timeout for re-encoding operations (seconds)
    REENCODE_TIMEOUT: int = 300


# Instances globales (singleton pattern)
analysis_config = AnalysisConfig()
scoring_config = ScoringConfig()
spectral_config = SpectralConfig()
repair_config = RepairConfig()
