"""Cassette audio source detection (Rule 11)."""

import logging
import math
from typing import List, Optional, Tuple, cast

import numpy as np
import soundfile as sf
from scipy import signal

from ..audio_loader import load_audio_segment
from ..constants import CUTOFF_VARIANCE_THRESHOLD

logger = logging.getLogger(__name__)


def bandpass_filter(
    data: np.ndarray, lowcut: float, highcut: float, fs: int, order: int = 5
) -> np.ndarray:
    """Apply a bandpass filter to the data."""
    sos = signal.butter(order, [lowcut, highcut], btype="bandpass", fs=fs, output="sos")
    return cast(np.ndarray, signal.sosfilt(sos, data))


def apply_rule_11_cassette_detection(  # noqa: C901
    file_path: str,
    cutoff_freq: float,
    cutoff_std: float,
    sample_rate: int,
    audio_data: Optional[object] = None,
) -> Tuple[int, List[str]]:
    """Apply Rule 11: Cassette Audio Source Detection.

    Detects if the file originates from a cassette tape by analyzing a
    30-second segment from the middle of the file (MEMORY OPTIMIZED).
    This approach avoids loading the entire file into memory.

    IMPORTANT — the returned score is EVIDENCE OF BEING A CASSETTE, not evidence
    of being fake. It must never be added to the transcode score. It was, until
    v1.8, and the audit caught it: Rule 11 measured AUC 0.321, meaning it handed
    *more* points to genuine files than to transcodes (+18.3 vs +11.2 on
    average). A genuine analog transfer was being pushed toward conviction for
    the crime of sounding like an analog transfer. The caller now reads this
    score as a signal and converts it into protection (a negative bonus) or
    nothing at all.

    Args:
        file_path: Path to the FLAC file.
        cutoff_freq: Detected cutoff frequency in Hz.
        cutoff_std: Standard deviation of cutoff frequency.
        sample_rate: Sample rate in Hz.
        audio_data: Optional pre-loaded audio (unused; kept for call compatibility).

    Returns:
        Tuple of (cassette_score, list_of_reasons)
        cassette_score: 0-70 (higher = more likely a genuine cassette transfer)
    """
    cassette_score = 0
    reasons: list[str] = []

    if cutoff_freq >= 19000:
        logger.debug(f"RULE 11: Skipped (cutoff {cutoff_freq:.0f} >= 19000)")
        return 0, reasons

    try:
        info = sf.info(file_path)
        duration = info.duration
        sr = info.samplerate

        # MEMORY OPTIMIZATION: Reduced from 60s to 30s
        segment_duration = 30.0
        start_sec = max(0, (duration - segment_duration) / 2)
        actual_duration = min(segment_duration, duration)

        audio, sr_loaded = load_audio_segment(
            file_path, start_sec=start_sec, duration_sec=actual_duration
        )

        if audio is None:
            logger.error("RULE 11: Failed to load the audio segment for analysis.")
            return 0, reasons

        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        # TEST 11A: Constant Tape Hiss
        if cutoff_freq < 16000:
            noise_band_freq = (cutoff_freq + 1000, 18000)
        else:
            noise_band_freq = (cutoff_freq + 500, min(20000, sr / 2 - 100))

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
                            autocorr = np.corrcoef(noise_signal[:-100], noise_signal[100:])[0, 1]
                            if np.isnan(autocorr):
                                autocorr = 0.0
                    except Exception:
                        autocorr = 0.0

                    if abs(autocorr) < 0.2:  # White/Pink noise (Random)
                        cassette_score += 30
                        reasons.append(
                            f"R11A: Tape hiss detected ({noise_energy_db:.1f} dB, random) (likely cassette)"
                        )
                        logger.info(
                            f"RULE 11A: Tape hiss detected ({noise_energy_db:.1f} dB, random)"
                        )

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
                response.append(-100)  # Effectively silence

        # Calculate slope (dB/kHz) if we have enough points
        if len(response) > 1:
            slope = (response[-1] - response[0]) / 6  # 6 kHz span

            if -6 < slope < -3:  # Natural progressive roll-off
                cassette_score += 20
                reasons.append(
                    f"R11B: Natural cassette roll-off ({slope:.1f} dB/kHz) (likely cassette)"
                )
                logger.info(f"RULE 11B: Natural cassette roll-off ({slope:.1f} dB/kHz)")
            elif slope < -10:  # Sharp cut
                cassette_score -= 20
                reasons.append(f"R11B: Sharp digital cut ({slope:.1f} dB/kHz) (likely digital)")
                logger.info(f"RULE 11B: Sharp digital cut ({slope:.1f} dB/kHz)")

        # TEST 11C — REMOVED in v1.8.
        # It read Rule 9C's MP3-noise-pattern flag and awarded +15 whenever no
        # pattern was found. Rule 9C measured AUC 0.497 (chance) and returned 0
        # for 118 of 120 files in an earlier feature study, so 11C was a constant
        # +15 dressed up as evidence. Rule 9 is gone; 11C goes with it, and the
        # cassette threshold below drops by the same 15 points so that every
        # other test keeps exactly the weight it had.

        # TEST 11D: Cutoff Modulation (wow/flutter)
        # ===========================================
        # Read on the reporting grid, not in raw Hz. ``detect_cutoff`` returns
        # slice boundaries, so every cutoff is quantised to a 250 Hz cell and,
        # with the three windows ``analyze_spectrum`` samples, the reachable
        # values of the wander below 300 Hz are exactly 0.0 (one cell), 117.9
        # (one window one cell away), 204.1 (three cells) and 235.7 (one window
        # two cells away). Two consequences, both repaired in v1.13.1:
        #
        #   * the old lower bound of 50 Hz let 117.9 — the SMALLEST possible
        #     non-zero value of a quantised statistic — earn +15 as "natural
        #     cutoff variation (wow/flutter)". One grid cell is not tape
        #     flutter. The bound is now CUTOFF_VARIANCE_THRESHOLD, the figure
        #     Rule 1's gate A already uses as "the smallest round figure above
        #     the one-cell wander" (ml/r1_gates_repricing.py). Two rules reading
        #     one statistic now share one idea of what its quantum means.
        #   * the old 30-50 Hz "neutral zone" was unreachable. Nothing can land
        #     there. It is gone rather than left looking calibrated.
        #
        # And NaN — the wander was not computable, one window only — contributes
        # NOTHING. Not +15, not -10. See spectrum.cutoff_wander: returning 0.0
        # there made every file of 90 s or less read as "suspect digital" for
        # -10, which is exactly enough to deny a roll-off-only file (11B alone,
        # 20 points) the -40 cassette protection. An absence, scored, toward
        # conviction.
        # The "very stable, suspect digital" -10 is GONE, and CASSETTE_THRESHOLD
        # rose by the same 10 so every other test keeps exactly the weight it
        # had — the same move v1.8 made when 11C was removed. Two reasons, one
        # of principle and one measured:
        #
        #   * on a 250 Hz grid, "std < 30" means "the windows landed in one
        #     cell", which is the ordinary case for genuine and transcode alike.
        #     It never separated anything; it applied a near-constant -10.
        #   * removing it WITHOUT compensating was measured first, on 132 files
        #     (74 movers + 58 controls, ml/r11d_absence_pass.py): 44 transcodes
        #     lost their conviction against a registered bound of 5, because
        #     roll-off-only files (11B alone, 20 points) started clearing a gate
        #     of 15 and collecting -40 with Rule 1 disabled. The phantom had
        #     been absorbed into the calibration. A constant belongs in the
        #     gate, not in a reading that was never taken.
        if math.isnan(cutoff_std):
            logger.debug("RULE 11D: cutoff wander not computable (single window) - no contribution")
        elif CUTOFF_VARIANCE_THRESHOLD < cutoff_std < 300:
            cassette_score += 15
            reasons.append(
                f"R11D: Natural cutoff variation ({cutoff_std:.0f} Hz, wow/flutter) (likely cassette)"
            )
            logger.info(f"RULE 11D: Natural cutoff variation ({cutoff_std:.0f} Hz, wow/flutter)")
        else:
            # A stable cutoff (0-130 Hz, i.e. up to one grid cell of wander) and
            # anything at or above 300: measured, and evidence of nothing.
            logger.debug(f"RULE 11D: wander {cutoff_std:.0f} Hz reads as neither - Neutral")

    except Exception as e:
        logger.error(f"RULE 11: Analysis error: {e}")
        return 0, reasons

    return max(0, cassette_score), reasons
