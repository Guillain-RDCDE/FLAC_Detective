"""Mathematical utilities for silence analysis.

This module contains low-level mathematical functions used by the silence
analysis module to detect vinyl noise, clicks, and other audio artifacts.
"""

import logging
import numpy as np
from scipy import signal
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def filter_band(
    audio_mono: np.ndarray,
    sample_rate: int,
    cutoff_freq: float
) -> Optional[np.ndarray]:
    """Apply bandpass filter above cutoff frequency.

    Args:
        audio_mono: Mono audio data
        sample_rate: Sample rate in Hz
        cutoff_freq: Cutoff frequency in Hz

    Returns:
        Filtered audio data or None if filtering fails
    """
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


def calculate_energy_db(audio_data: np.ndarray) -> float:
    """Calculate RMS energy in dB.

    Args:
        audio_data: Audio samples

    Returns:
        Energy in dB (relative to full scale)
    """
    rms_energy = np.sqrt(np.mean(audio_data ** 2))
    return float(20 * np.log10(rms_energy + 1e-10))


def calculate_autocorrelation(
    audio_data: np.ndarray,
    sample_rate: int,
    lag: int = 50
) -> float:
    """Calculate autocorrelation at specific lag.

    Used to detect random noise (low autocorrelation) vs periodic signals
    (high autocorrelation). Vinyl surface noise is typically random.

    Args:
        audio_data: Audio samples
        sample_rate: Sample rate in Hz
        lag: Lag in samples (default: 50)

    Returns:
        Autocorrelation coefficient (0.0 to 1.0)
    """
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


def calculate_temporal_variance(
    audio_data: np.ndarray,
    sample_rate: int
) -> float:
    """Calculate variance of energy across segments.

    Musical content has high temporal variance (loud/quiet sections).
    Constant noise has low temporal variance.

    Args:
        audio_data: Audio samples
        sample_rate: Sample rate in Hz

    Returns:
        Normalized variance (0.0 to 1.0+)
    """
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
        seg_db = calculate_energy_db(seg)
        segment_energies.append(seg_db)

    return float(np.std(segment_energies))


def detect_transients(
    audio_data: np.ndarray,
    sample_rate: int
) -> Tuple[int, float]:
    """Detect clicks and pops typical of vinyl records.

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
        peaks, _ = signal.find_peaks(
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
