"""Analyse spectrale de fichiers audio."""

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.fft import rfft, rfftfreq

from ..config import spectral_config

logger = logging.getLogger(__name__)


def analyze_spectrum(filepath: Path, sample_duration: float = 30.0) -> Tuple[float, float]:
    """Analyse le spectre de fréquences du fichier audio.

    Prend plusieurs échantillons à différents moments pour plus de robustesse.

    Args:
        filepath: Chemin vers le fichier audio.
        sample_duration: Durée en secondes à analyser.

    Returns:
        Tuple (cutoff_frequency, energy_ratio) où:
        - cutoff_frequency: fréquence de coupure détectée en Hz
        - energy_ratio: ratio d'énergie dans les hautes fréquences
    """
    try:
        # Lecture du fichier entier pour connaître sa durée
        info = sf.info(filepath)
        total_duration = info.duration
        samplerate = info.samplerate

        # Prendre 3 échantillons : début, milieu, fin (ou juste 1 si trop court)
        num_samples = 3 if total_duration > 90 else 1
        sample_duration = min(sample_duration, total_duration / num_samples)

        cutoff_freqs = []
        energy_ratios = []

        for i in range(num_samples):
            # Position de départ de cet échantillon
            start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
            start_time = max(0, start_time)
            start_frame = int(start_time * samplerate)

            # Lecture de l'échantillon
            data, _ = sf.read(
                filepath,
                start=start_frame,
                frames=int(sample_duration * samplerate),
                always_2d=True,
            )

            # Conversion en mono si stéréo
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            else:
                data = data[:, 0]

            # Application d'une fenêtre de Hann pour réduire les fuites spectrales
            window = signal.windows.hann(len(data))
            data_windowed = data * window

            # Calcul de la FFT
            fft_vals = rfft(data_windowed)
            fft_freq = rfftfreq(len(data_windowed), 1 / samplerate)

            # Magnitude spectrale (en dB)
            magnitude = np.abs(fft_vals)
            magnitude_db = 20 * np.log10(magnitude + 1e-10)

            # Détection de la fréquence de coupure
            cutoff_freq = detect_cutoff(fft_freq, magnitude_db)
            cutoff_freqs.append(cutoff_freq)

            # Calcul du ratio d'énergie haute fréquence (> 16 kHz)
            energy_ratio = calculate_high_frequency_energy(fft_freq, magnitude)
            energy_ratios.append(energy_ratio)

        # Prendre la MEILLEURE valeur (max) pour être moins strict
        final_cutoff = max(cutoff_freqs)
        final_energy = max(energy_ratios)

        return final_cutoff, final_energy

    except Exception as e:
        logger.debug(f"Erreur analyse spectrale: {e}")
        return 0, 0


def detect_cutoff(frequencies: np.ndarray, magnitude_db: np.ndarray) -> float:
    """Détecte la fréquence de coupure avec une méthode robuste.

    Méthode basée sur les percentiles:
    1. Calcule l'énergie de référence dans une zone sûre (10-14 kHz)
    2. Analyse le spectre par tranches de 500 Hz à partir de 14 kHz
    3. Détecte une vraie coupure = plusieurs tranches consécutives sous le seuil

    Args:
        frequencies: Array des fréquences.
        magnitude_db: Array des magnitudes en dB.

    Returns:
        Fréquence de coupure détectée en Hz.
    """
    # Focus sur les fréquences > REFERENCE_FREQ_LOW
    high_freq_mask = frequencies > spectral_config.REFERENCE_FREQ_LOW
    if not np.any(high_freq_mask):
        return float(frequencies[-1])

    freq_high = frequencies[high_freq_mask]
    mag_high = magnitude_db[high_freq_mask]

    # Lissage agressif pour ignorer les variations temporelles
    if len(mag_high) > 100:
        from scipy.ndimage import uniform_filter1d

        mag_smooth = uniform_filter1d(mag_high, size=100)
    else:
        mag_smooth = mag_high

    # Analyse par tranches
    tranche_size_hz = spectral_config.TRANCHE_SIZE
    freq_max = freq_high[-1]

    # Calcul de la référence (énergie médiane entre REFERENCE_FREQ_LOW-REFERENCE_FREQ_HIGH)
    # Cette zone est sûre même pour un MP3 128kbps (qui coupe à 16k)
    ref_mask = (freq_high >= spectral_config.REFERENCE_FREQ_LOW) & (
        freq_high <= spectral_config.REFERENCE_FREQ_HIGH
    )
    if np.any(ref_mask):
        reference_energy = np.percentile(mag_smooth[ref_mask], 50)
    else:
        reference_energy = np.max(mag_smooth)

    # Seuil de coupure
    cutoff_threshold = reference_energy - spectral_config.CUTOFF_THRESHOLD_DB

    # Analyse tranche par tranche à partir de CUTOFF_SCAN_START
    current_freq = spectral_config.CUTOFF_SCAN_START
    consecutive_low = 0

    while current_freq < freq_max:
        tranche_mask = (freq_high >= current_freq) & (freq_high < current_freq + tranche_size_hz)

        if np.any(tranche_mask):
            # On regarde le 75ème percentile pour être sûr qu'il n'y a pas de pics
            tranche_energy = np.percentile(mag_smooth[tranche_mask], 75)

            # Si cette tranche est très faible
            if tranche_energy < cutoff_threshold:
                consecutive_low += 1

                # Si N tranches consécutives sont faibles, c'est une vraie coupure
                if consecutive_low >= spectral_config.CONSECUTIVE_LOW_THRESHOLD:
                    # On retourne le début de la chute
                    return current_freq - (tranche_size_hz * (consecutive_low - 1))
            else:
                consecutive_low = 0

        current_freq += tranche_size_hz

    # Aucune coupure détectée -> authentique
    return float(freq_max)


def calculate_high_frequency_energy(frequencies: np.ndarray, magnitude: np.ndarray) -> float:
    """Calcule le ratio d'énergie dans les hautes fréquences (> HIGH_FREQ_THRESHOLD).

    Vérifie la présence CONTINUE d'énergie dans les hautes fréquences.

    Args:
        frequencies: Array des fréquences.
        magnitude: Array des magnitudes.

    Returns:
        Ratio d'énergie moyenne dans les hautes fréquences.
    """
    high_freq_idx = frequencies > spectral_config.HIGH_FREQ_THRESHOLD
    if not np.any(high_freq_idx):
        return 0.0

    # Analyse par tranches de 1 kHz
    tranche_energies: list[float] = []
    for f_start in range(spectral_config.HIGH_FREQ_THRESHOLD, int(frequencies[-1]), 1000):
        f_mask = (frequencies >= f_start) & (frequencies < f_start + 1000)
        if np.any(f_mask):
            tranche_energy = float(np.sum(magnitude[f_mask] ** 2))
            total_energy = float(np.sum(magnitude**2))
            tranche_energies.append(tranche_energy / total_energy if total_energy > 0 else 0.0)

    # Un vrai FLAC a de l'énergie dans TOUTES les tranches
    return float(np.mean(tranche_energies)) if tranche_energies else 0.0
