"""Audio quality analysis (clipping, DC offset, corruption).

This module provides a comprehensive audio quality analysis framework using
a strategy pattern for different quality detectors.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

import numpy as np
import soundfile as sf

from .new_scoring.audio_loader import load_audio_with_retry, is_temporary_decoder_error

logger = logging.getLogger(__name__)


# ============================================================================
# SEVERITY CALCULATION HELPERS
# ============================================================================

def _calculate_clipping_severity(percentage: float) -> str:
    """Calculate clipping severity based on percentage.

    Args:
        percentage: Percentage of clipped samples.

    Returns:
        Severity level: 'none', 'light', 'moderate', 'severe'.
    """
    if percentage == 0:
        return "none"
    elif percentage < 0.01:
        return "light"  # < 0.01% = a few peaks
    elif percentage < 0.1:
        return "moderate"  # 0.01-0.1% = noticeable issue
    else:
        return "severe"  # > 0.1% = very problematic


def _calculate_dc_offset_severity(abs_offset: float, threshold: float) -> str:
    """Calculate DC offset severity based on absolute offset.

    Args:
        abs_offset: Absolute DC offset value.
        threshold: Detection threshold.

    Returns:
        Severity level: 'none', 'light', 'moderate', 'severe'.
    """
    if abs_offset < threshold:
        return "none"
    elif abs_offset < 0.01:
        return "light"  # < 1%
    elif abs_offset < 0.05:
        return "moderate"  # 1-5%
    else:
        return "severe"  # > 5%


def _calculate_silence_issue_type(leading: float, trailing: float, threshold: float = 2.0) -> str:
    """Calculate silence issue type.

    Args:
        leading: Leading silence duration in seconds.
        trailing: Trailing silence duration in seconds.
        threshold: Threshold for issue detection (default 2.0 seconds).

    Returns:
        Issue type: 'none', 'leading', 'trailing', 'both', 'full_silence'.
    """
    if leading > threshold and trailing > threshold:
        return "both"
    elif leading > threshold:
        return "leading"
    elif trailing > threshold:
        return "trailing"
    else:
        return "none"


# ============================================================================
# ABSTRACT BASE CLASS FOR QUALITY DETECTORS
# ============================================================================

class QualityDetector(ABC):
    """Abstract base class for quality detectors."""

    @abstractmethod
    def detect(self, **kwargs) -> Dict[str, Any]:
        """Run the quality detection.

        Returns:
            Dictionary with detection results.
        """
        pass

    @property
    def name(self) -> str:
        """Get detector name."""
        return self.__class__.__name__


# ============================================================================
# CONCRETE DETECTOR IMPLEMENTATIONS
# ============================================================================

class ClippingDetector(QualityDetector):
    """Detects audio clipping."""

    def __init__(self, threshold: float = 0.99):
        """Initialize clipping detector.

        Args:
            threshold: Detection threshold (0.99 = 99% of max range).
        """
        self.threshold = threshold

    def detect(self, data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Detect clipping in audio data.

        Args:
            data: Audio data (mono or stereo).

        Returns:
            Dictionary with detection results.
        """
        # Convert to 1D if stereo
        if data.ndim > 1:
            data = data.flatten()

        # Count samples hitting the threshold
        clipped_samples = int(np.sum(np.abs(data) >= self.threshold))
        total_samples = data.size
        clipping_percentage = (clipped_samples / total_samples) * 100

        severity = _calculate_clipping_severity(clipping_percentage)

        return {
            "has_clipping": clipping_percentage > 0.01,  # Threshold: >0.01%
            "clipping_percentage": round(clipping_percentage, 4),
            "clipped_samples": clipped_samples,
            "severity": severity,
        }


class DCOffsetDetector(QualityDetector):
    """Detects DC offset (waveform offset)."""

    def __init__(self, threshold: float = 0.001):
        """Initialize DC offset detector.

        Args:
            threshold: Detection threshold (absolute value).
        """
        self.threshold = threshold

    def detect(self, data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Detect DC offset in audio data.

        Args:
            data: Audio data (mono or stereo).

        Returns:
            Dictionary with detection results.
        """
        # Calculate average per channel
        if data.ndim > 1:
            # Stereo: calculate average offset of both channels
            dc_offset = float(np.mean([np.mean(data[:, i]) for i in range(data.shape[1])]))
        else:
            # Mono
            dc_offset = float(np.mean(data))

        abs_offset = abs(dc_offset)
        severity = _calculate_dc_offset_severity(abs_offset, self.threshold)

        return {
            "has_dc_offset": abs_offset >= self.threshold,
            "dc_offset_value": round(dc_offset, 6),
            "severity": severity,
        }


class CorruptionDetector(QualityDetector):
    """Checks if audio file is readable and valid."""

    def detect(self, filepath: Path, **kwargs) -> Dict[str, Any]:
        """Detect corruption in audio file.

        Args:
            filepath: Path to audio file.

        Returns:
            Dictionary with detection results.
        """
        try:
            # Try to read the file with retry mechanism
            data, samplerate = load_audio_with_retry(str(filepath))
            
            # If loading failed after retries, check if it was a temporary error
            if data is None or samplerate is None:
                logger.warning(
                    f"Could not load {filepath.name} after retries. "
                    f"Not marking as corrupted (may be temporary decoder issue)."
                )
                return {
                    "is_corrupted": False,
                    "readable": True,
                    "error": "Temporary decoder error (not marked as corrupted)",
                    "frames_read": 0,
                    "partial_analysis": True,
                }

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
            error_msg = str(e)
            
            # Check if this is a temporary decoder error
            if is_temporary_decoder_error(error_msg):
                logger.warning(
                    f"Temporary decoder error in {filepath.name}: {error_msg}. "
                    f"Not marking as corrupted."
                )
                return {
                    "is_corrupted": False,
                    "readable": True,
                    "error": f"Temporary decoder error: {error_msg}",
                    "frames_read": 0,
                    "partial_analysis": True,
                }
            else:
                # Real corruption
                logger.debug(f"Corruption detected in {filepath.name}: {e}")
                return {
                    "is_corrupted": True,
                    "readable": False,
                    "error": error_msg,
                    "frames_read": 0,
                }


class SilenceDetector(QualityDetector):
    """Detects abnormal silence (leading/trailing)."""

    def __init__(self, threshold_db: float = -60.0, silence_threshold_sec: float = 2.0):
        """Initialize silence detector.

        Args:
            threshold_db: Silence threshold in dB (default -60dB).
            silence_threshold_sec: Threshold for issue detection (default 2.0 seconds).
        """
        self.threshold_db = threshold_db
        self.silence_threshold_sec = silence_threshold_sec

    def detect(self, data: np.ndarray, samplerate: int, **kwargs) -> Dict[str, Any]:
        """Detect abnormal silence in audio data.

        Args:
            data: Audio data.
            samplerate: Sampling rate.

        Returns:
            Dictionary with detection results.
        """
        if data.ndim > 1:
            data = np.mean(np.abs(data), axis=1)
        else:
            data = np.abs(data)

        threshold = 10 ** (self.threshold_db / 20)

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

        # Detection criteria
        has_issue = bool(leading_silence > self.silence_threshold_sec or trailing_silence > self.silence_threshold_sec)
        issue_type = _calculate_silence_issue_type(leading_silence, trailing_silence, self.silence_threshold_sec)

        return {
            "has_silence_issue": has_issue,
            "leading_silence_sec": round(float(leading_silence), 2),
            "trailing_silence_sec": round(float(trailing_silence), 2),
            "issue_type": issue_type
        }


class BitDepthDetector(QualityDetector):
    """Checks true bit depth (detects fake high-res)."""

    def detect(self, data: np.ndarray, reported_depth: int, **kwargs) -> Dict[str, Any]:
        """Detect true bit depth.

        Args:
            data: Audio data (float32).
            reported_depth: Bit depth reported by metadata.

        Returns:
            Dictionary with detection results.
        """
        if reported_depth <= 16:
            return {"is_fake_high_res": False, "estimated_depth": reported_depth}

        # For a 24-bit file, check if values correspond to 16-bit
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


class UpsamplingDetector(QualityDetector):
    """Detects sample rate upsampling."""

    def detect(self, cutoff_freq: float, samplerate: int, **kwargs) -> Dict[str, Any]:
        """Detect sample rate upsampling.

        Args:
            cutoff_freq: Detected cutoff frequency (Hz).
            samplerate: File sampling rate (Hz).

        Returns:
            Dictionary with detection results.
        """
        if samplerate <= 48000:
            return {"is_upsampled": False, "suspected_original_rate": samplerate}

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


# ============================================================================
# QUALITY ANALYZER (ORCHESTRATOR)
# ============================================================================

class AudioQualityAnalyzer:
    """Orchestrates all quality detectors."""

    def __init__(self):
        """Initialize quality analyzer with all detectors."""
        self.detectors: Dict[str, QualityDetector] = {
            "corruption": CorruptionDetector(),
            "clipping": ClippingDetector(),
            "dc_offset": DCOffsetDetector(),
            "silence": SilenceDetector(),
            "bit_depth": BitDepthDetector(),
            "upsampling": UpsamplingDetector(),
        }

    def analyze(self, filepath: Path, metadata: Dict | None = None, cutoff_freq: float = 0.0, cache=None) -> Dict[str, Any]:
        """Complete audio quality analysis of a file.

        PHASE 1 OPTIMIZATION: Uses AudioCache to avoid re-reading the file.

        Args:
            filepath: Path to audio file.
            metadata: File metadata (optional, for bit depth/samplerate).
            cutoff_freq: Cutoff frequency (optional, for upsampling).
            cache: Optional AudioCache instance for optimization.

        Returns:
            Dictionary with all quality analysis results.
        """
        results = {}

        # 1. Check corruption first
        corruption_result = self.detectors["corruption"].detect(filepath=filepath)
        results["corruption"] = corruption_result

        # If file is corrupted, cannot perform other analyses
        if corruption_result["is_corrupted"]:
            return self._get_empty_results(results, error_mode=False)

        # 2. Read file for subsequent analyses
        try:
            # OPTIMIZATION: Use cache if provided, otherwise read directly
            if cache is not None:
                logger.debug("⚡ CACHE: Loading full audio via cache for quality analysis")
                data, samplerate = cache.get_full_audio()
                # Convert to float32 and handle always_2d format
                data = data.astype(np.float32)
            else:
                # Fallback to direct read
                data, samplerate = sf.read(filepath, dtype='float32')

            # 3. Clipping detection
            results["clipping"] = self.detectors["clipping"].detect(data=data)

            # 4. DC offset detection
            results["dc_offset"] = self.detectors["dc_offset"].detect(data=data)

            # 5. Silence detection
            results["silence"] = self.detectors["silence"].detect(data=data, samplerate=samplerate)

            # 6. Fake High-Res detection
            reported_depth = self._get_reported_depth(metadata)
            results["bit_depth"] = self.detectors["bit_depth"].detect(data=data, reported_depth=reported_depth)

            # 7. Upsampling detection
            reported_rate = self._get_reported_rate(metadata, samplerate)
            results["upsampling"] = self.detectors["upsampling"].detect(cutoff_freq=cutoff_freq, samplerate=reported_rate)

        except Exception as e:
            logger.error(f"Error analyzing quality for {filepath.name}: {e}")
            return self._get_empty_results(results, error_mode=True, error_msg=str(e))

        return results

    def _get_reported_depth(self, metadata: Dict | None) -> int:
        """Extract reported bit depth from metadata.

        Args:
            metadata: File metadata.

        Returns:
            Reported bit depth (default 16).
        """
        if metadata and "bit_depth" in metadata:
            try:
                return int(metadata["bit_depth"])
            except (ValueError, TypeError):
                pass
        return 16

    def _get_reported_rate(self, metadata: Dict | None, default_rate: int) -> int:
        """Extract reported sample rate from metadata.

        Args:
            metadata: File metadata.
            default_rate: Default sample rate.

        Returns:
            Reported sample rate.
        """
        if metadata and "sample_rate" in metadata:
            try:
                return int(metadata["sample_rate"])
            except (ValueError, TypeError):
                pass
        return default_rate

    def _get_empty_results(self, results: Dict, error_mode: bool = False, error_msg: str = "") -> Dict:
        """Generate empty or error results.

        Args:
            results: Existing results dictionary.
            error_mode: Whether this is an error case.
            error_msg: Error message if applicable.

        Returns:
            Results dictionary with defaults.
        """
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


# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================

def detect_clipping(data: np.ndarray, threshold: float = 0.99) -> Dict[str, Any]:
    """Detects audio clipping (backward compatibility wrapper)."""
    detector = ClippingDetector(threshold=threshold)
    return detector.detect(data=data)


def detect_dc_offset(data: np.ndarray, threshold: float = 0.001) -> Dict[str, Any]:
    """Detects DC offset (backward compatibility wrapper)."""
    detector = DCOffsetDetector(threshold=threshold)
    return detector.detect(data=data)


def detect_corruption(filepath: Path) -> Dict[str, Any]:
    """Checks if audio file is readable (backward compatibility wrapper)."""
    detector = CorruptionDetector()
    return detector.detect(filepath=filepath)


def detect_silence(data: np.ndarray, samplerate: int, threshold_db: float = -60.0) -> Dict[str, Any]:
    """Detects abnormal silence (backward compatibility wrapper)."""
    detector = SilenceDetector(threshold_db=threshold_db)
    return detector.detect(data=data, samplerate=samplerate)


def detect_true_bit_depth(data: np.ndarray, reported_depth: int) -> Dict[str, Any]:
    """Checks true bit depth (backward compatibility wrapper)."""
    detector = BitDepthDetector()
    return detector.detect(data=data, reported_depth=reported_depth)


def detect_upsampling(cutoff_freq: float, samplerate: int) -> Dict[str, Any]:
    """Detects sample rate upsampling (backward compatibility wrapper)."""
    detector = UpsamplingDetector()
    return detector.detect(cutoff_freq=cutoff_freq, samplerate=samplerate)


def analyze_audio_quality(filepath: Path, metadata: Dict | None = None, cutoff_freq: float = 0.0, cache=None) -> Dict[str, Any]:
    """Complete audio quality analysis (backward compatibility wrapper).
    
    PHASE 1 OPTIMIZATION: Supports AudioCache parameter.
    """
    analyzer = AudioQualityAnalyzer()
    return analyzer.analyze(filepath=filepath, metadata=metadata, cutoff_freq=cutoff_freq, cache=cache)
