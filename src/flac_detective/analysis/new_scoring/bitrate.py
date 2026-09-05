"""Bitrate calculation functions for FLAC analysis."""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from .constants import (
    CUTOFF_THRESHOLDS,
    DEFAULT_VARIANCE_SEGMENTS,
    MIN_VARIANCE_SEGMENTS,
    MP3_SIGNATURES,
    NYQUIST_PERCENTAGE,
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
            logger.warning(
                f"Invalid duration {duration}s for {filepath.name}, cannot calculate bitrate"
            )
            return 0

        # Bitrate = (file_size_bytes × 8) / (duration_seconds × 1000)
        bitrate_kbps = (file_size_bytes * 8) / (duration * 1000)
        logger.debug(
            f"Real bitrate: {bitrate_kbps:.1f} kbps (size: {file_size_bytes} bytes, duration: {duration:.1f}s)"
        )
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
    filepath: Path, sample_rate: int, num_segments: int = DEFAULT_VARIANCE_SEGMENTS
) -> Optional[float]:
    """Standard deviation of the bitrate across ``num_segments`` slices, in kbps.

    A lossless encoder spends more bits on dense passages than on sparse ones, so
    genuine music varies across a track where a decoded constant-bitrate transcode
    does not. That is the statistic Rules 5 and 6 read.

    **It was never measured.** Until now this function computed every segment's
    size as ``file_size / num_segments`` — the same number, ten times — and
    returned the standard deviation of ten identical values. It returned 0.0 for
    every file this tool has ever analysed, and did so silently, as if it had
    looked. Rule 5 needs > 100 and Rule 6 needs > 50, so both have been
    structurally unreachable since they were written, while their unit tests
    passed by handing the rules a variance directly and never asking whether one
    could arrive.

    Each slice is now actually compressed. Measured on 40 corpus files:

        median 41.2 kbps, mean 44.2, min 15.1, **max 86.7**

    which settles the two rules differently and neither by opinion:

    * **Rule 6 becomes reachable** — 15 of those 40 clear its > 50 bar.
    * **Rule 5 does not.** Its > 100 bar sits above the highest value the
      statistic took on any file measured. Repairing the function does not revive
      it; the threshold is outside the range of the thing it thresholds. That is a
      calibration defect, recorded here and left for its own release rather than
      quietly retuned inside a bug fix.

    Returns None when the measurement could not be taken, never 0.0. A fabricated
    zero is what let this hide: an absence coerced to a number at the point it is
    consumed reads exactly like a real reading of "no variation at all", which is
    the strongest possible evidence of a constant-bitrate source.

    Args:
        filepath: Path to the audio file
        sample_rate: Sample rate in Hz (unused; kept for the existing call sites)
        num_segments: Number of slices to compress separately (default: 10)

    Returns:
        Standard deviation in kbps, or None when it could not be measured.
    """
    from ..audio_formats import flac_segment_bitrates

    try:
        info = sf.info(filepath)
        if info.duration < num_segments:
            num_segments = max(MIN_VARIANCE_SEGMENTS, int(info.duration))
        if num_segments <= 1:
            return None

        bitrates = flac_segment_bitrates(filepath, num_segments)
        if not bitrates or len(bitrates) < 2:
            return None
        return float(np.std(bitrates))

    except Exception as e:
        logger.debug(f"Error calculating bitrate variance: {e}")
        return None
