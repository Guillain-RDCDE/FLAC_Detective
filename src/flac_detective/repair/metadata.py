"""FLAC metadata management for repair."""

import logging
from pathlib import Path

from typing import cast

from mutagen.flac import FLAC, Picture, VCFLACDict

logger = logging.getLogger(__name__)


def extract_all_metadata(filepath: Path) -> dict:
    """Extracts ALL metadata from FLAC file.

    Args:
        filepath: Path to FLAC file.

    Returns:
        Dict with all tags, pictures, vendor, etc.
    """
    try:
        audio = FLAC(filepath)

        # Extract all Vorbis Comment tags
        tags = {}
        if audio.tags:
            # We know that for FLAC, tags is a VCFLACDict
            flac_tags = cast(VCFLACDict, audio.tags)
            for key, value in flac_tags.items():
                # Store as list (Vorbis Comments can have multiple values)
                tags[key] = list(value)

        # Extract all images (artwork)
        pictures = []
        for pic in audio.pictures:
            pictures.append(
                {
                    "type": pic.type,
                    "mime": pic.mime,
                    "desc": pic.desc,
                    "width": pic.width,
                    "height": pic.height,
                    "depth": pic.depth,
                    "colors": pic.colors,
                    "data": pic.data,  # Binary image data
                }
            )

        # Vendor info
        vendor = "reference libFLAC"
        if audio.tags and hasattr(audio.tags, "vendor"):
            vendor = audio.tags.vendor

        return {"tags": tags, "pictures": pictures, "vendor": vendor, "success": True}

    except Exception as e:
        logger.error(f"Metadata extraction error {filepath.name}: {e}")
        return {"success": False, "error": str(e)}


def restore_all_metadata(filepath: Path, metadata: dict) -> bool:
    """Restores ALL metadata into FLAC file.

    Args:
        filepath: Target FLAC file.
        metadata: Dict returned by extract_all_metadata().

    Returns:
        True if success, False otherwise.
    """
    try:
        audio = FLAC(filepath)

        # Delete all existing tags
        audio.delete()

        # Restore vendor
        if "vendor" in metadata and audio.tags:
            flac_tags = cast(VCFLACDict, audio.tags)
            flac_tags.vendor = metadata["vendor"]

        # Restore all tags
        for key, values in metadata.get("tags", {}).items():
            audio[key] = values

        # Restore all images
        audio.clear_pictures()
        for pic_data in metadata.get("pictures", []):
            pic = Picture()
            pic.type = pic_data["type"]
            pic.mime = pic_data["mime"]
            pic.desc = pic_data["desc"]
            pic.width = pic_data["width"]
            pic.height = pic_data["height"]
            pic.depth = pic_data["depth"]
            pic.colors = pic_data["colors"]
            pic.data = pic_data["data"]
            audio.add_picture(pic)

        # Save
        audio.save()

        return True

    except Exception as e:
        logger.error(f"Metadata restoration error: {e}")
        return False
