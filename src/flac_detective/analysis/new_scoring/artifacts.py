"""Detection of psychoacoustic compression artifacts (MP3/AAC signatures).

This module implements advanced detection methods for lossy compression artifacts
that go beyond simple frequency cutoff analysis:
- Pre-echo detection (MDCT artifacts)
- Aliasing in high frequencies (filterbank artifacts)
- MP3 quantization noise patterns
"""

import logging
import numpy as np
from typing import Optional, Tuple
import soundfile as sf
from scipy import signal
from scipy.fft import fft, fftfreq

from .audio_loader import load_audio_with_retry

logger = logging.getLogger(__name__)


def detect_preecho_artifacts(
    audio_data: np.ndarray,
    sample_rate: int,
    threshold_db: float = -3.0
) -> Tuple[float, int, int]:
    """Detect pre-echo artifacts before transients (Test 9A).

    MDCT-based codecs (MP3/AAC) create "ghost" artifacts before sharp transients
    due to the time-frequency uncertainty principle.

    Args:
        audio_data: Audio samples (mono or will be converted to mono)
        sample_rate: Sample rate in Hz
        threshold_db: Threshold for transient detection (default: -3dB)

    Returns:
        Tuple of (percentage_affected, num_transients, num_with_preecho)
    """
    # Convert to mono if stereo
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)

    # Normalize
    audio_data = audio_data / (np.max(np.abs(audio_data)) + 1e-10)

    # Convert threshold to linear
    threshold_linear = 10 ** (threshold_db / 20.0)

    # Find transients (sharp peaks)
    # Use envelope detection
    analytic_signal = signal.hilbert(audio_data)
    envelope = np.abs(analytic_signal)

    # Smooth envelope
    window_size = int(0.001 * sample_rate)  # 1ms window
    if window_size % 2 == 0:
        window_size += 1
    envelope_smooth = signal.medfilt(envelope, window_size)

    # Find peaks above threshold
    peaks, properties = signal.find_peaks(
        envelope_smooth,
        height=threshold_linear,
        distance=int(0.05 * sample_rate)  # At least 50ms apart
    )

    num_transients = len(peaks)

    if num_transients == 0:
        logger.debug("ARTIFACTS: No transients found for pre-echo analysis")
        return 0.0, 0, 0

    # Analyze 20ms before each peak
    pre_window_samples = int(0.020 * sample_rate)  # 20ms
    post_window_samples = int(0.010 * sample_rate)  # 10ms

    # High-frequency band (10-20 kHz)
    nyquist = sample_rate / 2
    if nyquist < 10000:
        logger.debug("ARTIFACTS: Sample rate too low for HF pre-echo analysis")
        return 0.0, num_transients, 0

    # Bandpass filter 10-20 kHz
    sos = signal.butter(4, [10000, min(20000, nyquist - 100)], 'bandpass', fs=sample_rate, output='sos')
    audio_hf = signal.sosfilt(sos, audio_data)

    # Calculate baseline HF energy (from quiet sections)
    baseline_energy = np.median(audio_hf ** 2)

    num_with_preecho = 0

    for peak_idx in peaks:
        # Skip if too close to start
        if peak_idx < pre_window_samples + post_window_samples:
            continue

        # Energy before transient
        pre_start = peak_idx - pre_window_samples
        pre_end = peak_idx - post_window_samples
        pre_energy = np.mean(audio_hf[pre_start:pre_end] ** 2)

        # Check if pre-echo detected (energy > 3x baseline)
        if pre_energy > baseline_energy * 3:
            num_with_preecho += 1

    percentage_affected = (num_with_preecho / num_transients) * 100 if num_transients > 0 else 0.0

    logger.debug(
        f"ARTIFACTS: Pre-echo analysis: {num_with_preecho}/{num_transients} transients affected "
        f"({percentage_affected:.1f}%)"
    )

    return percentage_affected, num_transients, num_with_preecho


def detect_hf_aliasing(
    audio_data: np.ndarray,
    sample_rate: int
) -> float:
    """Detect aliasing in high frequencies (Test 9B).

    MP3 filterbanks create spectral replicas with phase inversion.
    This detects correlation between inverted frequency bands.

    Args:
        audio_data: Audio samples (mono or will be converted to mono)
        sample_rate: Sample rate in Hz

    Returns:
        Correlation coefficient (0-1, higher = more aliasing)
    """
    # Convert to mono if stereo
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)

    nyquist = sample_rate / 2

    # Need at least 20 kHz Nyquist for this test
    if nyquist < 15000:
        logger.debug("ARTIFACTS: Sample rate too low for aliasing detection")
        return 0.0

    # Extract band A: 10-15 kHz
    sos_a = signal.butter(4, [10000, 15000], 'bandpass', fs=sample_rate, output='sos')
    band_a = signal.sosfilt(sos_a, audio_data)

    # Extract band B: 15-20 kHz (or up to Nyquist)
    upper_freq = min(20000, nyquist - 100)
    sos_b = signal.butter(4, [15000, upper_freq], 'bandpass', fs=sample_rate, output='sos')
    band_b = signal.sosfilt(sos_b, audio_data)

    # Invert band B
    band_b_inverted = -band_b

    # Calculate correlation
    # Use segments to avoid memory issues
    segment_length = min(len(band_a), int(sample_rate * 5))  # 5 seconds max

    correlations = []
    for i in range(0, len(band_a) - segment_length, segment_length // 2):
        seg_a = band_a[i:i + segment_length]
        seg_b_inv = band_b_inverted[i:i + segment_length]

        if np.std(seg_a) < 1e-6 or np.std(seg_b_inv) < 1e-6:
             correlations.append(0.0)
             continue

        # Normalize
        seg_a = seg_a / (np.std(seg_a) + 1e-10)
        seg_b_inv = seg_b_inv / (np.std(seg_b_inv) + 1e-10)

        # Correlation
        try:
            corr = np.abs(np.corrcoef(seg_a, seg_b_inv)[0, 1])
            if np.isnan(corr):
                corr = 0.0
        except Exception:
            corr = 0.0
            
        correlations.append(corr)

    if not correlations:
        return 0.0

    # Use median correlation
    correlation = np.median(correlations)

    logger.debug(f"ARTIFACTS: HF aliasing correlation: {correlation:.3f}")

    return float(correlation)


def detect_mp3_noise_pattern(
    audio_data: np.ndarray,
    sample_rate: int
) -> bool:
    """Detect MP3 quantization noise patterns (Test 9C).

    MP3 uses 32 subbands with regular spacing. This creates periodic
    patterns in the noise floor at specific frequencies (~689Hz, ~1378Hz).

    Args:
        audio_data: Audio samples (mono or will be converted to mono)
        sample_rate: Sample rate in Hz

    Returns:
        True if MP3 noise pattern detected, False otherwise
    """
    # Convert to mono if stereo
    if audio_data.ndim > 1:
        audio_data = np.mean(audio_data, axis=1)

    nyquist = sample_rate / 2

    # Need at least 20 kHz for this test
    if nyquist < 16000:
        logger.debug("ARTIFACTS: Sample rate too low for noise pattern detection")
        return False

    # Extract high-frequency noise band (16-20 kHz)
    upper_freq = min(20000, nyquist - 100)
    sos = signal.butter(4, [16000, upper_freq], 'bandpass', fs=sample_rate, output='sos')
    noise_band = signal.sosfilt(sos, audio_data)

    # Analyze segments
    segment_length = int(sample_rate * 2)  # 2 seconds

    if len(noise_band) < segment_length:
        logger.debug("ARTIFACTS: Audio too short for noise pattern analysis")
        return False

    # Take middle segment to avoid edge effects
    start_idx = len(noise_band) // 2 - segment_length // 2
    segment = noise_band[start_idx:start_idx + segment_length]

    # FFT on the noise
    fft_result = fft(segment)
    freqs = fftfreq(len(segment), 1 / sample_rate)

    # Only positive frequencies
    positive_freq_idx = freqs > 0
    freqs = freqs[positive_freq_idx]
    magnitude = np.abs(fft_result[positive_freq_idx])

    # Look for peaks at MP3 critical band frequencies
    # MP3 subbands are ~689Hz apart (22050 / 32)
    target_freqs = [689, 1378, 2067]  # First 3 harmonics

    detected_peaks = 0

    for target_freq in target_freqs:
        # Find peak near target frequency (±50Hz tolerance)
        freq_mask = (freqs >= target_freq - 50) & (freqs <= target_freq + 50)

        if not np.any(freq_mask):
            continue

        local_magnitude = magnitude[freq_mask]
        local_freqs = freqs[freq_mask]

        if len(local_magnitude) == 0:
            continue

        # Check if there's a significant peak
        peak_idx = np.argmax(local_magnitude)
        peak_value = local_magnitude[peak_idx]

        # Compare to surrounding noise floor
        noise_floor = np.median(magnitude)

        if peak_value > noise_floor * 2:  # Peak is 2x above noise floor
            detected_peaks += 1
            logger.debug(f"ARTIFACTS: MP3 noise peak detected at {local_freqs[peak_idx]:.1f} Hz")

    # If we detect at least 2 out of 3 harmonics, it's likely MP3
    pattern_detected = detected_peaks >= 2

    logger.debug(
        f"ARTIFACTS: MP3 noise pattern: {detected_peaks}/3 peaks detected "
        f"({'DETECTED' if pattern_detected else 'NOT DETECTED'})"
    )

    return pattern_detected


def analyze_compression_artifacts(
    file_path: str,
    cutoff_freq: float,
    mp3_bitrate_detected: Optional[int],
    audio_data: Optional[np.ndarray] = None,
    sample_rate: Optional[int] = None
) -> Tuple[int, list, dict]:
    """Analyze file for psychoacoustic compression artifacts (Rule 9).

    This function performs three tests:
    - Test 9A: Pre-echo detection
    - Test 9B: HF aliasing detection
    - Test 9C: MP3 noise pattern detection

    Args:
        file_path: Path to the FLAC file
        cutoff_freq: Detected cutoff frequency in Hz
        mp3_bitrate_detected: MP3 bitrate from Rule 1 (or None)
        audio_data: Optional pre-loaded audio data
        sample_rate: Optional sample rate of pre-loaded data

    Returns:
        Tuple of (score_delta, list_of_reasons, details_dict)
    """
    score = 0
    reasons = []
    details = {
        'preecho_percentage': 0.0,
        'aliasing_correlation': 0.0,
        'mp3_noise_pattern': False,
        'tests_run': []
    }

    # Activation condition: cutoff < 21 kHz OR MP3 signature detected
    should_activate = cutoff_freq < 21000 or mp3_bitrate_detected is not None

    if not should_activate:
        logger.debug(
            f"RULE 9: Skipped (cutoff {cutoff_freq:.0f} Hz >= 21000 and no MP3 signature)"
        )
        return score, reasons, details

    logger.info("RULE 9: Activation - Analyzing compression artifacts...")

    try:
        # Load audio file with retry mechanism if not provided
        if audio_data is None or sample_rate is None:
            logger.info("RULE 9: Loading audio from file (no cache provided)...")
            audio_data, sample_rate = load_audio_with_retry(file_path)
        else:
            logger.info("RULE 9: Using pre-loaded audio data (cached)")
        
        if audio_data is None or sample_rate is None:
            logger.error(
                f"RULE 9: Failed to load audio after retries. "
                f"Returning 0 points (no penalty for temporary decoder issues)."
            )
            return 0, [], details

        # Test 9A: Pre-echo detection
        try:
            preecho_pct, num_transients, num_affected = detect_preecho_artifacts(
                audio_data, sample_rate
            )
            details['preecho_percentage'] = preecho_pct
            details['tests_run'].append('9A')

            if preecho_pct > 10:
                score += 15
                reasons.append(f"R9A: Pré-echo détecté ({preecho_pct:.1f}% transitoires affectées) (+15pts)")
                logger.info(f"RULE 9A: +15 points (pre-echo {preecho_pct:.1f}% > 10%)")
            elif preecho_pct >= 5:
                score += 10
                reasons.append(f"R9A: Pré-echo modéré ({preecho_pct:.1f}% transitoires) (+10pts)")
                logger.info(f"RULE 9A: +10 points (pre-echo {preecho_pct:.1f}% >= 5%)")
            else:
                logger.debug(f"RULE 9A: 0 points (pre-echo {preecho_pct:.1f}% < 5%)")

        except Exception as e:
            logger.warning(f"RULE 9A: Pre-echo analysis failed: {e}")

        # Test 9B: HF aliasing detection
        try:
            aliasing_corr = detect_hf_aliasing(audio_data, sample_rate)
            details['aliasing_correlation'] = aliasing_corr
            details['tests_run'].append('9B')

            if aliasing_corr > 0.5:
                score += 15
                reasons.append(f"R9B: Aliasing HF fort (corr={aliasing_corr:.2f}) (+15pts)")
                logger.info(f"RULE 9B: +15 points (aliasing {aliasing_corr:.2f} > 0.5)")
            elif aliasing_corr >= 0.3:
                score += 10
                reasons.append(f"R9B: Aliasing HF modéré (corr={aliasing_corr:.2f}) (+10pts)")
                logger.info(f"RULE 9B: +10 points (aliasing {aliasing_corr:.2f} >= 0.3)")
            else:
                logger.debug(f"RULE 9B: 0 points (aliasing {aliasing_corr:.2f} < 0.3)")

        except Exception as e:
            logger.warning(f"RULE 9B: Aliasing analysis failed: {e}")

        # Test 9C: MP3 noise pattern detection
        try:
            mp3_pattern = detect_mp3_noise_pattern(audio_data, sample_rate)
            details['mp3_noise_pattern'] = mp3_pattern
            details['tests_run'].append('9C')

            if mp3_pattern:
                score += 10
                reasons.append("R9C: Pattern de bruit MP3 détecté (+10pts)")
                logger.info("RULE 9C: +10 points (MP3 noise pattern detected)")
            else:
                logger.debug("RULE 9C: 0 points (no MP3 noise pattern)")

        except Exception as e:
            logger.warning(f"RULE 9C: MP3 noise pattern analysis failed: {e}")

    except Exception as e:
        logger.error(f"RULE 9: Failed to load audio file: {e}")
        return score, reasons, details

    if score > 0:
        logger.info(f"RULE 9: Total +{score} points from artifact detection")
    else:
        logger.info("RULE 9: No compression artifacts detected")

    return score, reasons, details
