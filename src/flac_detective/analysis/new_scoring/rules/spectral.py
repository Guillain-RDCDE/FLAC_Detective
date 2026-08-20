"""Spectral analysis rules (Rule 1, Rule 2, Rule 8).

Rule 1's near-Nyquist region, and why it stays shut
---------------------------------------------------
Rule 1 awards +50, and every false conviction this project has ever shipped came
from Rule 1 + Rule 3 at +50 each. It is therefore guarded, and at 44.1 kHz the
binding guard is ``cutoff >= 0.95 * Nyquist`` (20,947.5 Hz): above that line Rule 1
returns before any instrument is consulted.

Real 320 kbps transcodes DO live above that line — his 17 real 2009 DJ-master MP3s
include 6 with no wall at all up to 22,023 Hz — so the guard is not merely
conservative; it is silent on a real population. Measured on our own corpus, that
region holds 29 of 40 ``mp3_V0`` files and 34 of 40 ``aac_ff320`` files.

It stays shut regardless, because 28 of his 75 **lawful** masters sit up there too.
See the comment on ``HIGH_QUALITY_CUTOFF_THRESHOLD``: no edge position separates
those two populations, so no amount of moving this constant would help.

Opening it was attempted on 2026-08-20 and **the measurement refused**:

* The calibrated instrument that settles the ambiguous zone,
  ``compute_residual_floor_db``, reads a FIXED band at 0.961-0.993 * Nyquist. Any wall
  landing inside that band is straddled — half live signal, half digital silence — so
  the instrument reads a brickwall as an authentic rolloff. It cannot simply be
  extended upward; a band that is meant to characterise a wall has to follow it.
* A cutoff-RELATIVE residual was built and measured instead (``ml/nearnyq_residual_probe.py``).
  In the closed region it reads AUC 0.79 on ``mp3_V0``, 0.72 on ``aacmf_256`` and
  **0.45 on ``aac_ff320``** — worse than chance on the arm that matters most. The
  genuine population reaches down to -59.6 dB, below the transcode median of -42.4,
  so no threshold separates them. And it abstains on 81 % of genuine files, correctly:
  a spectrum that runs to Nyquist has no wall to characterise, and n=9 transcodes is
  not a calibration set after what a 25-file sample did to Rule 15's bar.

So the region is closed on evidence, not on assumption, and the assumption that used
to justify it was false. Those are different failures and only one of them was fixed.

One consequence is corrected here: ``analyze_spectrum`` used to compute the residual
across [0.90, 0.95) * Nyquist while Rule 1 rejects any 320 estimate from
0.94 * Nyquist up — so a 220 Hz slice was computed and thrown away every time. The
window now stops where the rule stops. Widening the RULE to match the window was the
other way to reconcile them, and was rejected: in that slice 1 genuine file of 7
reads below the -55 dB conviction floor. One option is free and the other needs
evidence we do not have.
"""

import logging
import math
from typing import List, Optional, Tuple

from ..bitrate import estimate_mp3_bitrate, get_cutoff_threshold

logger = logging.getLogger(__name__)

# Wall-hardness gate for the near-Nyquist 320 kbps zone (Rule 1).
# A 320 kbps cutoff (~20.5 kHz) sits where an authentic band-limited rolloff and a
# real MP3 brickwall overlap, so cutoff position alone cannot tell them apart — this
# is the dominant false-positive source in real libraries. The residual spectral
# floor above the wall does separate them (calibrated on 50 synthetic FLAC->320k
# pairs + a band-limited surrogate, ROC AUC 0.95; the one confirmed real near-Nyquist
# transcode floored at -57 dB):
#   residual >  -55 dB -> authentic analog/dither floor      -> drop the signature
#   residual <= -55 dB -> digital-silence floor (transcode)  -> keep the +50 (FAKE)
# A single threshold (not a 3-band scheme): an intermediate "gray" band that withholds
# the +50 lets the score fall below the fast FAKE_CERTAIN short-circuit, after which
# protective rules (e.g. R7 clean-silence -50) can wrongly clear a genuine transcode.
# Keeping real transcodes at +50 preserves that short-circuit. Threshold favours the
# project's "protect authentic first" rule, accepting that transcodes of already
# band-limited material (shallow wall, floor > -55 dB) are near-undetectable anyway.
NEARNYQ_FLOOR_DB = -55.0


def apply_rule_1_mp3_bitrate(  # noqa: C901
    cutoff_freq: float,
    container_bitrate: float,
    cutoff_std: float = 0.0,
    sample_rate: int = 44100,
    energy_ratio: float = 0.0,
    residual_floor_db: float = float("nan"),
) -> Tuple[Tuple[int, List[str]], Optional[int]]:
    """Apply Rule 1: Constant MP3 Bitrate Detection (Spectral Estimation).

    Detects if the file's spectral cutoff matches a standard MP3 bitrate signature.
    This allows detecting MP3s recompressed as FLACs (Fake FLACs).

    Scoring:
        +50 points if estimated spectral bitrate matches a standard MP3 bitrate
        AND container bitrate is within expected range for that MP3 bitrate.

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        container_bitrate: Physical bitrate of the FLAC file in kbps
        cutoff_std: Standard deviation of cutoff frequency
        sample_rate: Sample rate in Hz (default: 44100)
        energy_ratio: High frequency energy ratio (default: 0.0)
        residual_floor_db: Spectral floor above the ~20.5 kHz wall in dB (NaN =
            unknown). Gates the near-Nyquist 320 kbps branch; NaN falls back to the
            legacy cutoff-only behaviour.

    Returns:
        Tuple of ((score_delta, list_of_reasons), estimated_bitrate)
    """
    score = 0
    reasons: List[str] = []

    # Safety check 1: Nyquist Exception (OPTIMAL)
    # If cutoff is >= 95% of Nyquist frequency, it's likely the anti-aliasing filter
    # of an authentic FLAC, not an MP3 signature
    nyquist_freq = sample_rate / 2.0
    nyquist_threshold = 0.95 * nyquist_freq

    if cutoff_freq >= nyquist_threshold:
        logger.debug(
            f"RULE 1: Skipped (cutoff {cutoff_freq:.0f} Hz >= 95% Nyquist {nyquist_threshold:.0f} Hz, "
            f"likely anti-aliasing filter)"
        )
        return (score, reasons), None

    # EXCEPTION CRITIQUE : Cutoff exactement 20 kHz (ENHANCED)
    # ==========================================================
    # Problème : FFT peut arrondir 20-21 kHz à 20000 Hz pile
    # Solutions :
    #   1. Test énergie résiduelle > 20 kHz (energy_ratio)
    #   2. Test variance nulle (cutoff_std)
    if cutoff_freq == 20000.0:
        # Test 1 : Énergie résiduelle au-dessus de 20 kHz (HIGH_FREQ_THRESHOLD)
        # Seuil minimal pour détecter présence d'énergie HF
        if energy_ratio > 0.000001:
            logger.info(f"RULE 1: Cutoff 20 kHz but HF energy = {energy_ratio:.6f}")
            logger.info("RULE 1: Likely FFT rounding, not MP3 320k - SKIP")
            return (0, []), None

        # Test 2 : Variance nulle + cutoff pile = ambigu
        if cutoff_std == 0.0:
            logger.info("RULE 1: Cutoff exactement 20000 Hz avec variance 0")
            logger.info("RULE 1: Ambiguous (could be FFT rounding) - SKIP for safety")
            return (0, []), None

    # Safety check 2: a cutoff this high is treated as an authentic high-quality FLAC.
    #
    # This comment used to read "MP3s never have cutoffs above 21.5 kHz (even 320 kbps
    # tops out around 20.5-21 kHz)". That is false, and it is false in BOTH directions,
    # which is a stronger and more useful statement than the one this comment carried
    # between 2026-08-20 and 2026-08-21.
    #
    # The first correction cited a specific frequency (~21,570 Hz) for an era-LAME 320
    # wall. Jamie Dodd of Provir supplied that number and then RETRACTED it himself,
    # with the error bars he had left off:
    #
    #   * it is one reading, of one file, by one edge-finder written that morning;
    #   * early 3.9x at -b 320 applies NO LOWPASS AT ALL, so the figure measures the
    #     source material and not the encoder — the same build group swings 3,800 Hz
    #     on content alone (17,420 Hz on one track of a CD, 21,226 Hz on another);
    #   * 503 of his 1,180 lawful files (42.6 %) already read an edge at or above it,
    #     so a threshold there convicts lawful CD masters at scale — classical and
    #     acoustic material first.
    #
    # He also disclosed fusing two different 8 Hz figures: 8.1 Hz was store-file vs
    # recreation, and ~8 Hz was build-to-build. "Walls at ~21,570 across five builds
    # within 8 Hz" is a sentence no measurement supports, and this file asserted it.
    # The build-to-build spread does survive on its own (5.3-5.4 Hz on separate
    # material, measured before the claim existed) but must never be bound to a
    # frequency.
    #
    # What survives is the conclusion, and it is the reason this guard cannot simply
    # be moved up. Of his 17 real 2009 DJ-master MP3s, 11 carry a sharp wall topping
    # out at 21,479 Hz and 6 have no wall at all up to 22,023 Hz; meanwhile 28 of his
    # 75 lawful masters sit above 21,570. BOTH POPULATIONS LIVE ON BOTH SIDES OF EVERY
    # LINE. There is no edge position that separates them, so 21,500 is not a
    # threshold set too low — it is the wrong kind of quantity.
    #
    # That also settles the instrument caveat rather than leaving it open. His two
    # edge-finders read the same file at 21,436.3 and 21,562.8 Hz, either side of this
    # constant. That is not a problem awaiting a fix; it is the same result arriving
    # from measurement error instead of from population overlap.
    #
    # The guard therefore stays, and stays as a GATE rather than as evidence. What
    # discriminates is how fast the spectrum falls, not where — see
    # analysis/spectrum.py's `detect_cutoff_detailed` and its EdgeReading docstring.
    #
    # Note this branch is REDUNDANT at 44.1 kHz, where safety check 1 has already
    # returned at 0.95 * Nyquist = 20,947.5 Hz. It is live at 48 kHz and above, where
    # 0.95 * Nyquist exceeds 21,500.
    HIGH_QUALITY_CUTOFF_THRESHOLD = 21500

    if cutoff_freq > HIGH_QUALITY_CUTOFF_THRESHOLD:
        logger.debug(
            f"RULE 1: Skipped (cutoff {cutoff_freq:.0f} Hz > {HIGH_QUALITY_CUTOFF_THRESHOLD} Hz, likely authentic FLAC)"
        )
        return (score, reasons), None

    # Safety check 3: Variance check
    # Authentic FLACs often have variable cutoffs (high variance).
    # CBR MP3s have very stable cutoffs (low variance).
    CUTOFF_VARIANCE_THRESHOLD = 100.0  # Hz

    if cutoff_std > CUTOFF_VARIANCE_THRESHOLD:
        logger.debug(
            f"RULE 1: Skipped (cutoff std {cutoff_std:.1f} > {CUTOFF_VARIANCE_THRESHOLD}, variable spectrum)"
        )
        return (score, reasons), None

    estimated_bitrate = estimate_mp3_bitrate(cutoff_freq)

    if estimated_bitrate == 0:
        return (score, reasons), None

    # Check if container bitrate matches the estimated MP3 bitrate range
    # Plages typiques pour MP3 convertis en FLAC
    mp3_ranges = {
        128: (400, 550),
        160: (450, 650),
        192: (500, 750),
        224: (550, 800),
        256: (600, 850),
        320: (700, 1050),
    }

    if estimated_bitrate in mp3_ranges:
        min_br, max_br = mp3_ranges[estimated_bitrate]

        # EXCEPTION SPÉCIFIQUE 320 kbps : Si cutoff >= 94% Nyquist, c'est probablement légitime
        # Les vrais MP3 320 kbps ont un cutoff autour de 20-20.5 kHz (approx 93% de 22.05kHz)
        # Un cutoff > 94% Nyquist suggère un filtre anti-aliasing naturel
        if estimated_bitrate == 320:
            nyquist_freq = sample_rate / 2.0
            nyquist_limit_percent = 0.94 * nyquist_freq

            if cutoff_freq >= nyquist_limit_percent:
                logger.debug(
                    f"RULE 1: Skipped 320 kbps detection (cutoff {cutoff_freq:.0f} Hz >= 94% Nyquist "
                    f"{nyquist_limit_percent:.0f} Hz, likely legitimate high-quality file)"
                )
                return (score, reasons), None

        # Le bitrate conteneur est-il dans la plage attendue ?
        if min_br <= container_bitrate <= max_br:
            # Near-Nyquist 320 kbps wall-hardness gate. The cutoff alone cannot tell a
            # 320k brickwall from an authentic band-limited rolloff here; the residual
            # floor can. NaN (unknown / not in the near-Nyquist zone) -> legacy +50.
            if (
                estimated_bitrate == 320
                and not math.isnan(residual_floor_db)
                and residual_floor_db > NEARNYQ_FLOOR_DB
            ):
                logger.info(
                    f"RULE 1: 320 kbps signature dropped (residual floor "
                    f"{residual_floor_db:.0f} dB > {NEARNYQ_FLOOR_DB:.0f} → authentic band-limited)"
                )
                reasons.append(
                    f"R1: 320 kbps cutoff near Nyquist but high residual floor "
                    f"({residual_floor_db:.0f} dB) → authentic band-limited, signature dropped"
                )
                return (score, reasons), None
            # residual <= -55 dB (or unknown): digital-silence floor = real transcode.

            score += 50
            reasons.append(f"Constant MP3 bitrate detected (Spectral): {estimated_bitrate} kbps")
            logger.info(
                f"RULE 1: +50 points (cutoff {cutoff_freq:.0f} Hz ~= {estimated_bitrate} kbps MP3, "
                f"container {container_bitrate:.0f} kbps in range {min_br}-{max_br})"
            )
            return (score, reasons), estimated_bitrate
        else:
            logger.debug(
                f"RULE 1: Skipped (cutoff suggests {estimated_bitrate} kbps MP3, "
                f"but container bitrate {container_bitrate:.0f} kbps outside range {min_br}-{max_br})"
            )

    return (score, reasons), None


def apply_rule_2_cutoff(cutoff_freq: float, sample_rate: int) -> Tuple[int, List[str]]:
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
    reasons: list[str] = []
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
            f"(cutoff {cutoff_freq:.0f} <threshold {cutoff_threshold:.0f})"
        )

    return score, reasons


def apply_rule_8_nyquist_exception(
    cutoff_freq: float,
    sample_rate: int,
    mp3_bitrate_detected: Optional[int],
    silence_ratio: Optional[float] = None,
) -> Tuple[int, List[str]]:
    """Apply Rule 8: Nyquist Exception (ALWAYS APPLIED with Safeguards).

    Protects files with cutoff frequency near the theoretical Nyquist limit
    (sample_rate / 2). These are likely authentic FLACs with proper anti-aliasing
    filters or high-quality recordings.

    Scoring (ALWAYS calculated):
        - cutoff >= 0.98 × Nyquist: -50 points base (strong bonus)
        - 0.95 <= cutoff < 0.98 × Nyquist: -30 points base (moderate bonus)
        - cutoff < 0.95 × Nyquist: 0 points (no bonus)

    Safeguards (reduce or cancel bonus):
        - MP3 signature + silence_ratio > 0.2: Bonus CANCELLED (0 points)
        - MP3 signature + silence_ratio > 0.15: Bonus REDUCED to -15 points
        - MP3 signature + silence_ratio <= 0.15: Bonus APPLIED (authentic)
        - No MP3 signature: Bonus APPLIED (always)

    Args:
        cutoff_freq: Detected cutoff frequency in Hz
        sample_rate: Sample rate in Hz
        mp3_bitrate_detected: Detected MP3 bitrate from Rule 1 (or None)
        silence_ratio: Ratio from Rule 7 silence analysis (or None)

    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
    score = 0
    reasons: list[str] = []

    # Calculate Nyquist frequency
    nyquist_freq = sample_rate / 2.0

    # Calculate cutoff as percentage of Nyquist
    cutoff_ratio = cutoff_freq / nyquist_freq

    # STEP 1: Calculate base bonus based on cutoff ratio
    base_bonus = 0

    if cutoff_ratio >= 0.98:
        base_bonus = -50
        bonus_description = "Very close to limit"
    elif cutoff_ratio >= 0.95:
        base_bonus = -30
        bonus_description = "Probably authentic"
    else:
        # No bonus for cutoff < 95% of Nyquist
        logger.debug(
            f"RULE 8: No bonus (cutoff {cutoff_freq:.0f} Hz = {cutoff_ratio*100:.1f}% of Nyquist, < 95%)"
        )
        return score, reasons

    # STEP 2: Apply safeguards if MP3 signature detected
    final_bonus = base_bonus

    if mp3_bitrate_detected is not None:
        # MP3 signature detected - check silence ratio
        if silence_ratio is not None and silence_ratio > 0.2:
            # Suspect artificial dither - CANCEL bonus
            final_bonus = 0
            reasons.append(
                f"R8: Nyquist bonus cancelled (MP3 signature {mp3_bitrate_detected} kbps + "
                f"suspect dither {silence_ratio:.2f} > 0.2)"
            )
            logger.info(
                f"RULE 8: Bonus CANCELLED (MP3 {mp3_bitrate_detected} kbps + "
                f"silence ratio {silence_ratio:.2f} > 0.2)"
            )
        elif silence_ratio is not None and silence_ratio > 0.15:
            # Grey zone - REDUCE bonus
            final_bonus = -15
            reasons.append(
                f"R8: Cutoff at {cutoff_ratio*100:.1f}% of Nyquist "
                f"({cutoff_freq:.0f}/{nyquist_freq:.0f} Hz) → Reduced bonus "
                f"(MP3 signature + grey zone) (-15pts)"
            )
            logger.info(
                f"RULE 8: Bonus REDUCED to -15 points (MP3 {mp3_bitrate_detected} kbps + "
                f"silence ratio {silence_ratio:.2f} in grey zone)"
            )
        else:
            # Silence ratio <= 0.15 or None - APPLY bonus (authentic)
            reasons.append(
                f"R8: Cutoff at {cutoff_ratio*100:.1f}% of Nyquist "
                f"({cutoff_freq:.0f}/{nyquist_freq:.0f} Hz) → {bonus_description} "
                f"({base_bonus}pts, MP3 signature but authentic silence)"
            )
            logger.info(
                f"RULE 8: {base_bonus} points (cutoff {cutoff_freq:.0f} Hz >= "
                f"{cutoff_ratio*100:.0f}% of Nyquist, MP3 signature but authentic silence)"
            )
    else:
        # No MP3 signature - APPLY bonus unconditionally
        reasons.append(
            f"R8: Cutoff at {cutoff_ratio*100:.1f}% of Nyquist "
            f"({cutoff_freq:.0f}/{nyquist_freq:.0f} Hz) → {bonus_description} ({base_bonus}pts)"
        )
        logger.info(
            f"RULE 8: {base_bonus} points (cutoff {cutoff_freq:.0f} Hz >= "
            f"{cutoff_ratio*100:.0f}% of Nyquist)"
        )

    score = final_bonus

    return score, reasons
