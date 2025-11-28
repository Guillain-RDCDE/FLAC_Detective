"""Gestion des métadonnées FLAC pour la réparation."""

import logging
from pathlib import Path

from typing import cast

from mutagen.flac import FLAC, Picture, VCFLACDict

logger = logging.getLogger(__name__)


def extract_all_metadata(filepath: Path) -> dict:
    """Extrait TOUTES les métadonnées du fichier FLAC.

    Args:
        filepath: Chemin vers le fichier FLAC.

    Returns:
        Dict avec tous les tags, pictures, vendor, etc.
    """
    try:
        audio = FLAC(filepath)

        # Extraction de tous les tags Vorbis Comment
        tags = {}
        if audio.tags:
            # On sait que pour du FLAC, tags est un VCFLACDict
            flac_tags = cast(VCFLACDict, audio.tags)
            for key, value in flac_tags.items():
                # Stocker en tant que liste (Vorbis Comments peuvent avoir plusieurs valeurs)
                tags[key] = list(value)

        # Extraction de toutes les images (artwork)
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
                    "data": pic.data,  # Données binaires de l'image
                }
            )

        # Informations vendor
        vendor = "reference libFLAC"
        if audio.tags and hasattr(audio.tags, "vendor"):
            vendor = audio.tags.vendor

        return {"tags": tags, "pictures": pictures, "vendor": vendor, "success": True}

    except Exception as e:
        logger.error(f"Erreur extraction métadonnées {filepath.name}: {e}")
        return {"success": False, "error": str(e)}


def restore_all_metadata(filepath: Path, metadata: dict) -> bool:
    """Restaure TOUTES les métadonnées dans le fichier FLAC.

    Args:
        filepath: Fichier FLAC cible.
        metadata: Dict retourné par extract_all_metadata().

    Returns:
        True si succès, False sinon.
    """
    try:
        audio = FLAC(filepath)

        # Supprimer tous les tags existants
        audio.delete()

        # Restaurer le vendor
        if "vendor" in metadata and audio.tags:
            flac_tags = cast(VCFLACDict, audio.tags)
            flac_tags.vendor = metadata["vendor"]

        # Restaurer tous les tags
        for key, values in metadata.get("tags", {}).items():
            audio[key] = values

        # Restaurer toutes les images
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

        # Sauvegarder
        audio.save()

        return True

    except Exception as e:
        logger.error(f"Erreur restauration métadonnées: {e}")
        return False
