"""New FLAC fake detection scoring system based on machine specifications.

This module implements a 0-100 point scoring system where:
- Higher score = More likely to be fake
- Score >= 80: FAKE_CERTAIN
- Score >= 50: FAKE_PROBABLE
- Score >= 30: DOUTEUX
- Score < 30: AUTHENTIQUE
"""

import logging
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple
import soundfile as sf

logger = logging.getLogger(__name__)


class BitrateMetrics(NamedTuple):
    """Container for bitrate-related metrics."""
    real_bitrate: float
    apparent_bitrate: int
    minimum_expected_bitrate: int
    variance: float


class AudioMetadata(NamedTuple):
    """Container for parsed audio metadata."""
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float


# MP3 Standard Bitrates (kbps) - IMMUTABLE
MP3_STANDARD_BITRATES = [96, 128, 160, 192, 224, 256, 320]

# Bitrate tolerance (kbps)
BITRATE_TOLERANCE = 10

# Score thresholds
SCORE_FAKE_CERTAIN = 80
SCORE_FAKE_PROBABLE = 50
SCORE_DOUTEUX = 30

# Variance threshold for authenticity (kbps)
VARIANCE_THRESHOLD = 100

# High bitrate threshold (kbps)
HIGH_BITRATE_THRESHOLD = 1000

# Coherent bitrate threshold (kbps)
COHERENT_BITRATE_THRESHOLD = 800

# Coherence tolerance (kbps)
COHERENCE_TOLERANCE = 100

# Default number of segments for variance calculation
DEFAULT_VARIANCE_SEGMENTS = 10

# Minimum segments for variance calculation
MIN_VARIANCE_SEGMENTS = 1


def get_cutoff_threshold(sample_rate: int) -> float:
    """Get cutoff frequency threshold based on sample rate.

    Args:
        sample_rate: Sample rate in Hz

    Returns:
        Cutoff threshold in Hz
    """
    thresholds = {
        44100: 20000,
        48000: 22000,
        88200: 40000,
        96000: 44000,
        176400: 80000,
        192000: 88000,
    }

    # If exact match, return it
    if sample_rate in thresholds:
        return thresholds[sample_rate]

    # Otherwise, use 45% of sample rate (Nyquist theorem)
    return sample_rate * 0.45


def get_minimum_expected_bitrate(sample_rate: int, bit_depth: int) -> int:
    """Get minimum expected bitrate for authentic FLAC.

    Args:
        sample_rate: Sample rate in Hz
        bit_depth: Bits per sample

    Returns:
        Minimum expected bitrate in kbps
    """
    # Bitrate minimums according to format
    bitrate_map = {
        (44100, 16): 600,
        (48000, 16): 650,
        (44100, 24): 900,
        (48000, 24): 1000,
        (88200, 24): 1800,
        (96000, 24): 2000,
    }

    key = (sample_rate, bit_depth)
    if key in bitrate_map:
        return bitrate_map[key]

    # Default calculation: sample_rate * bit_depth * channels * compression_ratio / 1000
    # Assuming stereo and ~0.6 compression ratio for FLAC
    return int(sample_rate * bit_depth * 2 * 0.6 / 1000)


def calculate_real_bitrate(filepath: Path, duration: float) -> float:
    """Calculate real bitrate from file size and duration.

    Args:
        filepath: Path to FLAC file
        duration: Duration in seconds

    Returns:
        Real bitrate in kbps
    """
    try:
        file_size_bytes = filepath.stat().st_size
        if duration <= 0:
            return 0

        # Bitrate = (file_size_bytes × 8) / (duration_seconds × 1000)
        bitrate_kbps = (file_size_bytes * 8) / (duration * 1000)
        return bitrate_kbps

    except Exception as e:
        logger.debug(f"Error calculating real bitrate: {e}")
        return 0


def calculate_apparent_bitrate(sample_rate: int, bit_depth: int, channels: int = 2) -> int:
    """Calculate apparent (theoretical) bitrate.

    Args:
        sample_rate: Sample rate in Hz
        bit_depth: Bits per sample
        channels: Number of channels (default 2 for stereo)

    Returns:
        Apparent bitrate in kbps
    """
    # Apparent bitrate = sample_rate × bit_depth × channels / 1000
    return int(sample_rate * bit_depth * channels / 1000)


def calculate_bitrate_variance(
    filepath: Path,
    sample_rate: int,
    num_segments: int = DEFAULT_VARIANCE_SEGMENTS
) -> float:
    """Calculate bitrate variance across multiple segments of the file.

    This helps identify authentic FLAC with variable bitrate vs constant bitrate transcodes.

    Note: This is an approximation. Since FLAC uses variable-length encoding, we cannot
    accurately determine segment boundaries without decoding the entire file. This method
    assumes uniform distribution of data across the file, which is good enough for
    detecting constant vs variable bitrate patterns.

    Args:
        filepath: Path to FLAC file
        sample_rate: Sample rate in Hz
        num_segments: Number of segments to analyze (default: 10)

    Returns:
        Bitrate variance in kbps (0.0 if calculation fails or file too short)
    """
    try:
        info = sf.info(filepath)
        total_duration = info.duration

        # Adjust number of segments if file is too short
        if total_duration < num_segments:
            num_segments = max(MIN_VARIANCE_SEGMENTS, int(total_duration))

        # If only one segment, variance is 0
        if num_segments <= 1:
            return 0.0

        segment_duration = total_duration / num_segments
        file_size = filepath.stat().st_size

        # Calculate approximate bitrate for each segment
        # Note: This assumes uniform data distribution, which is an approximation
        bitrates = []
        for _ in range(num_segments):
            # Approximate segment size (not perfectly accurate but good enough)
            segment_size = file_size / num_segments
            segment_bitrate = (segment_size * 8) / (segment_duration * 1000)
            bitrates.append(segment_bitrate)

        # Calculate standard deviation as variance measure
        if len(bitrates) > 1:
            import numpy as np
            variance = float(np.std(bitrates))
            return variance

        return 0.0

    except Exception as e:
        logger.debug(f"Error calculating bitrate variance: {e}")
        return 0.0


def _apply_rule_1_mp3_bitrate(real_bitrate: float) -> Tuple[int, List[str]]:
    """Apply Rule 1: Constant MP3 Bitrate Detection.

    Detects if the file's real bitrate matches a standard MP3 bitrate (96, 128, 160,
    192, 224, 256, 320 kbps). This is a strong indicator of a transcoded file.

    Scoring:
        +50 points if bitrate matches any standard MP3 bitrate (within tolerance)

    Args:
        real_bitrate: Actual file bitrate in kbps

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    for mp3_bitrate in MP3_STANDARD_BITRATES:
        bitrate_difference = abs(real_bitrate - mp3_bitrate)
        if bitrate_difference <= BITRATE_TOLERANCE:
            score += 50
            reasons.append(f"Constant MP3 bitrate detected: {mp3_bitrate} kbps")
            logger.debug(
                f"RULE 1: +50 points (bitrate {real_bitrate:.1f} ≈ {mp3_bitrate} kbps)"
            )
            break

    return score, reasons


def _apply_rule_2_cutoff(cutoff_freq: float, sample_rate: int) -> Tuple[int, List[str]]:
    """Apply Rule 2: Cutoff Frequency vs Sample Rate.

    Detects if the frequency cutoff is suspiciously low compared to what the sample
    rate should support. Authentic FLAC files should have frequency content up to
    near the Nyquist frequency (sample_rate / 2).

    Scoring:
        +0 to +30 points based on how far below the threshold the cutoff is
        Formula: min((threshold - cutoff) / 200, 30)

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        sample_rate: Sample rate in Hz

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []
    cutoff_threshold = get_cutoff_threshold(sample_rate)

    if cutoff_freq < cutoff_threshold:
        frequency_deficit = cutoff_threshold - cutoff_freq
        cutoff_penalty = min(frequency_deficit / 200, 30)
        score += int(cutoff_penalty)
        reasons.append(
            f"Low cutoff frequency: {cutoff_freq:.0f} Hz "
            f"(threshold: {cutoff_threshold:.0f} Hz, +{cutoff_penalty:.0f} pts)"
        )
        logger.debug(
            f"RULE 2: +{cutoff_penalty:.0f} points "
            f"(cutoff {cutoff_freq:.0f} < threshold {cutoff_threshold:.0f})"
        )

    return score, reasons


def _apply_rule_3_real_vs_expected(
    real_bitrate: float, apparent_bitrate: int, minimum_expected_bitrate: int
) -> Tuple[int, List[str]]:
    """Apply Rule 3: Real Bitrate vs Expected Bitrate.

    Detects files with suspiciously low real bitrate despite high apparent bitrate.
    This catches lossy files (like MP3) that have been upsampled to higher specs.

    Scoring:
        +50 points if real bitrate < 400 kbps AND apparent bitrate > minimum expected

    Args:
        real_bitrate: Actual file bitrate in kbps
        apparent_bitrate: Theoretical bitrate based on sample rate and bit depth
        minimum_expected_bitrate: Minimum bitrate expected for authentic FLAC

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Low real bitrate threshold
    LOW_BITRATE_THRESHOLD = 400

    is_real_too_low = real_bitrate < LOW_BITRATE_THRESHOLD
    is_apparent_high = apparent_bitrate > minimum_expected_bitrate

    if is_real_too_low and is_apparent_high:
        score += 50
        reasons.append(
            f"Real bitrate too low: {real_bitrate:.0f} kbps "
            f"(expected: >{minimum_expected_bitrate} kbps)"
        )
        logger.debug(
            f"RULE 3: +50 points (real {real_bitrate:.0f} < 400 "
            f"and apparent {apparent_bitrate} > minimum {minimum_expected_bitrate})"
        )

    return score, reasons


def _apply_rule_4_24bit(bit_depth: int, real_bitrate: float) -> Tuple[int, List[str]]:
    """Apply Rule 4: 24-bit File Exception.

    Detects 24-bit files with suspiciously low bitrate. Authentic 24-bit FLAC files
    should have significantly higher bitrates than 16-bit files.

    Scoring:
        +30 points if bit depth is 24-bit AND real bitrate < 500 kbps

    Args:
        bit_depth: Bits per sample (16 or 24)
        real_bitrate: Actual file bitrate in kbps

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Minimum expected bitrate for 24-bit files
    MIN_24BIT_BITRATE = 500

    is_24bit = bit_depth == 24
    is_bitrate_too_low = real_bitrate < MIN_24BIT_BITRATE

    if is_24bit and is_bitrate_too_low:
        score += 30
        reasons.append(
            f"Suspicious 24-bit file: real bitrate {real_bitrate:.0f} kbps < {MIN_24BIT_BITRATE} kbps"
        )
        logger.debug(
            f"RULE 4: +30 points (24-bit with bitrate {real_bitrate:.0f} < {MIN_24BIT_BITRATE})"
        )

    return score, reasons


def _apply_rule_5_high_variance(
    real_bitrate: float, bitrate_variance: float
) -> Tuple[int, List[str]]:
    """Apply Rule 5: Avoid False Positives - High Variable Bitrate.

    Reduces score for files with high bitrate and high variance, which are
    characteristics of authentic FLAC files. FLAC uses variable bitrate encoding,
    so authentic files should show variance.

    Scoring:
        -40 points if bitrate > 1000 kbps AND variance > 100 kbps

    Args:
        real_bitrate: Actual file bitrate in kbps
        bitrate_variance: Standard deviation of bitrate across segments

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    is_high_bitrate = real_bitrate > HIGH_BITRATE_THRESHOLD
    is_high_variance = bitrate_variance > VARIANCE_THRESHOLD

    if is_high_bitrate and is_high_variance:
        score -= 40
        reasons.append(
            f"Authentic high variable bitrate: {real_bitrate:.0f} kbps, "
            f"variance {bitrate_variance:.0f} kbps (-40 pts)"
        )
        logger.debug(
            f"RULE 5: -40 points (bitrate {real_bitrate:.0f} > {HIGH_BITRATE_THRESHOLD} "
            f"and variance {bitrate_variance:.0f} > {VARIANCE_THRESHOLD})"
        )

    return score, reasons


def _apply_rule_6_coherence(
    real_bitrate: float, apparent_bitrate: int
) -> Tuple[int, List[str]]:
    """Apply Rule 6: Avoid False Positives - Bitrate Coherence.

    Reduces score for files where real and apparent bitrates are coherent (similar)
    and both are high. This indicates an authentic high-quality FLAC file.

    Scoring:
        -30 points if |real - apparent| < 100 kbps AND real > 800 kbps

    Args:
        real_bitrate: Actual file bitrate in kbps
        apparent_bitrate: Theoretical bitrate based on sample rate and bit depth

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []
    bitrate_diff = abs(real_bitrate - apparent_bitrate)

    is_coherent = bitrate_diff < COHERENCE_TOLERANCE
    is_high_bitrate = real_bitrate > COHERENT_BITRATE_THRESHOLD

    if is_coherent and is_high_bitrate:
        score -= 30
        reasons.append(
            f"Coherent bitrates: real={real_bitrate:.0f} kbps ≈ "
            f"apparent={apparent_bitrate} kbps (-30 pts)"
        )
        logger.debug(
            f"RULE 6: -30 points (coherence {bitrate_diff:.0f} < {COHERENCE_TOLERANCE} "
            f"and bitrate {real_bitrate:.0f} > {COHERENT_BITRATE_THRESHOLD})"
        )

    return score, reasons


def _determine_verdict(score: int) -> Tuple[str, str]:
    """Determine verdict and confidence based on score."""
    if score >= SCORE_FAKE_CERTAIN:
        return "FAKE_CERTAIN", "VERY HIGH"
    elif score >= SCORE_FAKE_PROBABLE:
        return "FAKE_PROBABLE", "HIGH"
    elif score >= SCORE_DOUTEUX:
        return "DOUTEUX", "MEDIUM"
    else:
        return "AUTHENTIQUE", "HIGH"


def _parse_metadata(metadata: Dict) -> AudioMetadata:
    """Parse and validate metadata dictionary.

    Args:
        metadata: Raw metadata dictionary

    Returns:
        AudioMetadata with validated values
    """
    # Extract and validate sample_rate
    sample_rate = metadata.get("sample_rate", 44100)
    if isinstance(sample_rate, str):
        try:
            sample_rate = int(sample_rate)
        except (ValueError, TypeError):
            logger.warning(f"Invalid sample_rate '{sample_rate}', using default 44100")
            sample_rate = 44100

    # Extract and validate bit_depth
    bit_depth = metadata.get("bit_depth", 16)
    if isinstance(bit_depth, str):
        try:
            bit_depth = int(bit_depth)
        except (ValueError, TypeError):
            logger.warning(f"Invalid bit_depth '{bit_depth}', using default 16")
            bit_depth = 16

    # Extract channels and duration
    channels = metadata.get("channels", 2)
    duration = metadata.get("duration", 0)

    return AudioMetadata(
        sample_rate=sample_rate,
        bit_depth=bit_depth,
        channels=channels,
        duration=duration
    )


def _calculate_bitrate_metrics(
    filepath: Path,
    audio_meta: AudioMetadata
) -> BitrateMetrics:
    """Calculate all bitrate-related metrics.

    Args:
        filepath: Path to FLAC file
        audio_meta: Parsed audio metadata

    Returns:
        BitrateMetrics containing all calculated bitrate values
    """
    real_bitrate = calculate_real_bitrate(filepath, audio_meta.duration)
    apparent_bitrate = calculate_apparent_bitrate(
        audio_meta.sample_rate,
        audio_meta.bit_depth,
        audio_meta.channels
    )
    minimum_expected_bitrate = get_minimum_expected_bitrate(
        audio_meta.sample_rate,
        audio_meta.bit_depth
    )
    variance = calculate_bitrate_variance(filepath, audio_meta.sample_rate)

    logger.debug(
        f"Bitrate analysis: real={real_bitrate:.1f} kbps, "
        f"apparent={apparent_bitrate} kbps, "
        f"minimum_expected={minimum_expected_bitrate} kbps, "
        f"variance={variance:.1f} kbps"
    )

    return BitrateMetrics(
        real_bitrate=real_bitrate,
        apparent_bitrate=apparent_bitrate,
        minimum_expected_bitrate=minimum_expected_bitrate,
        variance=variance
    )


def _apply_scoring_rules(
    cutoff_freq: float,
    audio_meta: AudioMetadata,
    bitrate_metrics: BitrateMetrics
) -> Tuple[int, List[str]]:
    """Apply all scoring rules and aggregate results.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        audio_meta: Parsed audio metadata
        bitrate_metrics: Calculated bitrate metrics

    Returns:
        Tuple of (total_score, list_of_reasons)
    """
    total_score = 0
    all_reasons: List[str] = []

    # Apply all 6 rules
    rule_results = [
        _apply_rule_1_mp3_bitrate(bitrate_metrics.real_bitrate),
        _apply_rule_2_cutoff(cutoff_freq, audio_meta.sample_rate),
        _apply_rule_3_real_vs_expected(
            bitrate_metrics.real_bitrate,
            bitrate_metrics.apparent_bitrate,
            bitrate_metrics.minimum_expected_bitrate
        ),
        _apply_rule_4_24bit(audio_meta.bit_depth, bitrate_metrics.real_bitrate),
        _apply_rule_5_high_variance(
            bitrate_metrics.real_bitrate,
            bitrate_metrics.variance
        ),
        _apply_rule_6_coherence(
            bitrate_metrics.real_bitrate,
            bitrate_metrics.apparent_bitrate
        ),
    ]

    # Aggregate scores and reasons
    for rule_score, rule_reasons in rule_results:
        total_score += rule_score
        all_reasons.extend(rule_reasons)

    # Ensure score is non-negative
    total_score = max(0, total_score)

    return total_score, all_reasons


def new_calculate_score(
    cutoff_freq: float,
    metadata: Dict,
    duration_check: Dict,
    filepath: Path
) -> Tuple[int, str, str, str]:
    """Calculate fake detection score using the new 6-rule system.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        metadata: File metadata
        duration_check: Duration check results
        filepath: Path to FLAC file

    Returns:
        Tuple of (score, verdict, confidence, reasons_str)
    """
    # Parse and validate metadata
    audio_meta = _parse_metadata(metadata)

    # Calculate all bitrate metrics
    bitrate_metrics = _calculate_bitrate_metrics(filepath, audio_meta)

    # Apply scoring rules
    score, reasons = _apply_scoring_rules(cutoff_freq, audio_meta, bitrate_metrics)

    # Determine verdict and confidence
    verdict, confidence = _determine_verdict(score)

    # Format reasons for output
    reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"

    logger.info(
        f"Final score: {score}/100 - Verdict: {verdict} - Confidence: {confidence}"
    )

    return score, verdict, confidence, reasons_str
