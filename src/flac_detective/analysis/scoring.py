"""Quality score calculation for FLAC files."""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Adaptive threshold ratio (percentage of Nyquist frequency)
# A file is considered authentic if cutoff >= ADAPTIVE_THRESHOLD_RATIO * Nyquist
# Increased to 0.95 (e.g. 20.95kHz for 44.1kHz) to catch high-cutoff MP3s
ADAPTIVE_THRESHOLD_RATIO = 0.95

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


def get_adaptive_threshold(sample_rate: int) -> float:
    """Calculate adaptive threshold based on sample rate.

    Args:
        sample_rate: Sample rate in Hz.

    Returns:
        Adaptive threshold frequency in Hz (95% of Nyquist).
    """
    nyquist = sample_rate / 2.0
    return nyquist * ADAPTIVE_THRESHOLD_RATIO


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


def calculate_score(
    cutoff_freq: float, energy_ratio: float, metadata: Dict, duration_check: Dict
) -> Tuple[int, str]:
    """Calculates a confidence score (0-100) and generates a reason.

    Uses a multi-criteria scoring system:
    1. Cutoff Frequency & Bitrate Detection (Primary)
    2. High Frequency Energy (Secondary)
    3. Duration Consistency (Validation)
    4. Metadata Analysis (Validation)

    Args:
        cutoff_freq: Detected cutoff frequency in Hz.
        energy_ratio: Energy ratio in high frequencies.
        metadata: File metadata.
        duration_check: Duration check result.

    Returns:
        Tuple (score, reason) where score is between 0 and 100.
    """
    reasons = []
    score = 100

    # Get sample rate
    sample_rate = metadata.get("sample_rate", 44100)
    if isinstance(sample_rate, str):
        try:
            sample_rate = int(sample_rate)
        except (ValueError, TypeError):
            sample_rate = 44100

    nyquist = sample_rate / 2.0
    adaptive_threshold = get_adaptive_threshold(sample_rate)

    logger.debug(
        f"Scoring: sample_rate={sample_rate}Hz, Nyquist={nyquist:.0f}Hz, "
        f"threshold={adaptive_threshold:.0f}Hz, cutoff={cutoff_freq:.0f}Hz"
    )

    # --- CRITERION 1: Cutoff Frequency & Bitrate Detection ---

    # Check for specific MP3 signatures first (Priority 1)
    estimated_bitrate = estimate_mp3_bitrate(cutoff_freq)

    if estimated_bitrate > 0:
        # Detected a specific MP3 signature
        if estimated_bitrate == 320:
            score -= 40
            reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (matches MP3 320kbps)")
        elif estimated_bitrate == 256:
            score -= 50
            reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (matches MP3 256kbps)")
        elif estimated_bitrate == 224:
            score -= 60
            reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (matches MP3 224kbps)")
        elif estimated_bitrate == 192:
            score -= 70
            reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (matches MP3 192kbps)")
        elif estimated_bitrate <= 160:
            score -= 80
            reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (matches MP3 {estimated_bitrate}kbps)")

    elif cutoff_freq >= adaptive_threshold:
        # High cutoff, no MP3 signature -> Likely Authentic
        reasons.append(
            f"Full spectrum up to {cutoff_freq:.0f} Hz "
            f"(≥{ADAPTIVE_THRESHOLD_RATIO*100:.0f}% of Nyquist)"
        )
    else:
        # Low cutoff but no specific MP3 match (Generic Suspicion)
        score -= 60
        reasons.append(f"Unusual cutoff at {cutoff_freq:.0f} Hz (suspicious)")

    # --- CRITERION 2: High Frequency Energy ---
    # If cutoff is high but energy is low, it's suspicious (upsampling/filtering)

    cutoff_is_high = cutoff_freq >= adaptive_threshold

    if cutoff_is_high:
        if energy_ratio < 0.00001:
            score -= 10
            reasons.append("Very low high-freq energy (possible upsampling)")
    else:
        # If cutoff is low, low energy is expected, but extremely low energy reinforces suspicion
        if energy_ratio < 0.0001:
            score -= 10
            reasons.append("No energy >16kHz")

    # --- CRITERION 3: Duration Consistency ---
    if duration_check.get("mismatch"):
        diff_ms = duration_check.get("diff_ms", 0)
        if diff_ms > 1000:
            score -= 20
            reasons.append(f"Duration mismatch ({diff_ms:.0f}ms)")
        elif diff_ms > 100:
            score -= 10
            reasons.append(f"Slight duration mismatch ({diff_ms:.0f}ms)")

    # --- CRITERION 4: Metadata ---
    encoder = metadata.get("encoder", "").lower()
    if "lame" in encoder or "mp3" in encoder:
        score -= 30
        reasons.append(f"Suspicious encoder: {metadata.get('encoder')}")

    bit_depth = metadata.get("bit_depth")
    if bit_depth and isinstance(bit_depth, int) and bit_depth < 16:
        score -= 20
        reasons.append(f"Low bit depth: {bit_depth} bits")

    # Final Score
    final_score = max(0, min(100, score))
    reason_str = " | ".join(reasons) if reasons else "Normal analysis"

    return final_score, reason_str
