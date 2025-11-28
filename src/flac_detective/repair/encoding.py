"""Ré-encodage de fichiers FLAC."""

import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from ..config import repair_config

logger = logging.getLogger(__name__)


def reencode_flac(
    input_path: Path, output_path: Path, compression_level: int | None = None
) -> bool:
    """Ré-encode un fichier FLAC en utilisant soundfile.

    Cette fonction lit le fichier FLAC, puis le réécrit, ce qui force
    la recalculation des métadonnées du conteneur FLAC (notamment la durée).

    Args:
        input_path: Fichier source.
        output_path: Fichier destination.
        compression_level: 0-8 (8 = meilleure compression). Si None, utilise la config.
            Note: soundfile utilise libFLAC qui a ses propres niveaux de compression.

    Returns:
        True si succès, False sinon.
    """
    if compression_level is None:
        compression_level = repair_config.FLAC_COMPRESSION_LEVEL

    try:
        logger.debug(f"  Lecture du fichier FLAC: {input_path.name}")

        # Lecture du fichier audio complet
        data, samplerate = sf.read(input_path, dtype='float32')

        logger.debug(f"  Ré-encodage en FLAC (niveau {compression_level})...")

        # Mapping des niveaux de compression (0-8) vers les niveaux soundfile
        # soundfile/libFLAC utilise des niveaux de 0 à 8
        # On peut passer le niveau directement via les options de sous-type
        subtype_map = {
            0: 'PCM_16',  # Pas de compression (rapide)
            1: 'PCM_16',
            2: 'PCM_16',
            3: 'PCM_16',
            4: 'PCM_16',
            5: 'PCM_16',  # Défaut
            6: 'PCM_24',  # Meilleure qualité
            7: 'PCM_24',
            8: 'PCM_24',  # Meilleure compression
        }

        # Écriture du nouveau fichier FLAC
        # soundfile recalcule automatiquement toutes les métadonnées du conteneur
        sf.write(
            output_path,
            data,
            samplerate,
            format='FLAC',
            subtype=subtype_map.get(compression_level, 'PCM_16')
        )

        logger.debug(f"  ✓ Fichier ré-encodé: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Erreur ré-encodage: {e}")
        if output_path.exists():
            output_path.unlink()
        return False
