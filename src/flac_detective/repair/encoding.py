"""FLAC file re-encoding, lossless by construction."""

import logging
from pathlib import Path

import soundfile as sf

from ..config import repair_config

logger = logging.getLogger(__name__)

# The subtypes libsndfile writes into a FLAC container. The source's own is
# kept; anything else (a float or 32-bit source) does not fit a FLAC without a
# decision a repair must not take on its own.
_FLAC_SUBTYPES = ("PCM_S8", "PCM_16", "PCM_24")

# flac's own compression levels run 0-8; soundfile takes a 0.0-1.0 fraction.
_MAX_FLAC_LEVEL = 8


def _target_subtype(subtype: str) -> str:
    """The subtype to write so that not one bit of the source is lost."""
    if subtype in _FLAC_SUBTYPES:
        return subtype
    raise ValueError(f"cannot re-encode subtype {subtype!r} to FLAC without loss")


def reencode_flac(
    input_path: Path, output_path: Path, compression_level: int | None = None
) -> bool:
    """Re-encodes a FLAC file using soundfile, keeping its bit depth.

    This function reads the FLAC file, then rewrites it, which forces
    recalculation of the FLAC container metadata (especially duration).

    The samples are read as 32-bit integers and written back at the SOURCE'S
    subtype, so a 24-bit file comes out 24-bit. Until v2.0 this function read
    float32 and wrote PCM_16 for "compression levels" 0-5 — the default being
    5 — so every 24-bit file it repaired lost its low 8 bits. The compression
    level is now what its name says: flac's 0-8 (8 = smallest file), handed to
    libFLAC, and it never changes a sample.

    Args:
        input_path: Source file.
        output_path: Destination file.
        compression_level: 0-8 (8 = best compression). If None, uses config.

    Returns:
        True if successful, False otherwise.
    """
    if compression_level is None:
        compression_level = repair_config.FLAC_COMPRESSION_LEVEL
    level = min(max(int(compression_level), 0), _MAX_FLAC_LEVEL)

    try:
        logger.debug(f"  Reading FLAC file: {input_path.name}")
        info = sf.info(str(input_path))
        subtype = _target_subtype(str(info.subtype))

        # int32 is exact for every PCM subtype a FLAC can hold.
        data, samplerate = sf.read(str(input_path), dtype="int32")

        logger.debug(f"  Re-encoding to FLAC ({subtype}, level {level})...")
        sf.write(
            str(output_path),
            data,
            samplerate,
            format="FLAC",
            subtype=subtype,
            compression_level=level / _MAX_FLAC_LEVEL,
        )

        logger.debug(f"  ✓ File re-encoded: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Re-encoding error: {e}")
        if output_path.exists():
            output_path.unlink()
        return False
