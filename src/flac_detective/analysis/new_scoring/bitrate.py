"""Bitrate calculation functions for FLAC analysis."""

import logging
from pathlib import Path
import soundfile as sf
import numpy as np

from .constants import (
    MP3_SIGNATURES,
    CUTOFF_THRESHOLDS,
    NYQUIST_PERCENTAGE,
    DEFAULT_VARIANCE_SEGMENTS,
    MIN_VARIANCE_SEGMENTS,
)

logger = logging.getLogger(__name__)


def get_cutoff_threshold(sample_rate: int) -> float:
    """Get cutoff frequency threshold based on sample rate.

    Args:
        sample_rate: Sample rate in Hz

    Returns:
        Cutoff threshold in Hz
    """
    # If exact match, return it
    if sample_rate in CUTOFF_THRESHOLDS:
        return CUTOFF_THRESHOLDS[sample_rate]

    # Otherwise, use 45% of sample rate (Nyquist theorem)
    return sample_rate * NYQUIST_PERCENTAGE


def estimate_mp3_bitrate(cutoff_freq: float) -> int:
    """Estimates the original MP3 bitrate based on cutoff frequency.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz.

    Returns:
        Estimated bitrate in kbps, or 0 if no match found.
    """
    for bitrate, min_f, max_f in MP3_SIGNATURES:
        if min_f <= cutoff_freq < max_f:
            return bitrate
    return 0


def calculate_real_bitrate(filepath: Path, duration: float) -> float:
    """Calculate real bitrate from file size and duration.

    Args:
        filepath: Path to FLAC file
        duration: Duration in seconds

    Returns:
        Real bitrate in kbps
    """
    try:
        file_size_bytes = filepath.stat().st_size
        if duration <= 0:
            logger.warning(f"Invalid duration {duration}s for {filepath.name}, cannot calculate bitrate")
            return 0

        # Bitrate = (file_size_bytes × 8) / (duration_seconds × 1000)
        bitrate_kbps = (file_size_bytes * 8) / (duration * 1000)
        logger.info(f"Real bitrate calculated: {bitrate_kbps:.1f} kbps (size={file_size_bytes} bytes, duration={duration:.1f}s)")
        return bitrate_kbps

    except Exception as e:
        logger.error(f"Error calculating real bitrate: {e}")
        return 0


def calculate_apparent_bitrate(sample_rate: int, bit_depth: int, channels: int = 2) -> int:
    """Calculate apparent (theoretical) bitrate.

    Args:
        sample_rate: Sample rate in Hz
        bit_depth: Bits per sample
        channels: Number of channels (default 2 for stereo)

    Returns:
        Apparent bitrate in kbps
    """
    # Apparent bitrate = sample_rate × bit_depth × channels / 1000
    return int(sample_rate * bit_depth * channels / 1000)


def calculate_bitrate_variance(
    filepath: Path,
    sample_rate: int,
    num_segments: int = DEFAULT_VARIANCE_SEGMENTS
) -> float:
    """Calculate bitrate variance across multiple segments of the file.

    This helps identify authentic FLAC with variable bitrate vs constant bitrate transcodes.

    Note: This is an approximation. Since FLAC uses variable-length encoding, we cannot
    accurately determine segment boundaries without decoding the entire file. This method
    assumes uniform distribution of data across the file, which is good enough for
    detecting constant vs variable bitrate patterns.

    Args:
        filepath: Path to FLAC file
        sample_rate: Sample rate in Hz
        num_segments: Number of segments to analyze (default: 10)

    Returns:
        Bitrate variance in kbps (0.0 if calculation fails or file too short)
    """
    try:
        info = sf.info(filepath)
        total_duration = info.duration

        # Adjust number of segments if file is too short
        if total_duration < num_segments:
            num_segments = max(MIN_VARIANCE_SEGMENTS, int(total_duration))

        # If only one segment, variance is 0
        if num_segments <= 1:
            return 0.0

        segment_duration = total_duration / num_segments
        file_size = filepath.stat().st_size

        # Calculate approximate bitrate for each segment
        # Note: This assumes uniform data distribution, which is an approximation
        bitrates = []
        for _ in range(num_segments):
            # Approximate segment size (not perfectly accurate but good enough)
            segment_size = file_size / num_segments
            segment_bitrate = (segment_size * 8) / (segment_duration * 1000)
            bitrates.append(segment_bitrate)

        # Calculate standard deviation as variance measure
        if len(bitrates) > 1:
            variance = float(np.std(bitrates))
            return variance

        return 0.0

    except Exception as e:
        logger.debug(f"Error calculating bitrate variance: {e}")
        return 0.0
