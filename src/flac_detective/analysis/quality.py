"""Audio quality analysis (clipping, DC offset, corruption).

This module provides a comprehensive audio quality analysis framework using
a strategy pattern for different quality detectors.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

import numpy as np
import soundfile as sf

from .new_scoring.audio_loader import is_temporary_decoder_error, sf_blocks

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

    def detect_from_data(self, data: np.ndarray) -> Dict[str, Any]:
        """Detect clipping from an in-memory numpy array."""
        if data.ndim > 1:
            data = data.flatten()

        clipped_samples = int(np.sum(np.abs(data) >= self.threshold))
        total_samples = data.size
        clipping_percentage = (clipped_samples / total_samples) * 100 if total_samples > 0 else 0
        severity = _calculate_clipping_severity(clipping_percentage)

        return {
            "has_clipping": clipping_percentage > 0.01,
            "clipping_percentage": round(clipping_percentage, 4),
            "clipped_samples": clipped_samples,
            "severity": severity,
        }

    def detect(self, filepath: Path, **kwargs) -> Dict[str, Any]:
        """Detect clipping in audio data.

        Args:
            data: Audio data (mono or stereo).

        Returns:
            Dictionary with detection results.
        """
        total_samples = 0
        clipped_samples = 0

        try:
            # Get total frames from file info to avoid iterating just for the count
            info = sf.info(str(filepath))
            total_samples = info.frames

            if total_samples == 0:
                return {  # handle empty file
                    "has_clipping": False,
                    "clipping_percentage": 0.0,
                    "clipped_samples": 0,
                    "severity": "none",
                }

            # Use sf_blocks to iterate
            for chunk in sf_blocks(str(filepath), dtype="float32"):
                clipped_samples += int(np.sum(np.abs(chunk) >= self.threshold))

            clipping_percentage = (
                (clipped_samples / total_samples) * 100 if total_samples > 0 else 0
            )
            severity = _calculate_clipping_severity(clipping_percentage)

            return {
                "has_clipping": clipping_percentage > 0.01,
                "clipping_percentage": round(clipping_percentage, 4),
                "clipped_samples": clipped_samples,
                "severity": severity,
            }
        except Exception as e:
            logger.warning(f"Clipping detection failed for {filepath.name}: {e}")
            return {
                "has_clipping": False,
                "clipping_percentage": 0.0,
                "clipped_samples": 0,
                "severity": "error",
            }


class DCOffsetDetector(QualityDetector):
    """Detects DC offset (waveform offset)."""

    def __init__(self, threshold: float = 0.001):
        """Initialize DC offset detector.

        Args:
            threshold: Detection threshold (absolute value).
        """
        self.threshold = threshold

    def detect_from_data(self, data: np.ndarray) -> Dict[str, Any]:
        """Detect DC offset from an in-memory numpy array."""
        if data.ndim > 1:
            dc_offset = float(np.mean([np.mean(data[:, i]) for i in range(data.shape[1])]))
        else:
            dc_offset = float(np.mean(data))

        abs_offset = abs(dc_offset)
        severity = _calculate_dc_offset_severity(abs_offset, self.threshold)

        return {
            "has_dc_offset": abs_offset >= self.threshold,
            "dc_offset_value": round(dc_offset, 6),
            "severity": severity,
        }

    def detect(self, filepath: Path, **kwargs) -> Dict[str, Any]:
        """Detect DC offset in audio data.

        Args:
            data: Audio data (mono or stereo).

        Returns:
            Dictionary with detection results.
        """
        total_samples = 0
        sum_of_samples = 0.0

        try:
            info = sf.info(str(filepath))
            total_samples = info.frames * info.channels  # sum across all samples in all channels

            if total_samples == 0:
                return {
                    "has_dc_offset": False,
                    "dc_offset_value": 0.0,
                    "severity": "none",
                }

            # Use sf_blocks to iterate
            for chunk in sf_blocks(str(filepath), dtype="float32"):
                sum_of_samples += np.sum(chunk)

            dc_offset = sum_of_samples / total_samples if total_samples > 0 else 0.0
            abs_offset = abs(dc_offset)
            severity = _calculate_dc_offset_severity(abs_offset, self.threshold)

            return {
                "has_dc_offset": abs_offset >= self.threshold,
                "dc_offset_value": round(dc_offset, 6),
                "severity": severity,
            }
        except Exception as e:
            logger.warning(f"DC offset detection failed for {filepath.name}: {e}")
            return {
                "has_dc_offset": False,
                "dc_offset_value": 0.0,
                "severity": "error",
            }


class CorruptionDetector(QualityDetector):
    """Checks if audio file is readable and valid by iterating through it."""

    def detect(self, filepath: Path, **kwargs) -> Dict[str, Any]:
        frames_read = 0
        try:
            # Use sf.info for a quick header check
            info = sf.info(str(filepath))

            # Iterate through all blocks to ensure the whole file is decodable
            for chunk in sf_blocks(str(filepath)):
                frames_read += len(chunk)

            # Check for NaN or Inf in the last chunk as a sample check
            if chunk is not None and (np.any(np.isnan(chunk)) or np.any(np.isinf(chunk))):
                return {
                    "is_corrupted": True,
                    "readable": True,
                    "error": "File contains NaN or Inf values",
                    "frames_read": frames_read,
                }

            if frames_read != info.frames:
                return {
                    "is_corrupted": True,
                    "readable": True,
                    "error": f"Incomplete read: expected {info.frames}, got {frames_read}",
                    "frames_read": frames_read,
                    "partial_analysis": True,
                }

            return {
                "is_corrupted": False,
                "readable": True,
                "error": None,
                "frames_read": frames_read,
            }

        except Exception as e:
            error_msg = str(e)
            is_temp = is_temporary_decoder_error(error_msg)

            # If we read SOME frames before error, it's a partial read (not fully corrupt)
            if frames_read > 0:
                logger.warning(
                    f"Partial read for {filepath.name}: {frames_read} frames read before error: {error_msg}"
                )
                return {
                    "is_corrupted": False,  # NOT corrupted - just incomplete
                    "readable": True,  # We CAN read it partially
                    "error": error_msg,
                    "frames_read": frames_read,
                    "partial_analysis": True,  # Analysis will be partial
                }
            else:
                # Zero frames read - truly corrupted
                logger.error(
                    f"Corruption check failed for {filepath.name}: {error_msg} (0 frames readable)"
                )
                return {
                    "is_corrupted": not is_temp,  # Only mark as corrupted if it's NOT a temporary error
                    "readable": False,
                    "error": error_msg,
                    "frames_read": 0,
                    "partial_analysis": True,
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

    def detect_from_data(self, data: np.ndarray, samplerate: int) -> Dict[str, Any]:
        """Detect silence from an in-memory numpy array."""
        if data.ndim > 1:
            data = np.mean(np.abs(data), axis=1)
        else:
            data = np.abs(data)

        threshold = 10 ** (self.threshold_db / 20)
        non_silent = np.where(data > threshold)[0]

        if len(non_silent) == 0:
            return {
                "has_silence_issue": True,
                "leading_silence_sec": len(data) / samplerate,
                "trailing_silence_sec": 0.0,
                "issue_type": "full_silence",
            }

        start_idx = non_silent[0]
        end_idx = non_silent[-1]

        leading_silence = start_idx / samplerate
        trailing_silence = (len(data) - 1 - end_idx) / samplerate

        has_issue = bool(
            leading_silence > self.silence_threshold_sec
            or trailing_silence > self.silence_threshold_sec
        )
        issue_type = _calculate_silence_issue_type(
            leading_silence, trailing_silence, self.silence_threshold_sec
        )

        return {
            "has_silence_issue": has_issue,
            "leading_silence_sec": round(float(leading_silence), 2),
            "trailing_silence_sec": round(float(trailing_silence), 2),
            "issue_type": issue_type,
        }

    def detect(self, filepath: Path, **kwargs) -> Dict[str, Any]:
        """Detect abnormal silence in audio data.

        Args:
            data: Audio data.
            samplerate: Sampling rate.

        Returns:
            Dictionary with detection results.
        """
        try:
            info = sf.info(str(filepath))
            samplerate = info.samplerate
            total_frames = info.frames

            if total_frames == 0:
                return {  # handle empty file
                    "has_silence_issue": False,
                    "leading_silence_sec": 0.0,
                    "trailing_silence_sec": 0.0,
                    "issue_type": "none",
                }

            threshold = 10 ** (self.threshold_db / 20)
            first_non_silent_frame = None
            last_non_silent_frame = None
            current_frame = 0

            for chunk in sf_blocks(str(filepath), dtype="float32"):
                # Convert to mono for silence detection
                if chunk.ndim > 1:
                    mono_chunk = np.mean(np.abs(chunk), axis=1)
                else:
                    mono_chunk = np.abs(chunk)

                non_silent_indices = np.where(mono_chunk > threshold)[0]

                if non_silent_indices.size > 0:
                    if first_non_silent_frame is None:
                        first_non_silent_frame = current_frame + non_silent_indices[0]
                    last_non_silent_frame = current_frame + non_silent_indices[-1]

                current_frame += len(chunk)

            if first_non_silent_frame is None:  # Entire file is silent
                return {
                    "has_silence_issue": True,
                    "leading_silence_sec": total_frames / samplerate,
                    "trailing_silence_sec": 0.0,
                    "issue_type": "full_silence",
                }

            leading_silence = first_non_silent_frame / samplerate
            trailing_silence = (total_frames - 1 - last_non_silent_frame) / samplerate

            has_issue = bool(
                leading_silence > self.silence_threshold_sec
                or trailing_silence > self.silence_threshold_sec
            )
            issue_type = _calculate_silence_issue_type(
                leading_silence, trailing_silence, self.silence_threshold_sec
            )

            return {
                "has_silence_issue": has_issue,
                "leading_silence_sec": round(float(leading_silence), 2),
                "trailing_silence_sec": round(float(trailing_silence), 2),
                "issue_type": issue_type,
            }

        except Exception as e:
            logger.warning(f"Silence detection failed for {filepath.name}: {e}")
            return {
                "has_silence_issue": False,
                "leading_silence_sec": 0.0,
                "trailing_silence_sec": 0.0,
                "issue_type": "error",
            }


class BitDepthDetector(QualityDetector):
    """Checks true bit depth (detects fake high-res)."""

    def detect_from_data(self, data: np.ndarray, reported_depth: int) -> Dict[str, Any]:
        """Detect true bit depth from an in-memory numpy array."""
        if reported_depth <= 16:
            return {"is_fake_high_res": False, "estimated_depth": reported_depth}

        sample = data[:10000] if data.ndim == 1 else data[:10000, 0]
        scaled = sample * 32768.0
        residuals = np.abs(scaled - np.round(scaled))
        is_16bit = bool(np.all(residuals < 1e-4))

        return {
            "is_fake_high_res": is_16bit,
            "estimated_depth": 16 if is_16bit else 24,
            "details": "24-bit file contains only 16-bit data" if is_16bit else "True 24-bit",
        }

    def detect(self, filepath: Path, reported_depth: int, **kwargs) -> Dict[str, Any]:
        """Detect true bit depth.

        Args:
            data: Audio data (float32).
            reported_depth: Bit depth reported by metadata.

        Returns:
            Dictionary with detection results.
        """
        if reported_depth <= 16:
            return {"is_fake_high_res": False, "estimated_depth": reported_depth}

        try:
            # Read only the first chunk for analysis
            first_chunk = next(sf_blocks(str(filepath), dtype="float32", blocksize=10000), None)

            if first_chunk is None:
                # Handle empty or unreadable file
                return {"is_fake_high_res": False, "estimated_depth": reported_depth}

            # For a 24-bit file, check if values correspond to 16-bit
            sample = first_chunk if first_chunk.ndim == 1 else first_chunk[:, 0]

            scaled = sample * 32768.0
            residuals = np.abs(scaled - np.round(scaled))

            is_16bit = bool(np.all(residuals < 1e-4))

            return {
                "is_fake_high_res": is_16bit,
                "estimated_depth": 16 if is_16bit else 24,
                "details": "24-bit file contains only 16-bit data" if is_16bit else "True 24-bit",
            }
        except Exception as e:
            logger.warning(f"Bit depth detection failed for {filepath.name}: {e}")
            return {
                "is_fake_high_res": False,
                "estimated_depth": reported_depth,
                "details": "Analysis failed",
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
            "cutoff_freq": cutoff_freq,
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

    def analyze(
        self,
        filepath: Path,
        metadata: Dict | None = None,
        cutoff_freq: float = 0.0,
        cache=None,
    ) -> Dict[str, Any]:
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
        # If cache is provided and has data, skip corruption check (cache already loaded data)
        if cache is not None:
            logger.debug(f"Skipping corruption check for {filepath.name} - using cache")
            corruption_result = {
                "is_corrupted": False,
                "readable": True,
                "error": None,
                "frames_read": 0,  # Unknown but we have cache
                "partial_analysis": getattr(cache, "_is_partial", False),
            }
        else:
            corruption_result = self.detectors["corruption"].detect(filepath=filepath)

        results["corruption"] = corruption_result

        # If file is corrupted, cannot perform other analyses
        if corruption_result["is_corrupted"]:
            return self._get_empty_results(results, error_mode=False)

        # If partial_analysis but cache is provided, continue with partial data
        if corruption_result.get("partial_analysis") and cache is None:
            logger.warning(
                f"Cannot perform full quality analysis for {filepath.name} due to temporary read errors."
            )
            return self._get_empty_results(
                results, error_mode=True, error_msg="Partial analysis due to read errors"
            )
        elif corruption_result.get("partial_analysis") and cache is not None:
            logger.info(f"Proceeding with partial data analysis for {filepath.name} using cache")

        try:
            # No longer reading the full file here.
            # Detectors will read the file themselves in a memory-efficient way.

            # 3. Clipping detection
            results["clipping"] = self.detectors["clipping"].detect(filepath=filepath)

            # 4. DC offset detection
            results["dc_offset"] = self.detectors["dc_offset"].detect(filepath=filepath)

            # 5. Silence detection
            results["silence"] = self.detectors["silence"].detect(filepath=filepath)

            # 6. Fake High-Res detection
            reported_depth = self._get_reported_depth(metadata)
            results["bit_depth"] = self.detectors["bit_depth"].detect(
                filepath=filepath, reported_depth=reported_depth
            )

            # 7. Upsampling detection - this one doesn't need audio data, just metadata
            # It needs the sample rate. Let's get it from sf.info to be safe.
            try:
                info = sf.info(str(filepath))
                reported_rate = info.samplerate
            except Exception:
                reported_rate = self._get_reported_rate(metadata, 0)

            results["upsampling"] = self.detectors["upsampling"].detect(
                cutoff_freq=cutoff_freq, samplerate=reported_rate
            )

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

    def _get_empty_results(
        self, results: Dict, error_mode: bool = False, error_msg: str = ""
    ) -> Dict:
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
            "clipping": {
                "has_clipping": False,
                "clipping_percentage": 0.0,
                "severity": severity,
            },
            "dc_offset": {
                "has_dc_offset": False,
                "dc_offset_value": 0.0,
                "severity": severity,
            },
            "silence": {"has_silence_issue": False, "issue_type": severity},
            "bit_depth": {"is_fake_high_res": False, "estimated_depth": 0},
            "upsampling": {"is_upsampled": False, "suspected_original_rate": 0},
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


def analyze_audio_quality(
    filepath: Path,
    metadata: Dict | None = None,
    cutoff_freq: float = 0.0,
    cache=None,
) -> Dict[str, Any]:
    """Complete audio quality analysis (backward compatibility wrapper).

    PHASE 1 OPTIMIZATION: Supports AudioCache parameter.
    """
    analyzer = AudioQualityAnalyzer()
    return analyzer.analyze(
        filepath=filepath, metadata=metadata, cutoff_freq=cutoff_freq, cache=cache
    )


def detect_clipping(data: np.ndarray, threshold: float = 0.99) -> Dict[str, Any]:
    """Detects audio clipping (backward compatibility wrapper)."""
    detector = ClippingDetector(threshold=threshold)
    return detector.detect_from_data(data=data)


def detect_dc_offset(data: np.ndarray, threshold: float = 0.001) -> Dict[str, Any]:
    """Detects DC offset (backward compatibility wrapper)."""
    detector = DCOffsetDetector(threshold=threshold)
    return detector.detect_from_data(data=data)


def detect_corruption(filepath: Path) -> Dict[str, Any]:
    """Checks if audio file is readable (backward compatibility wrapper)."""
    detector = CorruptionDetector()
    return detector.detect(filepath=filepath)


def detect_silence(
    data: np.ndarray, samplerate: int, threshold_db: float = -60.0
) -> Dict[str, Any]:
    """Detects abnormal silence (backward compatibility wrapper)."""
    detector = SilenceDetector(threshold_db=threshold_db)
    return detector.detect_from_data(data=data, samplerate=samplerate)


def detect_true_bit_depth(data: np.ndarray, reported_depth: int) -> Dict[str, Any]:
    """Checks true bit depth (backward compatibility wrapper)."""
    detector = BitDepthDetector()
    return detector.detect_from_data(data=data, reported_depth=reported_depth)


def detect_upsampling(cutoff_freq: float, samplerate: int) -> Dict[str, Any]:
    """Detects sample rate upsampling (backward compatibility wrapper)."""
    detector = UpsamplingDetector()
    return detector.detect(cutoff_freq=cutoff_freq, samplerate=samplerate)
