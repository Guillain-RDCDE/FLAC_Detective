"""Analyse de qualité audio (clipping, DC offset, corruption)."""

import logging
from pathlib import Path
from typing import Dict, Any

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def detect_clipping(data: np.ndarray, threshold: float = 0.99) -> Dict[str, Any]:
    """Détecte la saturation audio (clipping).

    Le clipping se produit quand l'amplitude atteint les limites numériques
    (±1.0 pour les floats), causant une distorsion audible.

    Args:
        data: Données audio (mono ou stéréo).
        threshold: Seuil de détection (0.99 = 99% de la plage maximale).

    Returns:
        Dictionnaire avec les résultats de détection:
        - has_clipping: True si clipping détecté
        - clipping_percentage: Pourcentage d'échantillons clippés
        - clipped_samples: Nombre d'échantillons clippés
        - severity: 'none', 'light', 'moderate', 'severe'
    """
    # Convertir en 1D si stéréo
    if data.ndim > 1:
        data = data.flatten()

    # Compter les échantillons qui touchent le seuil
    clipped_samples = int(np.sum(np.abs(data) >= threshold))
    total_samples = data.size
    clipping_percentage = (clipped_samples / total_samples) * 100

    # Déterminer la sévérité
    if clipping_percentage == 0:
        severity = "none"
    elif clipping_percentage < 0.01:
        severity = "light"  # < 0.01% = quelques pics
    elif clipping_percentage < 0.1:
        severity = "moderate"  # 0.01-0.1% = problème notable
    else:
        severity = "severe"  # > 0.1% = très problématique

    return {
        "has_clipping": clipping_percentage > 0.01,  # Seuil: >0.01%
        "clipping_percentage": round(clipping_percentage, 4),
        "clipped_samples": clipped_samples,
        "severity": severity,
    }


def detect_dc_offset(data: np.ndarray, threshold: float = 0.001) -> Dict[str, Any]:
    """Détecte un décalage DC (offset de la forme d'onde).

    Un DC offset signifie que la forme d'onde n'est pas centrée sur zéro,
    ce qui réduit la plage dynamique et peut causer du clipping.

    Args:
        data: Données audio (mono ou stéréo).
        threshold: Seuil de détection (valeur absolue).

    Returns:
        Dictionnaire avec les résultats de détection:
        - has_dc_offset: True si offset détecté
        - dc_offset_value: Valeur moyenne du signal
        - severity: 'none', 'light', 'moderate', 'severe'
    """
    # Calculer la moyenne par canal
    if data.ndim > 1:
        # Stéréo: calculer l'offset moyen des deux canaux
        dc_offset = float(np.mean([np.mean(data[:, i]) for i in range(data.shape[1])]))
    else:
        # Mono
        dc_offset = float(np.mean(data))

    abs_offset = abs(dc_offset)

    # Déterminer la sévérité
    if abs_offset < threshold:
        severity = "none"
    elif abs_offset < 0.01:
        severity = "light"  # < 1%
    elif abs_offset < 0.05:
        severity = "moderate"  # 1-5%
    else:
        severity = "severe"  # > 5%

    return {
        "has_dc_offset": abs_offset >= threshold,
        "dc_offset_value": round(dc_offset, 6),
        "severity": severity,
    }


def detect_corruption(filepath: Path) -> Dict[str, Any]:
    """Vérifie si le fichier audio est lisible jusqu'à la fin.

    Tente de lire l'intégralité du fichier pour détecter les corruptions
    qui empêcheraient la lecture complète.

    Args:
        filepath: Chemin vers le fichier audio.

    Returns:
        Dictionnaire avec les résultats de détection:
        - is_corrupted: True si corruption détectée
        - readable: True si le fichier peut être lu
        - error: Message d'erreur si applicable
        - frames_read: Nombre de frames lues (si succès)
    """
    try:
        # Essayer de lire tout le fichier
        data, samplerate = sf.read(filepath, dtype='float32')

        # Vérifier que des données ont été lues
        if data.size == 0:
            return {
                "is_corrupted": True,
                "readable": False,
                "error": "No data read from file",
                "frames_read": 0,
            }

        # Vérifier qu'il n'y a pas de NaN ou Inf
        if np.any(np.isnan(data)) or np.any(np.isinf(data)):
            return {
                "is_corrupted": True,
                "readable": True,
                "error": "File contains NaN or Inf values",
                "frames_read": len(data),
            }

        return {
            "is_corrupted": False,
            "readable": True,
            "error": None,
            "frames_read": len(data),
        }

    except Exception as e:
        logger.debug(f"Corruption detected in {filepath.name}: {e}")
        return {
            "is_corrupted": True,
            "readable": False,
            "error": str(e),
            "frames_read": 0,
        }


def analyze_audio_quality(filepath: Path) -> Dict[str, Any]:
    """Analyse complète de la qualité audio d'un fichier.

    Combine toutes les détections de qualité en une seule analyse.

    Args:
        filepath: Chemin vers le fichier audio.

    Returns:
        Dictionnaire avec tous les résultats d'analyse de qualité.
    """
    results = {}

    # 1. Vérifier la corruption d'abord
    corruption_result = detect_corruption(filepath)
    results["corruption"] = corruption_result

    # Si le fichier est corrompu, on ne peut pas faire les autres analyses
    if corruption_result["is_corrupted"]:
        results["clipping"] = {
            "has_clipping": False,
            "clipping_percentage": 0.0,
            "clipped_samples": 0,
            "severity": "unknown",
        }
        results["dc_offset"] = {
            "has_dc_offset": False,
            "dc_offset_value": 0.0,
            "severity": "unknown",
        }
        return results

    # 2. Lire le fichier pour les analyses suivantes
    try:
        data, _ = sf.read(filepath, dtype='float32')

        # 3. Détection de clipping
        results["clipping"] = detect_clipping(data)

        # 4. Détection de DC offset
        results["dc_offset"] = detect_dc_offset(data)

    except Exception as e:
        logger.error(f"Error analyzing quality for {filepath.name}: {e}")
        results["clipping"] = {
            "has_clipping": False,
            "clipping_percentage": 0.0,
            "clipped_samples": 0,
            "severity": "error",
        }
        results["dc_offset"] = {
            "has_dc_offset": False,
            "dc_offset_value": 0.0,
            "severity": "error",
        }

    return results
