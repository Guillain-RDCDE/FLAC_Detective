"""New FLAC fake detection scoring system based on machine specifications.

This module implements a 0-100 point scoring system where:
- Higher score = More likely to be fake
- Score >= 80: FAKE_CERTAIN
- Score >= 50: FAKE_PROBABLE
- Score >= 30: DOUTEUX
- Score < 30: AUTHENTIQUE

Range: 0-150 points
"""

import logging
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
import soundfile as sf

logger = logging.getLogger(__name__)


class BitrateMetrics(NamedTuple):
    """Container for bitrate-related metrics."""
    real_bitrate: float
    apparent_bitrate: int
    variance: float


class AudioMetadata(NamedTuple):
    """Container for parsed audio metadata."""
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float


# MP3 Standard Bitrates (kbps) - IMMUTABLE
MP3_STANDARD_BITRATES = [96, 128, 160, 192, 224, 256, 320]

# MP3 Bitrate Signatures (Frequency Ranges)
# Format: (bitrate_kbps, min_freq, max_freq)
# Ranges are slightly overlapping or contiguous to catch edge cases
MP3_SIGNATURES = [
    (320, 19500, 21500),  # 320 kbps: ~19.5-21.5 kHz (often 20.5k)
    (256, 18500, 19500),  # 256 kbps: ~18.5-19.5 kHz
    (224, 17500, 18500),  # 224 kbps: ~17.5-18.5 kHz
    (192, 16500, 17500),  # 192 kbps: ~16.5-17.5 kHz
    (160, 15500, 16500),  # 160 kbps: ~15.5-16.5 kHz
    (128, 10000, 15500),  # 128 kbps or lower: < 15.5 kHz
]

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

# Apparent bitrate threshold for Rule 3 (kbps)
SEUIL_BITRATE_APPARENT_ELEVE = 600

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


def estimate_mp3_bitrate(cutoff_freq: float) -> int:
    """Estimates the original MP3 bitrate based on cutoff frequency.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz.

    Returns:
        Estimated bitrate in kbps, or 0 if no match found.
    """
    for bitrate, min_f, max_f in MP3_SIGNATURES:
        if min_f <= cutoff_freq < max_f:
            return bitrate
    return 0





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
            logger.warning(f"Invalid duration {duration}s for {filepath.name}, cannot calculate bitrate")
            return 0

        # Bitrate = (file_size_bytes × 8) / (duration_seconds × 1000)
        bitrate_kbps = (file_size_bytes * 8) / (duration * 1000)
        logger.info(f"Real bitrate calculated: {bitrate_kbps:.1f} kbps (size={file_size_bytes} bytes, duration={duration:.1f}s)")
        return bitrate_kbps

    except Exception as e:
        logger.error(f"Error calculating real bitrate: {e}")
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


def _apply_rule_1_mp3_bitrate(cutoff_freq: float) -> Tuple[Tuple[int, List[str]], Optional[int]]:
    """Apply Rule 1: Constant MP3 Bitrate Detection (Spectral Estimation).

    Detects if the file's spectral cutoff matches a standard MP3 bitrate signature.
    This allows detecting MP3s recompressed as FLACs (Fake FLACs).

    Scoring:
        +50 points if estimated spectral bitrate matches a standard MP3 bitrate

    Args:
        cutoff_freq: Detected cutoff frequency in Hz

    Returns:
        Tuple of ((score_delta, list_of_reasons), estimated_bitrate)
    """
    score = 0
    reasons: List[str] = []
    
    # Safety check: If cutoff > 21 kHz, it's likely an authentic high-quality FLAC
    # MP3s never have cutoffs above 21 kHz (even 320 kbps tops out around 20.5 kHz)
    HIGH_QUALITY_CUTOFF_THRESHOLD = 21000
    
    if cutoff_freq > HIGH_QUALITY_CUTOFF_THRESHOLD:
        logger.debug(
            f"RULE 1: Skipped (cutoff {cutoff_freq:.0f} Hz > {HIGH_QUALITY_CUTOFF_THRESHOLD} Hz, likely authentic FLAC)"
        )
        return (score, reasons), None

    estimated_bitrate = estimate_mp3_bitrate(cutoff_freq)

    if estimated_bitrate in MP3_STANDARD_BITRATES:
        score += 50
        reasons.append(f"Constant MP3 bitrate detected (Spectral): {estimated_bitrate} kbps")
        logger.info(
            f"RULE 1: +50 points (cutoff {cutoff_freq:.0f} Hz ~= {estimated_bitrate} kbps MP3)"
        )

    return (score, reasons), estimated_bitrate


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
            f"R2: Cutoff {cutoff_freq:.0f} Hz < {cutoff_threshold:.0f} Hz (+{cutoff_penalty:.0f}pts)"
        )
        logger.debug(
            f"RULE 2: +{cutoff_penalty:.0f} points "
            f"(cutoff {cutoff_freq:.0f} < threshold {cutoff_threshold:.0f})"
        )

    return score, reasons


def _apply_rule_3_source_vs_container(
    mp3_bitrate_detected: Optional[int], bitrate_conteneur: float
) -> Tuple[int, List[str]]:
    """Apply Rule 3: Source Bitrate vs Container Bitrate.

    Detects files where the detected MP3 source bitrate is much lower than
    the FLAC container bitrate, proving it's a converted MP3.

    Scoring:
        +50 points if mp3_bitrate_detected exists AND bitrate_conteneur > 600 kbps

    Args:
        mp3_bitrate_detected: Detected MP3 bitrate from spectral analysis (or None)
        bitrate_conteneur: Physical bitrate of the FLAC file in kbps

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Container bitrate threshold
    CONTAINER_THRESHOLD = 600

    if mp3_bitrate_detected is not None and bitrate_conteneur > CONTAINER_THRESHOLD:
        score += 50
        reasons.append(
            f"R3: Source {mp3_bitrate_detected} kbps vs conteneur {bitrate_conteneur:.0f} kbps"
        )
        logger.info(
            f"RULE 3: +50 points (source {mp3_bitrate_detected} kbps vs container {bitrate_conteneur:.0f} kbps)"
        )

    return score, reasons


def _apply_rule_4_24bit_suspect(
    bit_depth: int, mp3_bitrate_detected: Optional[int]
) -> Tuple[int, List[str]]:
    """Apply Rule 4: 24-bit Suspicious Files.

    Detects 24-bit files with suspiciously low MP3 source bitrate.
    Authentic 24-bit FLAC files should have high bitrates (> 500 kbps).

    Scoring:
        +30 points if bit depth is 24-bit AND mp3_bitrate_detected exists AND < 500 kbps

    Args:
        bit_depth: Bits per sample (16 or 24)
        mp3_bitrate_detected: Detected MP3 bitrate from spectral analysis (or None)

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # Minimum expected bitrate for 24-bit files
    MIN_24BIT_BITRATE = 500

    is_24bit = bit_depth == 24

    if is_24bit and mp3_bitrate_detected is not None and mp3_bitrate_detected < MIN_24BIT_BITRATE:
        score += 30
        reasons.append(
            f"R4: 24-bit avec bitrate source {mp3_bitrate_detected} kbps (upscale suspect)"
        )
        logger.info(
            f"RULE 4: +30 points (24-bit with MP3 source {mp3_bitrate_detected} kbps < {MIN_24BIT_BITRATE})"
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


def _apply_rule_6_variable_bitrate_protection(
    mp3_bitrate_detected: Optional[int], bitrate_conteneur: float
) -> Tuple[int, List[str]]:
    """Apply Rule 6: Avoid False Positives - High Variable Bitrate Protection.

    Protects authentic high-quality FLAC files with variable bitrate from being
    marked as suspicious due to slightly low cutoff (old recording equipment).

    Scoring:
        -30 points if mp3_bitrate_detected is None AND bitrate_conteneur > 800 kbps

    Args:
        mp3_bitrate_detected: Detected MP3 bitrate from spectral analysis (or None)
        bitrate_conteneur: Physical bitrate of the FLAC file in kbps

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons = []

    # High bitrate threshold for authentic FLAC protection
    HIGH_BITRATE_THRESHOLD = 800

    is_variable_bitrate = mp3_bitrate_detected is None
    is_high_bitrate = bitrate_conteneur > HIGH_BITRATE_THRESHOLD

    if is_variable_bitrate and is_high_bitrate:
        score -= 30
        reasons.append(
            f"R6: Bitrate variable élevé ({bitrate_conteneur:.0f} kbps) → Authentique (-30pts)"
        )
        logger.info(
            f"RULE 6: -30 points (variable bitrate with high container {bitrate_conteneur:.0f} kbps)"
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
    variance = calculate_bitrate_variance(filepath, audio_meta.sample_rate)

    logger.info(
        f"Bitrate analysis: real={real_bitrate:.1f} kbps, "
        f"apparent={apparent_bitrate} kbps, "
        f"variance={variance:.1f} kbps"
    )

    return BitrateMetrics(
        real_bitrate=real_bitrate,
        apparent_bitrate=apparent_bitrate,
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

    # Apply Rule 1 first to get the detected MP3 bitrate
    rule1_result, mp3_bitrate_detected = _apply_rule_1_mp3_bitrate(cutoff_freq)
    
    # Apply all 6 rules
    rule_results = [
        rule1_result,
        _apply_rule_2_cutoff(cutoff_freq, audio_meta.sample_rate),
        _apply_rule_3_source_vs_container(
            mp3_bitrate_detected,
            bitrate_metrics.real_bitrate
        ),
        _apply_rule_4_24bit_suspect(audio_meta.bit_depth, mp3_bitrate_detected),
        _apply_rule_5_high_variance(
            bitrate_metrics.real_bitrate,
            bitrate_metrics.variance
        ),
        _apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected,
            bitrate_metrics.real_bitrate
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
    logger.info(f"\n{'='*60}")
    logger.info(f"Starting score calculation for: {filepath.name}")
    logger.info(f"Metadata received: {metadata}")
    logger.info(f"Cutoff frequency: {cutoff_freq:.1f} Hz")
    logger.info(f"{'='*60}")
    
    # Parse and validate metadata
    audio_meta = _parse_metadata(metadata)
    
    # Validate duration
    if audio_meta.duration <= 0:
        logger.warning(f"Duration is {audio_meta.duration}, attempting to read from file...")
        try:
            import soundfile as sf
            info = sf.info(filepath)
            audio_meta = AudioMetadata(
                sample_rate=audio_meta.sample_rate,
                bit_depth=audio_meta.bit_depth,
                channels=audio_meta.channels,
                duration=info.duration
            )
            logger.info(f"Duration corrected to {info.duration:.1f}s from soundfile")
        except Exception as e:
            logger.error(f"Could not read duration from file: {e}")

    # Calculate all bitrate metrics
    bitrate_metrics = _calculate_bitrate_metrics(filepath, audio_meta)

    # Apply scoring rules
    score, reasons = _apply_scoring_rules(cutoff_freq, audio_meta, bitrate_metrics)

    # Determine verdict and confidence
    verdict, confidence = _determine_verdict(score)

    # Format reasons for output
    reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"

    logger.info(
        f"Final score: {score}/150 - Verdict: {verdict} - Confidence: {confidence}"
    )
    logger.info(f"Reasons: {reasons_str}")
    logger.info(f"{'='*60}\n")

    return score, verdict, confidence, reasons_str
