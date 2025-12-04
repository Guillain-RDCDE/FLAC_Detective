"""Audio quality analysis (clipping, DC offset, corruption)."""

import logging
from pathlib import Path
from typing import Dict, Any

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def detect_clipping(data: np.ndarray, threshold: float = 0.99) -> Dict[str, Any]:
    """Detects audio clipping.

    Clipping occurs when amplitude reaches digital limits
    (±1.0 for floats), causing audible distortion.

    Args:
        data: Audio data (mono or stereo).
        threshold: Detection threshold (0.99 = 99% of max range).

    Returns:
        Dictionary with detection results:
        - has_clipping: True if clipping detected
        - clipping_percentage: Percentage of clipped samples
        - clipped_samples: Number of clipped samples
        - severity: 'none', 'light', 'moderate', 'severe'
    """
    # Convert to 1D if stereo
    if data.ndim > 1:
        data = data.flatten()

    # Count samples hitting the threshold
    clipped_samples = int(np.sum(np.abs(data) >= threshold))
    total_samples = data.size
    clipping_percentage = (clipped_samples / total_samples) * 100

    # Determine severity
    if clipping_percentage == 0:
        severity = "none"
    elif clipping_percentage < 0.01:
        severity = "light"  # < 0.01% = a few peaks
    elif clipping_percentage < 0.1:
        severity = "moderate"  # 0.01-0.1% = noticeable issue
    else:
        severity = "severe"  # > 0.1% = very problematic

    return {
        "has_clipping": clipping_percentage > 0.01,  # Threshold: >0.01%
        "clipping_percentage": round(clipping_percentage, 4),
        "clipped_samples": clipped_samples,
        "severity": severity,
    }


def detect_dc_offset(data: np.ndarray, threshold: float = 0.001) -> Dict[str, Any]:
    """Detects DC offset (waveform offset).

    A DC offset means the waveform is not centered on zero,
    reducing dynamic range and potentially causing clipping.

    Args:
        data: Audio data (mono or stereo).
        threshold: Detection threshold (absolute value).

    Returns:
        Dictionary with detection results:
        - has_dc_offset: True if offset detected
        - dc_offset_value: Average signal value
        - severity: 'none', 'light', 'moderate', 'severe'
    """
    # Calculate average per channel
    if data.ndim > 1:
        # Stereo: calculate average offset of both channels
        dc_offset = float(np.mean([np.mean(data[:, i]) for i in range(data.shape[1])]))
    else:
        # Mono
        dc_offset = float(np.mean(data))

    abs_offset = abs(dc_offset)

    # Determine severity
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
    """Checks if audio file is readable until the end.

    Attempts to read the entire file to detect corruptions
    that would prevent full playback.

    Args:
        filepath: Path to audio file.

    Returns:
        Dictionary with detection results:
        - is_corrupted: True if corruption detected
        - readable: True if file can be read
        - error: Error message if applicable
        - frames_read: Number of frames read (if success)
    """
    try:
        # Try to read the whole file
        data, samplerate = sf.read(filepath, dtype='float32')

        # Check that data was read
        if data.size == 0:
            return {
                "is_corrupted": True,
                "readable": False,
                "error": "No data read from file",
                "frames_read": 0,
            }

        # Check for NaN or Inf
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
    """Detects abnormal silence (leading/trailing).

    Args:
        data: Audio data.
        samplerate: Sampling rate.
        threshold_db: Silence threshold in dB (default -60dB).

    Returns:
        Dictionary with results.
    """
    if data.ndim > 1:
        data = np.mean(np.abs(data), axis=1)
    else:
        data = np.abs(data)

    threshold = 10 ** (threshold_db / 20)

    # Find indices where signal exceeds threshold
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

    # Detection criteria (silence > 2 seconds)
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
    """Checks true bit depth.

    Detects if a 24-bit file is actually 16-bit (padding).

    Args:
        data: Audio data (float32).
        reported_depth: Bit depth reported by metadata.

    Returns:
        Dictionary with results.
    """
    if reported_depth <= 16:
        return {"is_fake_high_res": False, "estimated_depth": reported_depth}

    # For a 24-bit file, check if values correspond to 16-bit
    # In 16-bit, values are multiples of 1/32768
    # Check if data * 32768 is close to an integer

    # Take a sample to be faster
    sample = data[:10000] if data.ndim == 1 else data[:10000, 0]

    # Multiply by 2^15 (32768)
    scaled = sample * 32768.0
    residuals = np.abs(scaled - np.round(scaled))

    # If residuals are very low, it's probably 16-bit
    is_16bit = bool(np.all(residuals < 1e-4))

    return {
        "is_fake_high_res": is_16bit,
        "estimated_depth": 16 if is_16bit else 24,
        "details": "24-bit file contains only 16-bit data" if is_16bit else "True 24-bit"
    }


def detect_upsampling(cutoff_freq: float, samplerate: int) -> Dict[str, Any]:
    """Detects sample rate upsampling.

    Example: 96kHz with cutoff at 22kHz (typical of 44.1kHz).

    Args:
        cutoff_freq: Detected cutoff frequency (Hz).
        samplerate: File sampling rate (Hz).

    Returns:
        Dictionary with results.
    """
    if samplerate <= 48000:
        return {"is_upsampled": False, "suspected_original_rate": samplerate}

    # Theoretical Nyquist
    # nyquist = samplerate / 2 (unused)

    # If 96kHz (Nyquist 48k) but cuts at 22k -> Upsample from 44.1k
    # If cuts at 24k -> Upsample from 48k

    is_upsampled = False
    suspected_rate = samplerate

    if cutoff_freq < 24000:
        # Typical CD cutoff (22.05k) or DAT (24k)
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


def analyze_audio_quality(filepath: Path, metadata: Dict | None = None, cutoff_freq: float = 0.0) -> Dict[str, Any]:
    """Complete audio quality analysis of a file.

    Combines all quality detections into a single analysis.

    Args:
        filepath: Path to audio file.
        metadata: File metadata (optional, for bit depth/samplerate).
        cutoff_freq: Cutoff frequency (optional, for upsampling).

    Returns:
        Dictionary with all quality analysis results.
    """
    results = {}

    # 1. Check corruption first
    corruption_result = detect_corruption(filepath)
    results["corruption"] = corruption_result

    # If file is corrupted, cannot perform other analyses
    if corruption_result["is_corrupted"]:
        return _get_empty_results(results, error_mode=False)

    # 2. Read file for subsequent analyses
    try:
        data, samplerate = sf.read(filepath, dtype='float32')

        # 3. Clipping detection
        results["clipping"] = detect_clipping(data)

        # 4. DC offset detection
        results["dc_offset"] = detect_dc_offset(data)

        # 5. Silence detection (Phase 2)
        results["silence"] = detect_silence(data, samplerate)

        # 6. Fake High-Res detection (Phase 2)
        reported_depth = 16
        if metadata and "bit_depth" in metadata:
            try:
                reported_depth = int(metadata["bit_depth"])
            except (ValueError, TypeError):
                pass
        results["bit_depth"] = detect_true_bit_depth(data, reported_depth)

        # 7. Upsampling detection (Phase 2)
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
    """Generates empty or error results."""
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
