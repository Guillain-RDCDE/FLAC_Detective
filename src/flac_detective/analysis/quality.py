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


def detect_silence(data: np.ndarray, samplerate: int, threshold_db: float = -60.0) -> Dict[str, Any]:
    """Détecte le silence anormal (début/fin).

    Args:
        data: Données audio.
        samplerate: Fréquence d'échantillonnage.
        threshold_db: Seuil de silence en dB (défaut -60dB).

    Returns:
        Dictionnaire avec les résultats.
    """
    if data.ndim > 1:
        data = np.mean(np.abs(data), axis=1)
    else:
        data = np.abs(data)

    threshold = 10 ** (threshold_db / 20)
    
    # Trouver les indices où le signal dépasse le seuil
    non_silent = np.where(data > threshold)[0]
    
    if len(non_silent) == 0:
        return {
            "has_silence_issue": True,
            "leading_silence_sec": len(data) / samplerate,
            "trailing_silence_sec": 0.0,
            "issue_type": "full_silence"
        }

    start_idx = non_silent[0]
    end_idx = non_silent[-1]
    
    leading_silence = start_idx / samplerate
    trailing_silence = (len(data) - 1 - end_idx) / samplerate
    
    # Critères de détection (silence > 2 secondes)
    has_issue = bool(leading_silence > 2.0 or trailing_silence > 2.0)
    
    issue_type = "none"
    if leading_silence > 2.0 and trailing_silence > 2.0:
        issue_type = "both"
    elif leading_silence > 2.0:
        issue_type = "leading"
    elif trailing_silence > 2.0:
        issue_type = "trailing"

    return {
        "has_silence_issue": has_issue,
        "leading_silence_sec": round(float(leading_silence), 2),
        "trailing_silence_sec": round(float(trailing_silence), 2),
        "issue_type": issue_type
    }


def detect_true_bit_depth(data: np.ndarray, reported_depth: int) -> Dict[str, Any]:
    """Vérifie la profondeur de bits réelle.

    Détecte si un fichier 24-bit est en réalité du 16-bit (padding).

    Args:
        data: Données audio (float32).
        reported_depth: Profondeur de bits rapportée par les métadonnées.

    Returns:
        Dictionnaire avec les résultats.
    """
    if reported_depth <= 16:
        return {"is_fake_high_res": False, "estimated_depth": reported_depth}

    # Pour un fichier 24-bit, on vérifie si les valeurs correspondent à du 16-bit
    # En 16-bit, les valeurs sont des multiples de 1/32768
    # On vérifie si data * 32768 est proche d'un entier
    
    # On prend un échantillon pour aller plus vite
    sample = data[:10000] if data.ndim == 1 else data[:10000, 0]
    
    # Multiplier par 2^15 (32768)
    scaled = sample * 32768.0
    residuals = np.abs(scaled - np.round(scaled))
    
    # Si les résidus sont très faibles, c'est probablement du 16-bit
    is_16bit = bool(np.all(residuals < 1e-4))
    
    return {
        "is_fake_high_res": is_16bit,
        "estimated_depth": 16 if is_16bit else 24,
        "details": "24-bit file contains only 16-bit data" if is_16bit else "True 24-bit"
    }


def detect_upsampling(cutoff_freq: float, samplerate: int) -> Dict[str, Any]:
    """Détecte l'upsampling de fréquence d'échantillonnage.

    Exemple: 96kHz avec cutoff à 22kHz (typique du 44.1kHz).

    Args:
        cutoff_freq: Fréquence de coupure détectée (Hz).
        samplerate: Fréquence d'échantillonnage du fichier (Hz).

    Returns:
        Dictionnaire avec les résultats.
    """
    if samplerate <= 48000:
        return {"is_upsampled": False, "suspected_original_rate": samplerate}

    # Nyquist théorique
    nyquist = samplerate / 2
    
    # Si on a du 96kHz (Nyquist 48k) mais que ça coupe à 22k -> Upsample de 44.1k
    # Si ça coupe à 24k -> Upsample de 48k
    
    is_upsampled = False
    suspected_rate = samplerate

    if cutoff_freq < 24000:
        # Coupure typique CD (22.05k) ou DAT (24k)
        is_upsampled = True
        if cutoff_freq < 22500:
            suspected_rate = 44100
        else:
            suspected_rate = 48000
            
    return {
        "is_upsampled": is_upsampled,
        "suspected_original_rate": suspected_rate,
        "cutoff_freq": cutoff_freq
    }


def analyze_audio_quality(filepath: Path, metadata: Dict = None, cutoff_freq: float = 0.0) -> Dict[str, Any]:
    """Analyse complète de la qualité audio d'un fichier.

    Combine toutes les détections de qualité en une seule analyse.

    Args:
        filepath: Chemin vers le fichier audio.
        metadata: Métadonnées du fichier (optionnel, pour bit depth/samplerate).
        cutoff_freq: Fréquence de coupure (optionnel, pour upsampling).

    Returns:
        Dictionnaire avec tous les résultats d'analyse de qualité.
    """
    results = {}

    # 1. Vérifier la corruption d'abord
    corruption_result = detect_corruption(filepath)
    results["corruption"] = corruption_result

    # Si le fichier est corrompu, on ne peut pas faire les autres analyses
    if corruption_result["is_corrupted"]:
        return _get_empty_results(results, error_mode=False)

    # 2. Lire le fichier pour les analyses suivantes
    try:
        data, samplerate = sf.read(filepath, dtype='float32')

        # 3. Détection de clipping
        results["clipping"] = detect_clipping(data)

        # 4. Détection de DC offset
        results["dc_offset"] = detect_dc_offset(data)
        
        # 5. Détection de silence (Phase 2)
        results["silence"] = detect_silence(data, samplerate)
        
        # 6. Détection de faux High-Res (Phase 2)
        reported_depth = 16
        if metadata and "bit_depth" in metadata:
            try:
                reported_depth = int(metadata["bit_depth"])
            except (ValueError, TypeError):
                pass
        results["bit_depth"] = detect_true_bit_depth(data, reported_depth)
        
        # 7. Détection d'upsampling (Phase 2)
        reported_rate = samplerate
        if metadata and "sample_rate" in metadata:
            try:
                reported_rate = int(metadata["sample_rate"])
            except (ValueError, TypeError):
                pass
        results["upsampling"] = detect_upsampling(cutoff_freq, reported_rate)

    except Exception as e:
        logger.error(f"Error analyzing quality for {filepath.name}: {e}")
        return _get_empty_results(results, error_mode=True, error_msg=str(e))

    return results


def _get_empty_results(results: Dict, error_mode: bool = False, error_msg: str = "") -> Dict:
    """Génère des résultats vides ou d'erreur."""
    severity = "error" if error_mode else "unknown"
    
    defaults = {
        "clipping": {"has_clipping": False, "clipping_percentage": 0.0, "severity": severity},
        "dc_offset": {"has_dc_offset": False, "dc_offset_value": 0.0, "severity": severity},
        "silence": {"has_silence_issue": False, "issue_type": severity},
        "bit_depth": {"is_fake_high_res": False, "estimated_depth": 0},
        "upsampling": {"is_upsampled": False, "suspected_original_rate": 0}
    }
    
    for key, value in defaults.items():
        if key not in results:
            results[key] = value
            
    if error_mode and "corruption" not in results:
        results["corruption"] = {"is_corrupted": True, "error": error_msg}
        
    return results
