"""Centralized configuration for FLAC Detective."""

import os
from dataclasses import dataclass


@dataclass
class AnalysisConfig:
    """Configuration for spectral analysis."""

    # Sample duration to analyze (seconds)
    SAMPLE_DURATION: float = 30.0

    # Number of workers for multi-processing.
    #
    # Capped, and the cap is about START-UP, not about cores. Windows and macOS
    # spawn rather than fork, so every worker is a fresh interpreter that
    # re-imports the whole stack — numpy, scipy, soundfile and torch — before it
    # looks at a single file. Sixteen of those importing at once open thousands
    # of file handles in the same moment, and on Windows that fails with
    # `OSError: [WinError 1450] Insufficient system resources` inside the import
    # machinery, killing the worker before any audio is read.
    #
    # Reported from the field (issue: 36 files, 16 workers, Store Python 3.12 on
    # Windows 11) with a plausible but wrong diagnosis attached — "it loads all
    # the FLAC files into memory". The traceback is in `_fill_cache`, listing a
    # package directory during import. Nothing had been decoded yet.
    #
    # Eight is a declared ceiling, not a measured optimum: past it the marginal
    # file-per-second gain is small on any machine we have, and the start-up
    # cost is paid per process regardless. `--workers` overrides it in both
    # directions.
    WORKER_CAP: int = 8

    MAX_WORKERS: int = min(os.cpu_count() or 4, WORKER_CAP)

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
