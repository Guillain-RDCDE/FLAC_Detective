"""Spectral analysis of audio files."""

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
    """Analyzes the frequency spectrum of the audio file.

    Takes multiple samples at different times for robustness.

    Args:
        filepath: Path to the audio file.
        sample_duration: Duration in seconds to analyze.

    Returns:
        Tuple (cutoff_frequency, energy_ratio) where:
        - cutoff_frequency: detected cutoff frequency in Hz
        - energy_ratio: energy ratio in high frequencies
    """
    try:
        # Read entire file to know its duration
        info = sf.info(filepath)
        total_duration = info.duration
        samplerate = info.samplerate

        # Take 3 samples: start, middle, end (or just 1 if too short)
        num_samples = 3 if total_duration > 90 else 1
        sample_duration = min(sample_duration, total_duration / num_samples)

        cutoff_freqs = []
        energy_ratios = []

        for i in range(num_samples):
            # Start position of this sample
            start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
            start_time = max(0, start_time)
            start_frame = int(start_time * samplerate)

            # Read sample
            data, _ = sf.read(
                filepath,
                start=start_frame,
                frames=int(sample_duration * samplerate),
                always_2d=True,
            )

            # Convert to mono if stereo
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            else:
                data = data[:, 0]

            # Apply Hann window to reduce spectral leakage
            window = signal.windows.hann(len(data))
            data_windowed = data * window

            # Calculate FFT
            fft_vals = rfft(data_windowed)
            fft_freq = rfftfreq(len(data_windowed), 1 / samplerate)

            # Spectral magnitude (in dB)
            magnitude = np.abs(fft_vals)
            magnitude_db = 20 * np.log10(magnitude + 1e-10)

            # Detect cutoff frequency
            cutoff_freq = detect_cutoff(fft_freq, magnitude_db)
            cutoff_freqs.append(cutoff_freq)

            # Calculate high frequency energy ratio (> 16 kHz)
            energy_ratio = calculate_high_frequency_energy(fft_freq, magnitude)
            energy_ratios.append(energy_ratio)

        # Take the WORST value (min) for cutoff to be more strict
        # A transcoded file will have a low cutoff in ALL samples
        # We use min() because even one sample with low cutoff indicates transcoding
        final_cutoff = min(cutoff_freqs)
        
        # For energy, we also take min() to be consistent
        final_energy = min(energy_ratios)

        logger.info(
            f"Spectrum analysis: cutoff={final_cutoff:.0f} Hz, "
            f"energy_ratio={final_energy:.6f}, samples={cutoff_freqs}"
        )

        return final_cutoff, final_energy

    except Exception as e:
        logger.debug(f"Spectral analysis error: {e}")
        return 0, 0


def detect_cutoff(frequencies: np.ndarray, magnitude_db: np.ndarray) -> float:
    """Detects cutoff frequency with a robust method.

    Method based on percentiles:
    1. Calculates reference energy in a safe zone (10-14 kHz)
    2. Analyzes spectrum by 500 Hz slices starting from 14 kHz
    3. Detects a true cutoff = several consecutive slices below threshold

    Args:
        frequencies: Array of frequencies.
        magnitude_db: Array of magnitudes in dB.

    Returns:
        Detected cutoff frequency in Hz.
    """
    # Focus on frequencies > REFERENCE_FREQ_LOW
    high_freq_mask = frequencies > spectral_config.REFERENCE_FREQ_LOW
    if not np.any(high_freq_mask):
        return float(frequencies[-1])

    freq_high = frequencies[high_freq_mask]
    mag_high = magnitude_db[high_freq_mask]

    # Aggressive smoothing to ignore temporal variations
    if len(mag_high) > 100:
        from scipy.ndimage import uniform_filter1d

        mag_smooth = uniform_filter1d(mag_high, size=100)
    else:
        mag_smooth = mag_high

    # Slice analysis
    tranche_size_hz = spectral_config.TRANCHE_SIZE
    freq_max = freq_high[-1]

    # Calculate reference (median energy between REFERENCE_FREQ_LOW-REFERENCE_FREQ_HIGH)
    # This zone is safe even for a 128kbps MP3 (which cuts at 16k)
    ref_mask = (freq_high >= spectral_config.REFERENCE_FREQ_LOW) & (
        freq_high <= spectral_config.REFERENCE_FREQ_HIGH
    )
    if np.any(ref_mask):
        reference_energy = np.percentile(mag_smooth[ref_mask], 50)
    else:
        reference_energy = np.max(mag_smooth)

    # Cutoff threshold
    cutoff_threshold = reference_energy - spectral_config.CUTOFF_THRESHOLD_DB

    # Slice by slice analysis starting from CUTOFF_SCAN_START
    current_freq = spectral_config.CUTOFF_SCAN_START
    consecutive_low = 0

    while current_freq < freq_max:
        tranche_mask = (freq_high >= current_freq) & (freq_high < current_freq + tranche_size_hz)

        if np.any(tranche_mask):
            # Look at 75th percentile to ensure no peaks
            tranche_energy = np.percentile(mag_smooth[tranche_mask], 75)

            # If this slice is very low
            if tranche_energy < cutoff_threshold:
                consecutive_low += 1

                # If N consecutive slices are low, it's a true cutoff
                if consecutive_low >= spectral_config.CONSECUTIVE_LOW_THRESHOLD:
                    # Return start of drop
                    detected_cutoff = current_freq - (tranche_size_hz * (consecutive_low - 1))
                    logger.debug(
                        f"Cutoff detected at {detected_cutoff:.0f} Hz "
                        f"({consecutive_low} consecutive low slices)"
                    )
                    return detected_cutoff
            else:
                consecutive_low = 0

        current_freq += tranche_size_hz

    # No cutoff detected -> authentic
    logger.debug(f"No cutoff detected, full spectrum up to {freq_max:.0f} Hz")
    return float(freq_max)


def calculate_high_frequency_energy(frequencies: np.ndarray, magnitude: np.ndarray) -> float:
    """Calculates energy ratio in high frequencies (> HIGH_FREQ_THRESHOLD).

    Checks for CONTINUOUS presence of energy in high frequencies.

    Args:
        frequencies: Array of frequencies.
        magnitude: Array of magnitudes.

    Returns:
        Average energy ratio in high frequencies.
    """
    high_freq_idx = frequencies > spectral_config.HIGH_FREQ_THRESHOLD
    if not np.any(high_freq_idx):
        return 0.0

    # Analysis by 1 kHz slices
    tranche_energies: list[float] = []
    for f_start in range(spectral_config.HIGH_FREQ_THRESHOLD, int(frequencies[-1]), 1000):
        f_mask = (frequencies >= f_start) & (frequencies < f_start + 1000)
        if np.any(f_mask):
            tranche_energy = float(np.sum(magnitude[f_mask] ** 2))
            total_energy = float(np.sum(magnitude**2))
            tranche_energies.append(tranche_energy / total_energy if total_energy > 0 else 0.0)

    # A real FLAC has energy in ALL slices
    return float(np.mean(tranche_energies)) if tranche_energies else 0.0
