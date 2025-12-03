"""Metadata parsing functions for FLAC analysis."""

import logging
from typing import Dict

from .models import AudioMetadata

logger = logging.getLogger(__name__)


def parse_metadata(metadata: Dict) -> AudioMetadata:
    """Parse and validate metadata dictionary.

    Args:
        metadata: Raw metadata dictionary

    Returns:
        AudioMetadata with validated values
    """
    # Extract and validate sample_rate
    sample_rate = metadata.get("sample_rate", 44100)
    if isinstance(sample_rate, str):
        try:
            sample_rate = int(sample_rate)
        except (ValueError, TypeError):
            logger.warning(f"Invalid sample_rate '{sample_rate}', using default 44100")
            sample_rate = 44100

    # Extract and validate bit_depth
    bit_depth = metadata.get("bit_depth", 16)
    if isinstance(bit_depth, str):
        try:
            bit_depth = int(bit_depth)
        except (ValueError, TypeError):
            logger.warning(f"Invalid bit_depth '{bit_depth}', using default 16")
            bit_depth = 16

    # Extract channels and duration
    channels = metadata.get("channels", 2)
    duration = metadata.get("duration", 0)

    return AudioMetadata(
        sample_rate=sample_rate,
        bit_depth=bit_depth,
        channels=channels,
        duration=duration
    )
