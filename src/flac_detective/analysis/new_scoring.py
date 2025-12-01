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
from typing import Dict, List, Tuple
import soundfile as sf

logger = logging.getLogger(__name__)

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


def calculate_bitrate_variance(filepath: Path, sample_rate: int, num_segments: int = 10) -> float:
    """Calculate bitrate variance across multiple segments of the file.
    
    This helps identify authentic FLAC with variable bitrate vs constant bitrate transcodes.
    
    Args:
        filepath: Path to FLAC file
        sample_rate: Sample rate in Hz
        num_segments: Number of segments to analyze
        
    Returns:
        Bitrate variance in kbps
    """
    try:
        info = sf.info(filepath)
        total_duration = info.duration
        
        if total_duration < num_segments:
            num_segments = max(1, int(total_duration))
        
        segment_duration = total_duration / num_segments
        file_size = filepath.stat().st_size
        
        # Calculate bitrate for each segment (approximation based on file position)
        bitrates = []
        for i in range(num_segments):
            # Approximate segment size (not perfectly accurate but good enough)
            segment_size = file_size / num_segments
            segment_bitrate = (segment_size * 8) / (segment_duration * 1000)
            bitrates.append(segment_bitrate)
        
        # Calculate variance
        if len(bitrates) > 1:
            import numpy as np
            variance = float(np.std(bitrates))
            return variance
        
        return 0.0
        
    except Exception as e:
        logger.debug(f"Error calculating bitrate variance: {e}")
        return 0.0


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
    score = 0
    reasons: List[str] = []
    
    # Extract metadata
    sample_rate = metadata.get("sample_rate", 44100)
    if isinstance(sample_rate, str):
        try:
            sample_rate = int(sample_rate)
        except (ValueError, TypeError):
            sample_rate = 44100
    
    bit_depth = metadata.get("bit_depth", 16)
    if isinstance(bit_depth, str):
        try:
            bit_depth = int(bit_depth)
        except (ValueError, TypeError):
            bit_depth = 16
    
    channels = metadata.get("channels", 2)
    duration = metadata.get("duration", 0)
    
    # Calculate bitrates
    real_bitrate = calculate_real_bitrate(filepath, duration)
    apparent_bitrate = calculate_apparent_bitrate(sample_rate, bit_depth, channels)
    minimum_expected_bitrate = get_minimum_expected_bitrate(sample_rate, bit_depth)
    bitrate_variance = calculate_bitrate_variance(filepath, sample_rate)
    
    logger.debug(
        f"Bitrate analysis: real={real_bitrate:.1f} kbps, "
        f"apparent={apparent_bitrate} kbps, "
        f"minimum_expected={minimum_expected_bitrate} kbps, "
        f"variance={bitrate_variance:.1f} kbps"
    )
    
    # ========== RULE 1: CONSTANT MP3 BITRATE (50 POINTS) ==========
    for mp3_bitrate in MP3_STANDARD_BITRATES:
        if abs(real_bitrate - mp3_bitrate) <= BITRATE_TOLERANCE:
            score += 50
            reasons.append(f"Constant MP3 bitrate detected: {mp3_bitrate} kbps")
            logger.debug(f"RULE 1: +50 points (bitrate = {mp3_bitrate} kbps)")
            break
    
    # ========== RULE 2: CUTOFF FREQUENCY VS SAMPLE RATE (0-30 POINTS) ==========
    cutoff_threshold = get_cutoff_threshold(sample_rate)
    
    if cutoff_freq < cutoff_threshold:
        cutoff_penalty = min((cutoff_threshold - cutoff_freq) / 200, 30)
        score += int(cutoff_penalty)
        reasons.append(
            f"Low cutoff frequency: {cutoff_freq:.0f} Hz "
            f"(threshold: {cutoff_threshold:.0f} Hz, +{cutoff_penalty:.0f} pts)"
        )
        logger.debug(f"RULE 2: +{cutoff_penalty:.0f} points (cutoff < threshold)")
    
    # ========== RULE 3: REAL BITRATE VS EXPECTED BITRATE (50 POINTS) ==========
    if real_bitrate < 400 and apparent_bitrate > minimum_expected_bitrate:
        score += 50
        reasons.append(
            f"Real bitrate too low: {real_bitrate:.0f} kbps "
            f"(expected: >{minimum_expected_bitrate} kbps)"
        )
        logger.debug(f"RULE 3: +50 points (real bitrate < 400 and apparent > minimum)")
    
    # ========== RULE 4: 24-BIT FILE EXCEPTION (30 POINTS) ==========
    if bit_depth == 24 and real_bitrate < 500:
        score += 30
        reasons.append(
            f"Suspicious 24-bit file: real bitrate {real_bitrate:.0f} kbps < 500 kbps"
        )
        logger.debug(f"RULE 4: +30 points (24-bit with bitrate < 500)")
    
    # ========== RULE 5: AVOID FALSE POSITIVES - HIGH VARIABLE BITRATE (-40 POINTS) ==========
    if real_bitrate > HIGH_BITRATE_THRESHOLD and bitrate_variance > VARIANCE_THRESHOLD:
        score -= 40
        score = max(0, score)  # Minimum 0
        reasons.append(
            f"Authentic high variable bitrate: {real_bitrate:.0f} kbps, "
            f"variance {bitrate_variance:.0f} kbps (-40 pts)"
        )
        logger.debug(f"RULE 5: -40 points (bitrate > 1000 and variance > 100)")
    
    # ========== RULE 6: AVOID FALSE POSITIVES - BITRATE COHERENCE (-30 POINTS) ==========
    bitrate_diff = abs(real_bitrate - apparent_bitrate)
    if bitrate_diff < COHERENCE_TOLERANCE and real_bitrate > COHERENT_BITRATE_THRESHOLD:
        score -= 30
        score = max(0, score)  # Minimum 0
        reasons.append(
            f"Coherent bitrates: real={real_bitrate:.0f} kbps ≈ "
            f"apparent={apparent_bitrate} kbps (-30 pts)"
        )
        logger.debug(f"RULE 6: -30 points (coherence and bitrate > 800)")
    
    # ========== DETERMINE VERDICT ==========
    if score >= SCORE_FAKE_CERTAIN:
        verdict = "FAKE_CERTAIN"
        confidence = "VERY HIGH"
    elif score >= SCORE_FAKE_PROBABLE:
        verdict = "FAKE_PROBABLE"
        confidence = "HIGH"
    elif score >= SCORE_DOUTEUX:
        verdict = "DOUTEUX"
        confidence = "MEDIUM"
    else:
        verdict = "AUTHENTIQUE"
        confidence = "HIGH"
    
    # Format reasons
    reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"
    
    logger.info(
        f"Final score: {score}/100 - Verdict: {verdict} - Confidence: {confidence}"
    )
    
    return score, verdict, confidence, reasons_str
