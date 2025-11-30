"""FLAC metadata management."""

import logging
from pathlib import Path
from typing import Dict

import soundfile as sf
from mutagen.flac import FLAC

logger = logging.getLogger(__name__)


def read_metadata(filepath: Path) -> Dict:
    """Reads FLAC file metadata.

    Args:
        filepath: Path to FLAC file.

    Returns:
        Dictionary containing metadata (sample_rate, bit_depth, etc.).
    """
    try:
        audio = FLAC(filepath)
        info = audio.info

        return {
            "sample_rate": info.sample_rate,
            "bit_depth": info.bits_per_sample,
            "channels": info.channels,
            "duration": info.length,
            "encoder": audio.get("encoder", ["Unknown"])[0]
            if audio.get("encoder")
            else "Unknown",
        }
    except Exception as e:
        logger.debug(f"Metadata reading error: {e}")
        return {}


def check_duration_consistency(filepath: Path, metadata: Dict) -> Dict:
    """Checks consistency between declared duration and real duration.

    Industry standard criterion: durations must match.
    A discrepancy can indicate a corrupted file or failed transcoding.

    Args:
        filepath: Path to FLAC file.
        metadata: File metadata.

    Returns:
        Dict with: mismatch, metadata_duration, real_duration, diff_samples, diff_ms.
    """
    try:
        # Duration from FLAC metadata
        metadata_duration = metadata.get("duration", 0)

        # Real duration by reading audio file
        info = sf.info(filepath)
        real_duration = info.duration

        # Difference in samples (more precise than seconds)
        sample_rate = metadata.get("sample_rate", info.samplerate)
        metadata_samples = int(metadata_duration * sample_rate)
        real_samples = int(real_duration * sample_rate)
        diff_samples = abs(metadata_samples - real_samples)

        # Tolerance: 1 frame (588 samples for 44.1kHz, ~13ms)
        tolerance_samples = 588

        # Calculate offset in milliseconds
        diff_ms = (diff_samples / sample_rate) * 1000

        mismatch = diff_samples > tolerance_samples

        if mismatch:
            mismatch_str = f"⚠️ Mismatch: {diff_samples:,} samples ({diff_ms:.1f}ms)"
        else:
            mismatch_str = "✓ Consistent durations"

        return {
            "mismatch": mismatch_str if mismatch else None,
            "metadata_duration": f"{metadata_duration:.3f}s",
            "real_duration": f"{real_duration:.3f}s",
            "diff_samples": diff_samples,
            "diff_ms": diff_ms,
        }

    except Exception as e:
        logger.debug(f"Duration check error: {e}")
        return {
            "mismatch": None,
            "metadata_duration": "N/A",
            "real_duration": "N/A",
            "diff_samples": 0,
            "diff_ms": 0,
        }
