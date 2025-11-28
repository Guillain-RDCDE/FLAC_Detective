"""Gestion des métadonnées FLAC."""

import logging
from pathlib import Path
from typing import Dict

import soundfile as sf
from mutagen.flac import FLAC

logger = logging.getLogger(__name__)


def read_metadata(filepath: Path) -> Dict:
    """Lit les métadonnées du fichier FLAC.

    Args:
        filepath: Chemin vers le fichier FLAC.

    Returns:
        Dictionnaire contenant les métadonnées (sample_rate, bit_depth, etc.).
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
        logger.debug(f"Erreur lecture métadonnées: {e}")
        return {}


def check_duration_consistency(filepath: Path, metadata: Dict) -> Dict:
    """Vérifie la cohérence entre durée déclarée et durée réelle.

    Critère utilisé par Fakin' The Funk: les durées doivent correspondre.
    Une divergence peut indiquer un fichier corrompu ou un transcodage raté.

    Args:
        filepath: Chemin vers le fichier FLAC.
        metadata: Métadonnées du fichier.

    Returns:
        Dict avec: mismatch, metadata_duration, real_duration, diff_samples, diff_ms.
    """
    try:
        # Durée depuis métadonnées FLAC
        metadata_duration = metadata.get("duration", 0)

        # Durée réelle en lisant le fichier audio
        info = sf.info(filepath)
        real_duration = info.duration

        # Différence en samples (plus précis que les secondes)
        sample_rate = metadata.get("sample_rate", info.samplerate)
        metadata_samples = int(metadata_duration * sample_rate)
        real_samples = int(real_duration * sample_rate)
        diff_samples = abs(metadata_samples - real_samples)

        # Tolérance : 1 frame (588 samples pour 44.1kHz, ~13ms)
        tolerance_samples = 588

        # Calcul du décalage en millisecondes
        diff_ms = (diff_samples / sample_rate) * 1000

        mismatch = diff_samples > tolerance_samples

        if mismatch:
            mismatch_str = f"⚠️ Décalage: {diff_samples:,} samples ({diff_ms:.1f}ms)"
        else:
            mismatch_str = "✓ Durées cohérentes"

        return {
            "mismatch": mismatch_str if mismatch else None,
            "metadata_duration": f"{metadata_duration:.3f}s",
            "real_duration": f"{real_duration:.3f}s",
            "diff_samples": diff_samples,
            "diff_ms": diff_ms,
        }

    except Exception as e:
        logger.debug(f"Erreur vérification durée: {e}")
        return {
            "mismatch": None,
            "metadata_duration": "N/A",
            "real_duration": "N/A",
            "diff_samples": 0,
            "diff_ms": 0,
        }
