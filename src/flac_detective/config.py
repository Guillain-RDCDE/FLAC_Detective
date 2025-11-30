"""Configuration centralisée de FLAC Detective."""

from dataclasses import dataclass


@dataclass
class AnalysisConfig:
    """Configuration pour l'analyse spectrale."""

    # Durée d'échantillon à analyser (secondes)
    SAMPLE_DURATION: float = 30.0

    # Nombre de workers pour le multi-threading
    MAX_WORKERS: int = 4

    # Intervalle de sauvegarde automatique (nombre de fichiers)
    SAVE_INTERVAL: int = 50


@dataclass
class ScoringConfig:
    """Configuration pour le système de scoring."""

    # Seuils de score
    AUTHENTIC_THRESHOLD: int = 90  # >= 90% = Authentique
    PROBABLY_AUTHENTIC_THRESHOLD: int = 70  # >= 70% = Probablement authentique
    SUSPECT_THRESHOLD: int = 50  # >= 50% = Suspect
    # < 50% = Fake

    # Pénalités
    PENALTY_LOW_ENERGY: int = 30
    PENALTY_DURATION_MISMATCH: int = 20
    PENALTY_SUSPICIOUS_METADATA: int = 10


@dataclass
class SpectralConfig:
    """Configuration pour l'analyse spectrale."""

    # Zone de référence pour le calcul d'énergie (Hz)
    REFERENCE_FREQ_LOW: int = 10000
    REFERENCE_FREQ_HIGH: int = 14000

    # Début du scan de coupure (Hz)
    CUTOFF_SCAN_START: int = 14000

    # Taille des tranches d'analyse (Hz)
    TRANCHE_SIZE: int = 250

    # Seuil de coupure (dB sous la référence)
    CUTOFF_THRESHOLD_DB: int = 30

    # Nombre de tranches consécutives faibles pour confirmer une coupure
    CONSECUTIVE_LOW_THRESHOLD: int = 2

    # Fréquence minimale pour l'énergie haute fréquence (Hz)
    HIGH_FREQ_THRESHOLD: int = 16000


@dataclass
class RepairConfig:
    """Configuration pour le module de réparation."""

    # Niveau de compression FLAC (0-8, 8 = meilleur)
    FLAC_COMPRESSION_LEVEL: int = 5

    # Créer un backup automatiquement
    BACKUP_ENABLED: bool = True

    # Tolérance pour la différence de durée (samples)
    DURATION_TOLERANCE_SAMPLES: int = 588  # ~1 frame MP3 à 44.1kHz

    # Timeout pour les opérations de ré-encodage (secondes)
    REENCODE_TIMEOUT: int = 300


# Instances globales (singleton pattern)
analysis_config = AnalysisConfig()
scoring_config = ScoringConfig()
spectral_config = SpectralConfig()
repair_config = RepairConfig()
