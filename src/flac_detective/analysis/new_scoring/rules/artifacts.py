"""Artifacts analysis rules (Rule 9)."""

from typing import List, Optional, Tuple
from ..artifacts import analyze_compression_artifacts


def apply_rule_9_compression_artifacts(
    file_path: str,
    cutoff_freq: float,
    mp3_bitrate_detected: Optional[int],
    audio_data: Optional[object] = None,
    sample_rate: Optional[int] = None
) -> Tuple[int, List[str], dict]:
    """Apply Rule 9: Psychoacoustic Compression Artifacts Detection.

    Detects lossy compression signatures beyond simple frequency cutoff:
    - Test 9A: Pre-echo artifacts (MDCT ghosting before transients)
    - Test 9B: High-frequency aliasing (filterbank artifacts)
    - Test 9C: MP3 quantization noise patterns

    This rule activates ONLY if:
    - cutoff_freq < 21000 Hz (suspicious zone), OR
    - Rule 1 detected an MP3 signature

    Scoring (cumulative, max +40 points):
        Test 9A (Pre-echo):
            - >10% transients affected: +15 points
            - 5-10% affected: +10 points
            - <5%: 0 points

        Test 9B (HF Aliasing):
            - Correlation > 0.5: +15 points (strong aliasing)
            - Correlation 0.3-0.5: +10 points (moderate aliasing)
            - Correlation < 0.3: 0 points

        Test 9C (MP3 Noise Pattern):
            - Pattern detected: +10 points
            - No pattern: 0 points

    Args:
        file_path: Path to the FLAC file
        cutoff_freq: Detected cutoff frequency in Hz
        mp3_bitrate_detected: Detected MP3 bitrate from Rule 1 (or None)
        audio_data: Optional pre-loaded audio data (numpy array)
        sample_rate: Optional sample rate of pre-loaded data

    Returns:
        Tuple of (score_delta, list_of_reasons, details_dict)
    """
    # analyze_compression_artifacts is imported at module level

    score, reasons, details = analyze_compression_artifacts(
        file_path,
        cutoff_freq,
        mp3_bitrate_detected,
        audio_data=audio_data,
        sample_rate=sample_rate
    )

    return score, reasons, details
