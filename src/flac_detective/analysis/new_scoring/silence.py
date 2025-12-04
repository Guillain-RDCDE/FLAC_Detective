"""Silence analysis module for Rule 7.

This module implements the logic to detect silences in audio files and analyze
the high-frequency energy ratio between silence and music to distinguish
between authentic FLACs and converted MP3s.
"""

import logging
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import List, Tuple, Optional
from scipy import signal

logger = logging.getLogger(__name__)

def detect_silences(
    audio_data: np.ndarray,
    sample_rate: int,
    threshold_db: float = -40.0,
    min_duration: float = 0.5
) -> List[Tuple[int, int]]:
    """Detect silent segments in audio data.

    Args:
        audio_data: Audio samples (numpy array)
        sample_rate: Sample rate in Hz
        threshold_db: Silence threshold in dB (relative to full scale)
        min_duration: Minimum duration of silence in seconds

    Returns:
        List of (start_index, end_index) tuples for silent segments
    """
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_mono = np.mean(audio_data, axis=1)
    else:
        audio_mono = audio_data

    # Calculate amplitude in dB
    # Avoid log of zero by adding a small epsilon
    amplitude = np.abs(audio_mono)
    db_levels = 20 * np.log10(amplitude + 1e-10)

    # Create boolean mask for silence
    is_silence = db_levels < threshold_db

    # Find segments
    # Pad with False to detect edges
    is_silence_padded = np.concatenate(([False], is_silence, [False]))
    diff = np.diff(is_silence_padded.astype(int))

    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]

    silence_segments = []
    min_samples = int(min_duration * sample_rate)

    for start, end in zip(starts, ends):
        if (end - start) >= min_samples:
            silence_segments.append((start, end))

    return silence_segments

def calculate_spectral_energy(
    audio_segment: np.ndarray,
    sample_rate: int,
    freq_range: Tuple[int, int] = (16000, 22000)
) -> float:
    """Calculate normalized spectral energy in a specific frequency band.

    Args:
        audio_segment: Audio samples
        sample_rate: Sample rate in Hz
        freq_range: (min_freq, max_freq) to analyze

    Returns:
        Normalized energy value (0.0 to 1.0)
    """
    if len(audio_segment) == 0:
        return 0.0

    # Apply FFT
    # Use a window to reduce spectral leakage
    window = np.hanning(len(audio_segment))
    fft_result = np.fft.rfft(audio_segment * window)
    fft_freqs = np.fft.rfftfreq(len(audio_segment), 1/sample_rate)

    # Calculate power spectrum (magnitude squared)
    power_spectrum = np.abs(fft_result) ** 2

    # Find indices for the frequency range
    min_freq, max_freq = freq_range
    idx_min = np.searchsorted(fft_freqs, min_freq)
    idx_max = np.searchsorted(fft_freqs, max_freq)

    # Sum energy in the band
    band_energy = np.sum(power_spectrum[idx_min:idx_max])

    # Normalize by number of samples to make it comparable
    # (Simplified normalization as per requirements)
    normalized_energy = band_energy / len(audio_segment)

    return float(normalized_energy)

def analyze_silence_ratio(
    file_path: Path
) -> Tuple[Optional[float], str, float, float]:
    """Analyze the ratio of HF energy between silence and music.

    Args:
        file_path: Path to the audio file

    Returns:
        Tuple of (ratio, verdict_code, silence_energy, music_energy)
        ratio can be None if analysis failed (e.g. no silence)
        verdict_code: "TRANSCODE", "AUTHENTIC", "UNCERTAIN", "NO_SILENCE", etc.
    """
    try:
        # Load audio file
        # Using soundfile directly
        data, sample_rate = sf.read(file_path)

        # 1. Detect silences
        silences = detect_silences(data, sample_rate)

        if not silences:
            logger.info("Rule 7: No silence detected")
            return None, "NO_SILENCE", 0.0, 0.0

        # Calculate total silence duration
        total_silence_samples = sum(end - start for start, end in silences)
        total_silence_sec = total_silence_samples / sample_rate

        if total_silence_sec < 2.0:
            logger.info(f"Rule 7: Insufficient silence ({total_silence_sec:.2f}s < 2.0s)")
            return None, "INSUFFICIENT_SILENCE", 0.0, 0.0

        # 2. Extract audio segments

        # 2.1 Music reference (10s to 40s)
        start_music = int(10 * sample_rate)
        end_music = int(40 * sample_rate)

        # Handle short files
        if len(data) < end_music:
            end_music = len(data)
            start_music = max(0, end_music - int(30 * sample_rate))

        if start_music >= end_music:
             # Fallback for very short files
             start_music = 0
             end_music = len(data) // 2

        music_segment = data[start_music:end_music]

        # Flatten to mono if needed for FFT
        if len(music_segment.shape) > 1:
            music_segment = np.mean(music_segment, axis=1)

        # 2.2 Silence segments
        silence_audio_list = []
        for start, end in silences:
            segment = data[start:end]
            if len(segment.shape) > 1:
                segment = np.mean(segment, axis=1)
            silence_audio_list.append(segment)

        if not silence_audio_list:
             return None, "ERROR_EXTRACTING_SILENCE", 0.0, 0.0

        silence_segment = np.concatenate(silence_audio_list)

        # 3. Calculate Energy
        energy_music = calculate_spectral_energy(music_segment, sample_rate)
        energy_silence = calculate_spectral_energy(silence_segment, sample_rate)

        # 4. Calculate Ratio
        # Add epsilon to avoid division by zero
        ratio = energy_silence / (energy_music + 1e-10)

        logger.info(
            f"Rule 7 Analysis: Silence={total_silence_sec:.2f}s, "
            f"Energy(Silence)={energy_silence:.2e}, Energy(Music)={energy_music:.2e}, "
            f"Ratio={ratio:.4f}"
        )

        return ratio, "OK", energy_silence, energy_music

    except Exception as e:
        logger.error(f"Error in Rule 7 analysis: {e}")
        return None, "ERROR", 0.0, 0.0


def _filter_band(
    audio_mono: np.ndarray,
    sample_rate: int,
    cutoff_freq: float
) -> Optional[np.ndarray]:
    """Apply bandpass filter above cutoff frequency."""
    nyquist = sample_rate / 2

    # Need at least 1 kHz above cutoff for analysis
    if cutoff_freq >= nyquist - 1000:
        logger.debug("VINYL: Cutoff too close to Nyquist for noise analysis")
        return None

    # Bandpass filter: cutoff_freq to Nyquist - 100Hz
    upper_freq = nyquist - 100

    try:
        sos = signal.butter(4, [cutoff_freq, upper_freq], 'bandpass', fs=sample_rate, output='sos')
        return signal.sosfilt(sos, audio_mono)
    except Exception as e:
        logger.warning(f"VINYL: Filtering failed: {e}")
        return None


def _calculate_energy_db(audio_data: np.ndarray) -> float:
    """Calculate RMS energy in dB."""
    rms_energy = np.sqrt(np.mean(audio_data ** 2))
    return float(20 * np.log10(rms_energy + 1e-10))


def _calculate_autocorrelation(audio_data: np.ndarray, sample_rate: int, lag: int = 50) -> float:
    """Calculate autocorrelation at specific lag."""
    # Use a short segment for autocorrelation
    segment_length = min(len(audio_data), int(sample_rate * 1.0))  # 1 second
    segment = audio_data[:segment_length]

    # Normalize
    segment = segment - np.mean(segment)
    segment = segment / (np.std(segment) + 1e-10)

    if len(segment) > lag * 2:
        autocorr = np.corrcoef(segment[:-lag], segment[lag:])[0, 1]
        return float(np.abs(autocorr))
    return 0.0


def _calculate_temporal_variance(audio_data: np.ndarray, sample_rate: int) -> float:
    """Calculate variance of energy across segments."""
    segment_duration = 1.0  # seconds
    segment_samples = int(segment_duration * sample_rate)
    num_segments = min(5, len(audio_data) // segment_samples)

    if num_segments < 2:
        return 0.0

    segment_energies = []
    for i in range(num_segments):
        start_idx = i * segment_samples
        end_idx = start_idx + segment_samples
        seg = audio_data[start_idx:end_idx]
        seg_db = _calculate_energy_db(seg)
        segment_energies.append(seg_db)

    return float(np.std(segment_energies))


def detect_vinyl_noise(
    audio_data: np.ndarray,
    sample_rate: int,
    cutoff_freq: float
) -> Tuple[bool, dict]:
    """Detect vinyl surface noise above the musical cutoff (Phase 2).

    Vinyl records have characteristic noise above the musical content:
    - Present energy (> -70dB)
    - Random texture (low autocorrelation)
    - Temporally constant (low variance)

    Args:
        audio_data: Audio samples (mono or stereo)
        sample_rate: Sample rate in Hz
        cutoff_freq: Musical cutoff frequency in Hz

    Returns:
        Tuple of (is_vinyl, details_dict)
    """
    details = {
        'energy_db': -100.0,
        'autocorr': 0.0,
        'temporal_variance': 0.0,
        'is_vinyl': False
    }

    # Convert to mono if stereo
    if audio_data.ndim > 1:
        audio_mono = np.mean(audio_data, axis=1)
    else:
        audio_mono = audio_data

    # Filter band above cutoff
    noise_band = _filter_band(audio_mono, sample_rate, cutoff_freq)
    if noise_band is None:
        return False, details

    # 1. Measure average energy in dB
    energy_db = _calculate_energy_db(noise_band)
    details['energy_db'] = energy_db

    logger.debug(f"VINYL: Noise energy = {energy_db:.1f} dB")

    # Vinyl noise should be present (> -70dB)
    if energy_db < -70:
        logger.debug("VINYL: No significant noise detected")
        return False, details

    # 2. Calculate autocorrelation (texture analysis)
    autocorr = _calculate_autocorrelation(noise_band, sample_rate)
    details['autocorr'] = autocorr
    logger.debug(f"VINYL: Autocorrelation = {autocorr:.3f}")

    # 3. Measure temporal constancy
    temporal_variance = _calculate_temporal_variance(noise_band, sample_rate)
    details['temporal_variance'] = temporal_variance
    logger.debug(f"VINYL: Temporal variance = {temporal_variance:.2f} dB")

    # Decision criteria for vinyl noise:
    # 1. Energy > -70dB (noise present)
    # 2. Autocorrelation < 0.3 (random, not patterned)
    # 3. Temporal variance < 5dB (constant)

    is_vinyl = (
        energy_db > -70 and
        details['autocorr'] < 0.3 and
        details['temporal_variance'] < 5.0
    )

    details['is_vinyl'] = is_vinyl

    if is_vinyl:
        logger.info(
            f"VINYL: Detected vinyl noise (energy={energy_db:.1f}dB, "
            f"autocorr={details['autocorr']:.3f}, variance={details['temporal_variance']:.2f}dB)"
        )
    else:
        logger.debug(
            f"VINYL: Not vinyl noise (energy={energy_db:.1f}dB, "
            f"autocorr={details['autocorr']:.3f}, variance={details['temporal_variance']:.2f}dB)"
        )

    return is_vinyl, details


def detect_clicks_and_pops(
    audio_data: np.ndarray,
    sample_rate: int
) -> Tuple[int, float]:
    """Detect clicks and pops typical of vinyl records (Phase 3).

    Vinyl records have brief transients (clicks/pops) from dust and scratches.
    Typical vinyl: 5-50 clicks per minute.

    Args:
        audio_data: Audio samples (mono or stereo)
        sample_rate: Sample rate in Hz

    Returns:
        Tuple of (num_clicks, clicks_per_minute)
    """
    # Convert to mono if stereo
    if audio_data.ndim > 1:
        audio_mono = np.mean(audio_data, axis=1)
    else:
        audio_mono = audio_data

    # Calculate duration
    duration_sec = len(audio_mono) / sample_rate

    if duration_sec < 10:
        logger.debug("CLICKS: Audio too short for click detection")
        return 0, 0.0

    # Detect brief transients (<1ms duration)
    # Use envelope detection

    # High-pass filter to remove low-frequency content
    try:
        sos = signal.butter(4, 1000, 'highpass', fs=sample_rate, output='sos')
        audio_hp = signal.sosfilt(sos, audio_mono)
    except Exception as e:
        logger.warning(f"CLICKS: Filtering failed: {e}")
        return 0, 0.0

    # Envelope detection
    analytic_signal = signal.hilbert(audio_hp)
    envelope = np.abs(analytic_signal)

    # Smooth envelope slightly
    window_size = int(0.0005 * sample_rate)  # 0.5ms
    if window_size % 2 == 0:
        window_size += 1
    if window_size >= 3:
        envelope_smooth = signal.medfilt(envelope, window_size)
    else:
        envelope_smooth = envelope

    # Find peaks (clicks)
    # Threshold: 3x median envelope
    threshold = np.median(envelope_smooth) * 3

    # Peaks must be at least 10ms apart
    min_distance = int(0.01 * sample_rate)

    try:
        peaks, properties = signal.find_peaks(
            envelope_smooth,
            height=threshold,
            distance=min_distance
        )
    except Exception as e:
        logger.warning(f"CLICKS: Peak detection failed: {e}")
        return 0, 0.0

    num_clicks = len(peaks)
    clicks_per_minute = (num_clicks / duration_sec) * 60

    logger.debug(
        f"CLICKS: Detected {num_clicks} clicks in {duration_sec:.1f}s "
        f"({clicks_per_minute:.1f} clicks/min)"
    )

    return num_clicks, clicks_per_minute
