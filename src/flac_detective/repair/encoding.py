"""FLAC file re-encoding."""

import logging
from pathlib import Path

import soundfile as sf

from ..config import repair_config

logger = logging.getLogger(__name__)


def reencode_flac(
    input_path: Path, output_path: Path, compression_level: int | None = None
) -> bool:
    """Re-encodes a FLAC file using soundfile.

    This function reads the FLAC file, then rewrites it, which forces
    recalculation of the FLAC container metadata (especially duration).

    Args:
        input_path: Source file.
        output_path: Destination file.
        compression_level: 0-8 (8 = best compression). If None, uses config.
            Note: soundfile uses libFLAC which has its own compression levels.

    Returns:
        True if successful, False otherwise.
    """
    if compression_level is None:
        compression_level = repair_config.FLAC_COMPRESSION_LEVEL

    try:
        logger.debug(f"  Reading FLAC file: {input_path.name}")

        # Read complete audio file
        data, samplerate = sf.read(input_path, dtype='float32')

        logger.debug(f"  Re-encoding to FLAC (level {compression_level})...")

        # Compression level mapping (0-8) to soundfile levels
        # soundfile/libFLAC uses levels 0 to 8
        # We can pass the level directly via subtype options
        subtype_map = {
            0: 'PCM_16',  # No compression (fast)
            1: 'PCM_16',
            2: 'PCM_16',
            3: 'PCM_16',
            4: 'PCM_16',
            5: 'PCM_16',  # Default
            6: 'PCM_24',  # Better quality
            7: 'PCM_24',
            8: 'PCM_24',  # Best compression
        }

        # Write new FLAC file
        # soundfile automatically recalculates all container metadata
        sf.write(
            output_path,
            data,
            samplerate,
            format='FLAC',
            subtype=subtype_map.get(compression_level, 'PCM_16')
        )

        logger.debug(f"  ✓ File re-encoded: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Re-encoding error: {e}")
        if output_path.exists():
            output_path.unlink()
        return False
