"""Analyseur principal de fichiers FLAC."""

import logging
from pathlib import Path
from typing import Dict

from .metadata import check_duration_consistency, read_metadata
from .scoring import calculate_score
from .spectrum import analyze_spectrum

logger = logging.getLogger(__name__)


class FLACAnalyzer:
    """Analyseur de fichiers FLAC pour détecter les transcodages MP3."""

    def __init__(self, sample_duration: float = 30.0):
        """Initialise l'analyseur.

        Args:
            sample_duration: Durée en secondes à analyser (30s par défaut).
        """
        self.sample_duration = sample_duration

    def analyze_file(self, filepath: Path) -> Dict:
        """Analyse un fichier FLAC et détermine s'il est authentique.

        Args:
            filepath: Chemin vers le fichier FLAC à analyser.

        Returns:
            Dict avec: filepath, filename, score, reason, cutoff_freq, metadata, duration_mismatch.
        """
        try:
            # Lecture des métadonnées
            metadata = read_metadata(filepath)

            # Vérification de cohérence durée (critère FTF)
            duration_check = check_duration_consistency(filepath, metadata)

            # Analyse spectrale
            cutoff_freq, energy_ratio = analyze_spectrum(filepath, self.sample_duration)

            # Calcul du score et raison
            score, reason = calculate_score(cutoff_freq, energy_ratio, metadata, duration_check)

            return {
                "filepath": str(filepath),
                "filename": filepath.name,
                "score": score,
                "reason": reason,
                "cutoff_freq": cutoff_freq,
                "sample_rate": metadata.get("sample_rate", "N/A"),
                "bit_depth": metadata.get("bit_depth", "N/A"),
                "encoder": metadata.get("encoder", "N/A"),
                "duration_mismatch": duration_check["mismatch"],
                "duration_metadata": duration_check["metadata_duration"],
                "duration_real": duration_check["real_duration"],
                "duration_diff": duration_check["diff_samples"],
            }

        except Exception as e:
            logger.error(f"Erreur analyse {filepath.name}: {e}")
            return {
                "filepath": str(filepath),
                "filename": filepath.name,
                "score": 0,
                "reason": f"Erreur: {str(e)}",
                "cutoff_freq": 0,
                "sample_rate": "N/A",
                "bit_depth": "N/A",
                "encoder": "N/A",
                "duration_mismatch": "Erreur",
                "duration_metadata": "N/A",
                "duration_real": "N/A",
                "duration_diff": "N/A",
            }
