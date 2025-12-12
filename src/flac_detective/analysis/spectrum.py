"""Spectral analysis of audio files."""

import logging
from pathlib import Path
from typing import Tuple, List

import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq, set_workers

from ..config import spectral_config
from .audio_cache import AudioCache
from .window_cache import get_hann_window

logger = logging.getLogger(__name__)


def analyze_spectrum(filepath: Path, sample_duration: float = 30.0, cache: AudioCache = None) -> Tuple[float, float, float]:
    """Analyzes the frequency spectrum of the audio file.

    Takes multiple samples at different times for robustness.
    OPTIMIZED: Uses AudioCache to avoid multiple file reads.

    Args:
        filepath: Path to the audio file.
        sample_duration: Duration in seconds to analyze.
        cache: Optional AudioCache instance for optimization.

    Returns:
        Tuple (cutoff_frequency, energy_ratio, cutoff_std) where:
        - cutoff_frequency: detected cutoff frequency in Hz
        - energy_ratio: energy ratio in high frequencies
        - cutoff_std: standard deviation of cutoff frequency
    """
    try:
        # Create cache if not provided
        if cache is None:
            cache = AudioCache(filepath)

        # Read entire file to know its duration
        info = sf.info(filepath)
        total_duration = info.duration
        samplerate = info.samplerate

        # Take 3 samples: start, middle, end (or just 1 if too short)
        num_samples = 3 if total_duration > 90 else 1
        sample_duration = min(sample_duration, total_duration / num_samples)

        cutoff_freqs = []
        energy_ratios = []

        def _analyze_sample(i: int) -> Tuple[float, float]:
            """Analyze a single sample."""
            # Start position of this sample
            start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
            start_time = max(0, start_time)
            start_frame = int(start_time * samplerate)
            frames_to_read = int(sample_duration * samplerate)

            # OPTIMIZATION: Use cache instead of direct sf.read
            logger.debug(f"⚡ CACHE: Reading segment {i+1}/{num_samples} via cache")
            data, _ = cache.get_segment(start_frame, frames_to_read)

            # Convert to mono if stereo
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            else:
                data = data[:, 0]

            # Apply Hann window to reduce spectral leakage
            # PHASE 2 OPTIMIZATION: Use cached window
            window = get_hann_window(len(data))
            data_windowed = data * window

            # Calculate FFT
            # PHASE 3 OPTIMIZATION: Use parallel FFT
            # Limit FFT to 1 worker to avoid thread explosion in multiprocess context
            with set_workers(1):
                fft_vals = rfft(data_windowed)
            fft_freq = rfftfreq(len(data_windowed), 1 / samplerate)

            # Spectral magnitude (in dB)
            magnitude = np.abs(fft_vals)
            magnitude_db = 20 * np.log10(magnitude + 1e-10)

            # Detect cutoff frequency
            cutoff_freq = detect_cutoff(fft_freq, magnitude_db)

            # Calculate high frequency energy ratio (> 16 kHz)
            energy_ratio = calculate_high_frequency_energy(fft_freq, magnitude)
            
            return cutoff_freq, energy_ratio

        # PHASE 4 OPTIMIZATION: Parallelize sample analysis
        # Draw samples sequentially to avoid thread overhead
        results = [_analyze_sample(i) for i in range(num_samples)]
        cutoff_freqs = [r[0] for r in results]
        energy_ratios = [r[1] for r in results]

        # Take the WORST value (min) for cutoff to be more strict
        # A transcoded file will have a low cutoff in ALL samples
        # We use min() because even one sample with low cutoff indicates transcoding
        final_cutoff = min(cutoff_freqs)

        # For energy, we also take min() to be consistent
        final_energy = min(energy_ratios)

        # Calculate standard deviation of cutoffs to detect variable spectral content
        # Authentic FLACs often have high variance in cutoff frequency
        cutoff_std = float(np.std(cutoff_freqs)) if len(cutoff_freqs) > 1 else 0.0

        logger.info(
            f"Spectrum analysis: cutoff={final_cutoff:.0f} Hz, "
            f"energy_ratio={final_energy:.6f}, cutoff_std={cutoff_std:.1f}, samples={cutoff_freqs}"
        )

        return final_cutoff, final_energy, cutoff_std

    except Exception as e:
        logger.debug(f"Spectral analysis error: {e}")
        return 0, 0, 0


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


def analyze_segment_consistency(filepath: Path, progressive: bool = True, cache: AudioCache = None) -> Tuple[List[float], float]:
    """Analyzes segments of the file to detect cutoff consistency (OPTIMIZED - Progressive).

    Phase 2 Optimization: Progressive analysis
    - Start with 2 segments (Start + End) for quick check
    - If coherent (variance < 500 Hz), STOP (60% of cases)
    - Otherwise, analyze 3 more segments (25%, 50%, 75%)

    PHASE 1 OPTIMIZATION: Uses AudioCache to avoid multiple file reads.

    Segments: Start (5%), 25%, 50%, 75%, End (95%)

    Args:
        filepath: Path to the audio file.
        progressive: If True, use progressive analysis (default). If False, analyze all 5 segments.
        cache: Optional AudioCache instance for optimization.

    Returns:
        Tuple (list_of_cutoffs, cutoff_variance)
    """
    try:
        # Create cache if not provided
        if cache is None:
            cache = AudioCache(filepath)

        info = sf.info(filepath)
        total_duration = info.duration
        samplerate = info.samplerate

        segment_duration = 10.0  # 10 seconds per segment

        def analyze_single_segment(center_ratio: float) -> float:
            """Analyze a single segment and return its cutoff."""
            center_time = total_duration * center_ratio
            start_time = max(0, center_time - (segment_duration / 2))

            # Ensure we don't go past end
            if start_time + segment_duration > total_duration:
                start_time = max(0, total_duration - segment_duration)

            start_frame = int(start_time * samplerate)
            frames_to_read = int(segment_duration * samplerate)

            try:
                # OPTIMIZATION: Use cache instead of direct sf.read
                logger.debug(f"⚡ CACHE: Reading segment at {center_ratio*100:.0f}% via cache")
                data, _ = cache.get_segment(start_frame, frames_to_read)

                if len(data) < frames_to_read and len(data) == 0:
                    return 0.0

                # Convert to mono
                if data.shape[1] > 1:
                    data = np.mean(data, axis=1)
                else:
                    data = data[:, 0]

                # Windowing
                # PHASE 2 OPTIMIZATION: Use cached window
                window = get_hann_window(len(data))
                data_windowed = data * window

                # FFT
                # PHASE 3 OPTIMIZATION: Use parallel FFT
                # Limit FFT to 1 worker
                with set_workers(1):
                    fft_vals = rfft(data_windowed)
                fft_freq = rfftfreq(len(data_windowed), 1 / samplerate)

                magnitude = np.abs(fft_vals)
                magnitude_db = 20 * np.log10(magnitude + 1e-10)

                cutoff = detect_cutoff(fft_freq, magnitude_db)
                return cutoff

            except Exception as e:
                logger.warning(f"Error analyzing segment at {center_ratio*100:.0f}%: {e}")
                return 0.0

        # PHASE 1: Analyze Start + End (2 segments)
        # Analyze Start + End (Sequential)
        cutoffs = [analyze_single_segment(0.05), analyze_single_segment(0.95)]

        # Filter valid cutoffs
        valid_cutoffs = [c for c in cutoffs if c > 0]

        if len(valid_cutoffs) < 2:
            logger.warning("OPTIMIZATION R10: Less than 2 valid segments, cannot determine consistency")
            return cutoffs, 0.0

        # Calculate initial variance
        variance = float(np.std(valid_cutoffs))

        logger.debug(f"OPTIMIZATION R10: Phase 1 - Start={cutoffs[0]:.0f} Hz, End={cutoffs[1]:.0f} Hz, Variance={variance:.1f} Hz")

        # PHASE 2: Progressive decision
        if progressive:
            # If variance < 500 Hz, segments are coherent -> STOP
            if variance < 500:
                logger.info(f"⚡ OPTIMIZATION R10: Early stop - Coherent segments (variance {variance:.1f} < 500 Hz)")
                # Return only 2 segments (optimization)
                return cutoffs, variance

            # If variance > 1000 Hz, already know it's dynamic -> STOP
            if variance > 1000:
                logger.info(f"⚡ OPTIMIZATION R10: Early stop - High variance detected ({variance:.1f} > 1000 Hz)")
                return cutoffs, variance

            # Otherwise (500 <= variance <= 1000), need more data
            logger.info(f"OPTIMIZATION R10: Expanding to 5 segments (variance {variance:.1f} in grey zone)")

        # PHASE 3: Analyze middle segments (25%, 50%, 75%)
        # Analyze middle segments (Sequential)
        middle_segments = [0.25, 0.50, 0.75]
        results = {r: analyze_single_segment(r) for r in middle_segments}

        # Insert in correct position to maintain order
        cutoffs.insert(1, results[0.25])
        cutoffs.insert(2, results[0.50])
        cutoffs.insert(3, results[0.75])

        # Recalculate variance with all 5 segments
        valid_cutoffs = [c for c in cutoffs if c > 0]

        if len(valid_cutoffs) > 1:
            variance = float(np.std(valid_cutoffs))
        else:
            variance = 0.0

        logger.debug(f"OPTIMIZATION R10: Phase 3 - All 5 segments analyzed, final variance={variance:.1f} Hz")

        return cutoffs, variance

    except Exception as e:
        logger.error(f"Segment consistency analysis failed: {e}")
        return [], 0.0
