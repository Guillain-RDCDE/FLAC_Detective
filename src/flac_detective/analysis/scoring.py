"""Calcul de score de qualité pour fichiers FLAC."""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Seuils de fréquence pour classification (en Hz)
THRESHOLDS = {
    "authentic": 20000,  # FLAC authentique: > 20 kHz
    "mp3_320": 20500,  # MP3 320 kbps: ~20-20.5 kHz
    "mp3_256": 19000,  # MP3 256 kbps: ~19-20 kHz
    "mp3_192": 18000,  # MP3 192 kbps: ~18-19 kHz
    "mp3_128": 16000,  # MP3 128 kbps: ~16-17 kHz
}


def calculate_score(
    cutoff_freq: float, energy_ratio: float, metadata: Dict, duration_check: Dict
) -> Tuple[int, str]:
    """Calcule un score de confiance (0-100) et génère une raison.

    Score:
    - 90-100: Très probablement authentique
    - 70-89: Probablement authentique
    - 50-69: Suspect
    - 0-49: Très probablement transcodé

    Args:
        cutoff_freq: Fréquence de coupure détectée en Hz.
        energy_ratio: Ratio d'énergie dans les hautes fréquences.
        metadata: Métadonnées du fichier.
        duration_check: Résultat de la vérification de durée.

    Returns:
        Tuple (score, raison) où score est entre 0 et 100.
    """
    reasons = []
    score = 100

    # Analyse de la fréquence de coupure (critère PRINCIPAL)
    cutoff_is_full_spectrum = cutoff_freq >= 21000

    if cutoff_freq >= 21000:
        reasons.append(f"Spectre complet jusqu'à {cutoff_freq:.0f} Hz (excellent)")
    elif cutoff_freq >= THRESHOLDS["authentic"]:
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (authentique)")
    elif cutoff_freq >= 19500:
        score -= 15
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (légèrement suspect)")
    elif cutoff_freq >= THRESHOLDS["mp3_256"]:
        score -= 35
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (typique MP3 256-320k)")
    elif cutoff_freq >= THRESHOLDS["mp3_192"]:
        score -= 55
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (typique MP3 192k)")
    elif cutoff_freq >= THRESHOLDS["mp3_128"]:
        score -= 75
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (typique MP3 128k)")
    else:
        score -= 90
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (très suspect)")

    # Analyse du ratio d'énergie haute fréquence (critère SECONDAIRE)
    score = _analyze_energy_ratio(score, energy_ratio, cutoff_is_full_spectrum, reasons)

    # Vérification de cohérence durée (critère FTF)
    score = _check_duration_mismatch(score, duration_check, reasons)

    # Analyse des métadonnées suspectes
    score = _check_suspicious_metadata(score, metadata, reasons)

    # Calcul du score final
    final_score = max(0, min(100, score))
    reason = " | ".join(reasons) if reasons else "Analyse normale"

    return final_score, reason


def _analyze_energy_ratio(
    score: int, energy_ratio: float, cutoff_is_full_spectrum: bool, reasons: list
) -> int:
    """Analyse le ratio d'énergie haute fréquence.

    Args:
        score: Score actuel.
        energy_ratio: Ratio d'énergie dans les hautes fréquences.
        cutoff_is_full_spectrum: True si le spectre est complet (≥21kHz).
        reasons: Liste des raisons (modifiée in-place).

    Returns:
        Score mis à jour.
    """
    if cutoff_is_full_spectrum:
        # Spectre complet : énergie faible = mastering volontaire ou style musical
        if energy_ratio < 0.00001:
            reasons.append("Contenu ultra-aigu minimal (mastering ou style musical)")
            score -= 5
    else:
        # Spectre incomplet : énergie faible = SUSPECT
        if energy_ratio < 0.0001:
            score -= 25
            reasons.append("Absence d'énergie >16kHz (renforce suspicion)")
        elif energy_ratio < 0.001:
            score -= 15
            reasons.append("Très peu d'énergie >16kHz")
        elif energy_ratio < 0.005:
            score -= 5
            reasons.append("Énergie faible >16kHz")

    return score


def _check_duration_mismatch(score: int, duration_check: Dict, reasons: list) -> int:
    """Vérifie la cohérence de durée.

    Args:
        score: Score actuel.
        duration_check: Résultat de la vérification de durée.
        reasons: Liste des raisons (modifiée in-place).

    Returns:
        Score mis à jour.
    """
    if duration_check.get("mismatch"):
        diff_ms = duration_check.get("diff_ms", 0)
        if diff_ms > 1000:  # > 1 seconde
            score -= 20
            reasons.append(f"Durée incohérente ({diff_ms:.0f}ms de décalage)")
        elif diff_ms > 100:  # > 100ms
            score -= 10
            reasons.append(f"Léger décalage durée ({diff_ms:.0f}ms)")

    return score


def _check_suspicious_metadata(score: int, metadata: Dict, reasons: list) -> int:
    """Vérifie les métadonnées suspectes.

    Args:
        score: Score actuel.
        metadata: Métadonnées du fichier.
        reasons: Liste des raisons (modifiée in-place).

    Returns:
        Score mis à jour.
    """
    # Analyse de l'encodeur
    encoder = metadata.get("encoder", "").lower()
    if "lame" in encoder or "mp3" in encoder:
        score -= 30
        reasons.append(f"Encodeur suspect: {metadata.get('encoder', 'N/A')}")

    # Vérification bit depth
    bit_depth = metadata.get("bit_depth")
    if bit_depth and bit_depth < 16:
        score -= 20
        reasons.append(f"Bit depth suspect: {bit_depth} bits")

    return score
