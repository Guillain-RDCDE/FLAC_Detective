"""Cassette audio source detection (Rule 11)."""

import logging
from typing import List, Tuple, Optional
import numpy as np
from scipy import signal
import soundfile as sf

from ..audio_loader import load_audio_with_retry

logger = logging.getLogger(__name__)


def bandpass_filter(data: np.ndarray, lowcut: float, highcut: float, fs: int, order: int = 5) -> np.ndarray:
    """Apply a bandpass filter to the data."""
    sos = signal.butter(order, [lowcut, highcut], btype='bandpass', fs=fs, output='sos')
    return signal.sosfilt(sos, data)


def apply_rule_11_cassette_detection(
    file_path: str,
    cutoff_freq: float,
    cutoff_std: float,
    mp3_pattern_detected: bool,
    cutoff_std: float,
    mp3_pattern_detected: bool,
    sample_rate: int,
    audio_data: Optional[object] = None
) -> Tuple[int, List[str]]:
    """Apply Rule 11: Cassette Audio Source Detection.

    Detects if the file originates from a cassette tape.
    High score = High likelyhood of being a cassette (Authentic).

    Args:
        file_path: Path to the FLAC file.
        cutoff_freq: Detected cutoff frequency in Hz.
        cutoff_std: Standard deviation of cutoff frequency.
        mp3_pattern_detected: Result from Rule 9C.
        sample_rate: Sample rate in Hz.

    Returns:
        Tuple of (cassette_score, list_of_reasons)
        cassette_score: 0-85 (Positive score means likely cassette)
    """
    cassette_score = 0
    reasons = []

    # Activation condition: cutoff < 19 kHz (cassette limitation)
    if cutoff_freq >= 19000:
        logger.debug(f"RULE 11: Skipped (cutoff {cutoff_freq:.0f} >= 19000)")
        return 0, reasons

    try:
    try:
        # Load audio file with retry mechanism if not provided
        audio = None
        sr = sample_rate

        if audio_data is not None:
             logger.info("RULE 11: Using pre-loaded audio data (cached)")
             audio = audio_data
             # Assume sample_rate matches the one provided in args
        else:
             logger.info("RULE 11: Loading audio from file (no cache provided)...")
             audio, sr = load_audio_with_retry(file_path)
             if sr != sample_rate and sr is not None:
                 # Minimal check, though if we loaded from file, we trust this new SR.
                 pass
        
        if audio is None:
            logger.error(
                f"RULE 11: Failed to load audio after retries. "
                f"Returning 0 points (no penalty for temporary decoder issues)."
            )
            return 0, reasons
        
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1) # Mono
        
        # TEST 11A: Constant Tape Hiss
        # ====================================
        # Filter high band (above musical cutoff)
        if cutoff_freq < 16000:
            noise_band_freq = (cutoff_freq + 1000, 18000)
        else:
            noise_band_freq = (cutoff_freq + 500, min(20000, sr/2 - 100))
        
        # Ensure valid range
        if noise_band_freq[1] <= noise_band_freq[0]:
             logger.debug("RULE 11: Skipped 11A (invalid noise band)")
        else:
            noise_signal = bandpass_filter(audio, noise_band_freq[0], noise_band_freq[1], sr)
            noise_energy_db = 20 * np.log10(np.std(noise_signal) + 1e-10)
            
            if noise_energy_db > -55:  # Noise present
                # Check random texture (no MP3 pattern)
                # Ensure we have enough data for correlation
                if len(noise_signal) > 200:
                    try:
                        # Check variation to avoid Div/0
                        std_check = np.std(noise_signal)
                        if std_check < 1e-6:
                             autocorr = 0.0
                        else:
                             autocorr = np.corrcoef(
                                noise_signal[:-100],
                                noise_signal[100:]
                            )[0, 1]
                            if np.isnan(autocorr):
                                autocorr = 0.0
                    except Exception:
                        autocorr = 0.0
                    
                    if abs(autocorr) < 0.2:  # White/Pink noise (Random)
                        cassette_score += 30
                        reasons.append(f"R11A: Bruit de bande détecté ({noise_energy_db:.1f} dB, aléatoire) (Prob. Cassette)")
                        logger.info(f"RULE 11A: Tape hiss detected ({noise_energy_db:.1f} dB, random)")
        
        # TEST 11B: Progressive Roll-off
        # ================================
        # Measure freq response 12-18 kHz
        freqs = np.linspace(12000, 18000, 20)
        response = []
        
        for freq in freqs:
            # Ensure within Nyquist
            if freq + 250 < sr / 2:
                band_signal = bandpass_filter(audio, freq - 250, freq + 250, sr)
                energy = np.std(band_signal)
                response.append(20 * np.log10(energy + 1e-10))
            else:
                 response.append(-100) # Effectively silence

        # Calculate slope (dB/kHz) if we have enough points
        if len(response) > 1:
            slope = (response[-1] - response[0]) / 6  # 6 kHz span
            
            if -6 < slope < -3:  # Natural progressive roll-off
                cassette_score += 20
                reasons.append(f"R11B: Roll-off naturel cassette ({slope:.1f} dB/kHz) (Prob. Cassette)")
                logger.info(f"RULE 11B: Natural cassette roll-off ({slope:.1f} dB/kHz)")
            elif slope < -10:  # Sharp cut
                cassette_score -= 20
                reasons.append(f"R11B: Coupure nette numérique ({slope:.1f} dB/kHz) (Prob. Numérique)")
                logger.info(f"RULE 11B: Sharp digital cut ({slope:.1f} dB/kHz)")

        # TEST 11C: No MP3 Pattern
        # ================================
        if not mp3_pattern_detected:
            cassette_score += 15
            reasons.append("R11C: Aucun pattern MP3 détecté (compatible cassette) (Prob. Cassette)")
            logger.info("RULE 11C: No MP3 pattern detected (compatible with cassette)")

        # TEST 11D: Cutoff Modulation (wow/flutter)
        # ===========================================
        if 50 < cutoff_std < 300:  # Moderate variation
            cassette_score += 15
            reasons.append(f"R11D: Variation cutoff naturelle ({cutoff_std:.0f} Hz, wow/flutter) (Prob. Cassette)")
            logger.info(f"RULE 11D: Natural cutoff variation ({cutoff_std:.0f} Hz, wow/flutter)")
        elif cutoff_std < 30:  # Very stable (digital silence/CBR)
            cassette_score -= 10
            reasons.append(f"R11D: Cutoff très stable ({cutoff_std:.0f} Hz, suspect digital) (Prob. Numérique)")
            logger.info(f"RULE 11D: Cutoff very stable ({cutoff_std:.0f} Hz, suspect digital)")
        elif cutoff_std < 50:
            # 30-50 Hz: Neutral zone (stable cassette deck is possible)
            logger.debug(f"RULE 11D: Cutoff stable but acceptable ({cutoff_std:.0f} Hz) - Neutral")

    except Exception as e:
        logger.error(f"RULE 11: Analysis error: {e}")
        return 0, reasons
    
    return max(0, cassette_score), reasons
