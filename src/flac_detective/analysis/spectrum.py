"""Spectral analysis of audio files."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, NamedTuple, Optional, Tuple

import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq, set_workers

from ..config import spectral_config
from .window_cache import get_hann_window

if TYPE_CHECKING:
    from .audio_cache import AudioCache

logger = logging.getLogger(__name__)


def _welch_magnitude_db(
    data_mono: np.ndarray, samplerate: int, nfft: int = 16384
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Welch-averaged magnitude spectrum (Hann, 50% overlap) in dB.

    A stable spectrum estimate for the residual-floor metric. Returns (None, None)
    if the signal is shorter than one FFT window.
    """
    if len(data_mono) < nfft:
        return None, None
    win = get_hann_window(nfft)
    step = nfft // 2
    acc: Optional[np.ndarray] = None
    count = 0
    with set_workers(1):
        for start in range(0, len(data_mono) - nfft, step):
            seg = data_mono[start : start + nfft] * win
            m = np.abs(rfft(seg))
            acc = m if acc is None else acc + m
            count += 1
    if count == 0 or acc is None:
        return None, None
    mag = acc / count
    freq = rfftfreq(nfft, 1 / samplerate)
    magnitude_db = 20 * np.log10(mag + 1e-10)
    return freq, magnitude_db


def compute_residual_floor_db(
    full_audio: np.ndarray, samplerate: int, max_seconds: float = 30.0
) -> float:
    """Residual spectral floor just above the ~20.5 kHz wall, vs the in-band reference.

    A real 320 kbps MP3 brickwall drops to the digital-silence floor (strongly
    negative, ~ -70 dB); an authentic band-limited rolloff keeps a higher
    analog/dither floor (~ -25 to -50 dB). This is the discriminator that cutoff
    position alone cannot provide near Nyquist (calibrated on 50 synthetic
    FLAC->320k pairs + a band-limited surrogate; see Rule 1's near-Nyquist gate).

    Returns NaN when the reference/top bands are unavailable (e.g. hi-res) or the
    signal is too short — callers must treat NaN as "unknown" and fall back to the
    legacy behaviour.
    """
    try:
        data = full_audio
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        data = np.asarray(data[: int(max_seconds * samplerate)], dtype=np.float64)
        freq, magnitude_db = _welch_magnitude_db(data, samplerate)
        if freq is None or magnitude_db is None:
            return float("nan")
        nyq = samplerate / 2.0
        ref_mask = (freq >= 0.45 * nyq) & (freq <= 0.65 * nyq)
        top_mask = (freq >= 0.961 * nyq) & (freq <= 0.993 * nyq)
        if not (np.any(ref_mask) and np.any(top_mask)):
            return float("nan")
        ref = float(np.median(magnitude_db[ref_mask]))
        top = float(np.median(magnitude_db[top_mask]))
        return top - ref
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"Residual floor computation failed: {e}")
        return float("nan")


def analyze_spectrum(
    filepath: Path, sample_duration: float = 30.0, cache: "Optional[AudioCache]" = None
) -> Tuple[float, float, float, float]:
    """Analyzes the frequency spectrum of the audio file.

    Takes multiple samples at different times for robustness.
    OPTIMIZED: Uses AudioCache to avoid multiple file reads.

    Args:
        filepath: Path to the audio file.
        sample_duration: Duration in seconds to analyze.
        cache: Optional AudioCache instance for optimization.

    Returns:
        Tuple (cutoff_frequency, energy_ratio, cutoff_std, residual_floor_db) where:
        - cutoff_frequency: detected cutoff frequency in Hz
        - energy_ratio: energy ratio in high frequencies
        - cutoff_std: standard deviation of cutoff frequency
        - residual_floor_db: floor above the ~20.5 kHz wall (NaN unless the cutoff
          sits in the near-Nyquist 320 kbps zone, where Rule 1 needs it)
    """
    try:
        # Create cache if not provided
        if cache is None:
            from .audio_cache import AudioCache

            cache = AudioCache(filepath)

        # Get actual audio data to know real duration (handles partial files)
        full_audio, samplerate = cache.get_full_audio()
        actual_frames = len(full_audio)
        total_duration = actual_frames / samplerate

        # Check if we're working with partial data
        is_partial = cache.is_partial()
        if is_partial:
            logger.warning(
                f"Working with partial audio data: {actual_frames} frames ({total_duration:.1f}s)"
            )

        # Take 3 samples: start, middle, end (or just 1 if too short)
        num_samples = 3 if total_duration > 90 else 1
        sample_duration = min(sample_duration, total_duration / num_samples)

        cutoff_freqs = []
        energy_ratios = []

        def _analyze_sample(i: int) -> Tuple[float, float]:
            """Analyze a single sample."""
            # Start position of this sample
            start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
            start_time = max(0, start_time)
            start_frame = int(start_time * samplerate)
            frames_to_read = int(sample_duration * samplerate)

            # Ensure we don't read beyond available data (for partial files)
            if start_frame + frames_to_read > actual_frames:
                frames_to_read = max(0, actual_frames - start_frame)
                if frames_to_read == 0:
                    logger.warning(f"Sample {i+1} beyond available data, skipping")
                    return 0.0, 0.0

            # Extract segment from cached full audio
            logger.debug(f"⚡ CACHE: Extracting segment {i+1}/{num_samples} from cached audio")
            data = full_audio[start_frame : start_frame + frames_to_read]

            # Convert to mono if stereo
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            else:
                data = data[:, 0]

            # Apply Hann window to reduce spectral leakage
            # PHASE 2 OPTIMIZATION: Use cached window
            window = get_hann_window(len(data))
            data_windowed = data * window

            # Calculate FFT
            # PHASE 3 OPTIMIZATION: Use parallel FFT
            # Limit FFT to 1 worker to avoid thread explosion in multiprocess context
            with set_workers(1):
                fft_vals = rfft(data_windowed)
            fft_freq = rfftfreq(len(data_windowed), 1 / samplerate)

            # Spectral magnitude (in dB)
            magnitude = np.abs(fft_vals)
            magnitude_db = 20 * np.log10(magnitude + 1e-10)

            # Detect cutoff frequency (pass samplerate for adaptive detection)
            cutoff_freq = detect_cutoff(fft_freq, magnitude_db, samplerate)

            # Calculate high frequency energy ratio (> 16 kHz)
            energy_ratio = calculate_high_frequency_energy(fft_freq, magnitude)

            return cutoff_freq, energy_ratio

        # PHASE 4 OPTIMIZATION: Parallelize sample analysis
        # Draw samples sequentially to avoid thread overhead
        results = [_analyze_sample(i) for i in range(num_samples)]
        cutoff_freqs = [r[0] for r in results]
        energy_ratios = [r[1] for r in results]

        # Take the WORST value (min) for cutoff to be more strict
        # A transcoded file will have a low cutoff in ALL samples
        # We use min() because even one sample with low cutoff indicates transcoding
        final_cutoff = min(cutoff_freqs)

        # For energy, we also take min() to be consistent
        final_energy = min(energy_ratios)

        # Calculate standard deviation of cutoffs to detect variable spectral content
        # Authentic FLACs often have high variance in cutoff frequency
        cutoff_std = float(np.std(cutoff_freqs)) if len(cutoff_freqs) > 1 else 0.0

        # Residual-floor metric for Rule 1's near-Nyquist 320 kbps gate. Only the
        # band where a 320k brickwall overlaps an authentic rolloff needs it, so we
        # skip the extra Welch pass everywhere else to keep the hot path fast.
        #
        # The top of this window was 0.95 * Nyquist until 2026-08-20, while Rule 1
        # rejects any 320 estimate from 0.94 * Nyquist up — so the residual was
        # computed across a 220 Hz slice the rule could never consult, and thrown
        # away. The window now stops where the rule stops.
        #
        # Widening the RULE to 0.95 instead was the other way to reconcile them, and
        # was measured before being rejected: in that slice 1 genuine file of 7 reads
        # below the -55 dB conviction floor. See rules/spectral.py's module docstring.
        nyquist = samplerate / 2.0
        residual_floor_db = float("nan")
        if 0.90 * nyquist <= final_cutoff < 0.94 * nyquist:
            residual_floor_db = compute_residual_floor_db(full_audio, samplerate)

        logger.info(
            f"Spectrum analysis: cutoff={final_cutoff:.0f} Hz, "
            f"energy_ratio={final_energy:.6f}, cutoff_std={cutoff_std:.1f}, "
            f"residual_floor_db={residual_floor_db:.1f}, samples={cutoff_freqs}"
        )

        return final_cutoff, final_energy, cutoff_std, residual_floor_db

    except Exception as e:
        logger.debug(f"Spectral analysis error: {e}")
        return 0, 0, 0, float("nan")


def detect_cutoff(  # noqa: C901
    frequencies: np.ndarray, magnitude_db: np.ndarray, samplerate: int = 44100
) -> float:
    """Detects cutoff frequency with a robust method adapted to sample rate.

    Method based on percentiles:
    1. Calculates reference energy in a safe zone (adaptive based on sample rate)
    2. Analyzes spectrum by slices starting from an adaptive frequency
    3. Detects a true cutoff = several consecutive slices below threshold

    Args:
        frequencies: Array of frequencies.
        magnitude_db: Array of magnitudes in dB.
        samplerate: Sample rate of the audio file (Hz).

    Returns:
        Detected cutoff frequency in Hz.
    """
    # Adaptive parameters based on sample rate
    # For high-res files (>48kHz), scale reference zone and scan start proportionally
    nyquist_freq = samplerate / 2.0

    # Calculate adaptive parameters (as percentage of Nyquist frequency)
    # Reference zone: 45-65% of Nyquist for standard files, adjusted for hi-res
    if samplerate <= 48000:
        # Standard resolution (44.1/48 kHz) - use fixed values optimized for MP3 detection
        reference_freq_low = spectral_config.REFERENCE_FREQ_LOW
        reference_freq_high = spectral_config.REFERENCE_FREQ_HIGH
        cutoff_scan_start = spectral_config.CUTOFF_SCAN_START
    else:
        # High resolution (88.2/96/176.4/192 kHz) - scale proportionally
        scale_factor = samplerate / 44100.0
        reference_freq_low = int(spectral_config.REFERENCE_FREQ_LOW * scale_factor)
        reference_freq_high = int(spectral_config.REFERENCE_FREQ_HIGH * scale_factor)
        cutoff_scan_start = int(spectral_config.CUTOFF_SCAN_START * scale_factor)

    # Focus on frequencies > reference_freq_low
    high_freq_mask = frequencies > reference_freq_low
    if not np.any(high_freq_mask):
        return float(frequencies[-1])

    freq_high = frequencies[high_freq_mask]
    mag_high = magnitude_db[high_freq_mask]

    # Aggressive smoothing to ignore temporal variations
    if len(mag_high) > 100:
        from scipy.ndimage import uniform_filter1d

        mag_smooth = uniform_filter1d(mag_high, size=100)
    else:
        mag_smooth = mag_high

    # Slice analysis
    tranche_size_hz = spectral_config.TRANCHE_SIZE
    freq_max = freq_high[-1]

    # Calculate reference (median energy between reference_freq_low-reference_freq_high)
    ref_mask = (freq_high >= reference_freq_low) & (freq_high <= reference_freq_high)
    if np.any(ref_mask):
        reference_energy = np.percentile(mag_smooth[ref_mask], 50)
    else:
        reference_energy = np.max(mag_smooth)

    # Cutoff threshold
    cutoff_threshold = reference_energy - spectral_config.CUTOFF_THRESHOLD_DB

    # Slice by slice analysis starting from cutoff_scan_start
    current_freq = cutoff_scan_start
    consecutive_low = 0

    while current_freq < freq_max:
        tranche_mask = (freq_high >= current_freq) & (freq_high < current_freq + tranche_size_hz)

        if np.any(tranche_mask):
            # Look at 75th percentile to ensure no peaks
            tranche_energy = np.percentile(mag_smooth[tranche_mask], 75)

            # If this slice is very low
            if tranche_energy < cutoff_threshold:
                consecutive_low += 1

                # If N consecutive slices are low, it's a true cutoff
                if consecutive_low >= spectral_config.CONSECUTIVE_LOW_THRESHOLD:
                    # Return start of drop
                    detected_cutoff = current_freq - (tranche_size_hz * (consecutive_low - 1))
                    logger.debug(
                        f"Cutoff detected at {detected_cutoff:.0f} Hz "
                        f"({consecutive_low} consecutive low slices)"
                    )
                    return detected_cutoff
            else:
                consecutive_low = 0

        current_freq += tranche_size_hz

    # No cutoff detected with slice method -> try energy-based fallback
    # This catches MP3 upscales that have noise in high frequencies
    logger.debug("No cutoff detected with slice method, trying energy-based detection")

    # Energy-based detection: find where 90% of cumulative energy is reached
    # Convert dB back to linear magnitude: magnitude = 10^(magnitude_db/20)
    magnitude_linear = 10 ** (magnitude_db / 20.0)
    energy = magnitude_linear**2  # Energy is square of linear magnitude
    cumulative_energy = np.cumsum(energy)
    total_energy = cumulative_energy[-1]

    if total_energy > 0:
        # Find where we reach 90% of total energy
        energy_90_idx = np.where(cumulative_energy >= 0.90 * total_energy)[0]
        if len(energy_90_idx) > 0:
            energy_cutoff = frequencies[energy_90_idx[0]]

            # If energy-based cutoff is significantly lower than Nyquist, use it
            # This indicates energy concentration in lower frequencies (MP3 signature)
            # BUT: Only if it's in the realistic MP3 cutoff range (15kHz+)
            # Very low cutoffs (< 10kHz) are usually just bass concentration, not transcoding
            if 15000 < energy_cutoff < nyquist_freq * 0.95:  # Realistic MP3 range
                logger.debug(
                    f"Energy-based cutoff detected at {energy_cutoff:.0f} Hz (90% energy threshold)"
                )
                return float(energy_cutoff)
            elif energy_cutoff < 15000:
                logger.debug(f"Energy concentration at {energy_cutoff:.0f} Hz (bass, not cutoff)")
                # Bass concentration but no MP3 cutoff signature - likely authentic
                return float(freq_max)

    # If energy-based also didn't find anything suspicious, truly authentic
    logger.debug(f"No cutoff detected, full spectrum up to {freq_max:.0f} Hz")
    return float(freq_max)


class EdgeReading(NamedTuple):
    """What ``detect_cutoff`` cannot say, because it can only return one float.

    ``detect_cutoff`` returns Nyquist in three unrelated situations: the spectrum
    genuinely runs to the top, the energy is concentrated in the bass and no wall was
    looked for, and nothing was found at all. A caller reading 22,050 Hz cannot tell
    a measurement from a shrug, and any median computed over a mixture of the two is
    partly a median of failures.

    This project already knows that lesson from Rule 15's mono gate — "the correct
    behaviour being silence, not a low score, because a low score is still an
    opinion" — and did not apply it here. Jamie Dodd's engine returns an explicit
    *no wall found* sentinel, which is why his lawful population reads as a sentinel
    rather than as a pile of numbers near Nyquist.

    ``found`` is that sentinel. ``width_hz`` is the second half, and it is the more
    valuable one.

    Why width
    ---------
    His measurement, given after retracting the frequency he had handed over: an edge
    POSITION does not separate lawful masters from MP3 transcodes at all. Of his 17
    real 2009 DJ-master MP3s, 11 carry a sharp wall topping out at 21,479 Hz and 6
    have no wall up to 22,023 Hz — while 28 of his 75 lawful masters sit above 21,570.
    Both populations live on both sides of any line.

    What separates is how FAST the spectrum falls. In his engine frequency is only a
    gate (21,350-21,650 Hz) and the test underneath is a transition width, used as a
    conjunction rather than a threshold: his MP3 positives return 390-519 Hz.

    With his own caveat, given unprompted: of 75 lawful files inside that window, 5
    do show a sharp wall (409-900 Hz). Width does the work and is still not a
    separator on its own, which is why the conjunction exists.

    Our numbers are NOT comparable to his
    -------------------------------------
    Different smoothing, different reference band, different definition of where a
    transition starts and stops. His own standing rule applies to us here: never
    quote an absolute edge figure without naming the instrument that produced it. So
    ``width_hz`` is calibrated against our own corpus or not at all, and his 390-519
    is context, never a threshold to import.

    MEASURED 2026-08-21: width does not become a rule here
    -------------------------------------------------------
    ``ml/edge_width_probe.py``, 120 genuine and 40 per arm. Width separates at AUC
    0.48-0.62 — 0.48 on ``aac_ff320``, i.e. below chance — and at a 5 % genuine cost
    it fires on 0-5 % of each arm. Against a stereo family at 92 % and an MDCT rule
    at AUC 0.99, that is not an axis.

    It was measured twice. The first run reused ``detect_cutoff``'s size-100
    smoothing kernel and was invalid: at 2.69 Hz per bin that kernel spans 269 Hz,
    and every width it produced (137-215 Hz median) sat below its own filter. The
    synthetic control passed anyway, because a step function survives any kernel —
    the same failure as the MP3-geometry probe that validated against a control
    sharing its defect. Fixing it to 9 bins gave the statistic real dynamic range
    (a synthetic brickwall went 70 Hz -> 11 Hz against a rolloff at ~200 Hz) and
    changed the corpus answer not at all.

    So the honest statement is narrow: **width does not work bolted onto our
    edge-finder.** Our position comes from a 269 Hz-smoothed curve and the width
    search starts 250 Hz below it, so the two halves are not one coherent
    instrument. This says nothing about whether it works in Provir's, where it does.

    One thing did fall out, and it is not a result
    ----------------------------------------------
    Exactly 3 of our 39 measurable genuine files read as near-perfect brickwalls —
    2.7 Hz, 0.0 Hz and 18.8 Hz, at 21,000 / 21,000 / 20,250 Hz. Either they are
    transcodes mislabelled in our own genuine corpus, or the statistic is spurious on
    them. **This cannot be settled with the statistic under test**, and excluding them
    because they look like transcodes is precisely the circularity this whole exchange
    is about. They are adjudication candidates for ``ml/wild_fake_ledger.py``, whose
    ``basis`` field exists for this, and nothing more until a human with evidence
    rules on them.

    For the record, and stated as a bound rather than as a finding: if all three were
    transcodes, the 5 %-cost fire rates would rise to 7.5-25 % per arm. Still not an
    axis, so the question does not change the decision — which is the only reason it
    is safe to write down.
    """

    cutoff_hz: float
    found: bool
    width_hz: float


# Where the transition is considered to start, relative to the in-band reference.
# -6 dB rather than -3: at -3 dB an ordinary spectral dip opens a transition that
# never closes, and the width then measures the music.
EDGE_START_DROP_DB = 6.0

# Smoothing for the WIDTH measurement, in bins — deliberately NOT the size-100
# kernel ``detect_cutoff`` uses to find the edge.
#
# The first version of this function reused that kernel and produced a null: AUC
# 0.51-0.64 across six arms, with every measured width (137-215 Hz median) sitting
# BELOW the kernel's own span. At 16384-point FFT and 44.1 kHz a bin is 2.69 Hz, so
# size=100 smears across 269 Hz — the statistic was reading the filter.
#
# Aggressive smoothing is right for finding WHERE an edge is and wrong for measuring
# HOW STEEP it is, and reusing it was the same mistake as the earlier MP3-geometry
# probe that validated against a synthetic control sharing its own defect: the
# synthetic brickwall passed because a step function survives any kernel.
WIDTH_SMOOTH_BINS = 9


def detect_cutoff_detailed(
    frequencies: np.ndarray, magnitude_db: np.ndarray, samplerate: int = 44100
) -> EdgeReading:
    """``detect_cutoff`` plus the two things it cannot express: a sentinel and a width.

    Deliberately a SEPARATE function. ``detect_cutoff`` feeds every scoring rule, and
    changing what it returns would change verdicts; this one is for measurement
    contexts — arms, probes, published tables — where averaging a failure into a
    median is the actual harm. See :class:`EdgeReading`.
    """
    cutoff = float(detect_cutoff(frequencies, magnitude_db, samplerate))
    nyquist = samplerate / 2.0

    # detect_cutoff signals "nothing found" by returning the top of the band. That is
    # the ambiguity this function exists to resolve, so it is resolved here rather
    # than by the caller guessing.
    if cutoff >= frequencies[-1] - 1e-6 or cutoff >= 0.999 * nyquist:
        return EdgeReading(cutoff_hz=cutoff, found=False, width_hz=float("nan"))

    if samplerate <= 48000:
        ref_low = spectral_config.REFERENCE_FREQ_LOW
        ref_high = spectral_config.REFERENCE_FREQ_HIGH
    else:
        scale = samplerate / 44100.0
        ref_low = int(spectral_config.REFERENCE_FREQ_LOW * scale)
        ref_high = int(spectral_config.REFERENCE_FREQ_HIGH * scale)

    ref_mask = (frequencies >= ref_low) & (frequencies <= ref_high)
    if not np.any(ref_mask):
        return EdgeReading(cutoff_hz=cutoff, found=True, width_hz=float("nan"))
    reference = float(np.median(magnitude_db[ref_mask]))

    # Lightly smoothed — see WIDTH_SMOOTH_BINS. The edge POSITION comes from
    # detect_cutoff's own heavily-smoothed curve; the STEEPNESS has to come from a
    # curve that still has steepness in it.
    above = frequencies > ref_low
    freq_high = frequencies[above]
    mag_high = magnitude_db[above]
    if len(mag_high) > WIDTH_SMOOTH_BINS:
        from scipy.ndimage import uniform_filter1d

        mag_high = uniform_filter1d(mag_high, size=WIDTH_SMOOTH_BINS)

    start_level = reference - EDGE_START_DROP_DB
    end_level = reference - spectral_config.CUTOFF_THRESHOLD_DB

    # Search forward from the detected edge minus one slice: the edge is reported as
    # the START of the drop, so the transition begins at or just before it.
    search = freq_high >= (cutoff - spectral_config.TRANCHE_SIZE)
    if not np.any(search):
        return EdgeReading(cutoff_hz=cutoff, found=True, width_hz=float("nan"))
    freq_s, mag_s = freq_high[search], mag_high[search]

    below_start = np.flatnonzero(mag_s <= start_level)
    below_end = np.flatnonzero(mag_s <= end_level)
    if below_start.size == 0 or below_end.size == 0:
        # The spectrum never reaches the floor above the edge — a rolloff that fades
        # rather than a wall that stops. Not a width, and not a zero either.
        return EdgeReading(cutoff_hz=cutoff, found=True, width_hz=float("nan"))

    first_start = float(freq_s[below_start[0]])
    reaches_floor = below_end[below_end >= below_start[0]]
    if reaches_floor.size == 0:
        return EdgeReading(cutoff_hz=cutoff, found=True, width_hz=float("nan"))

    width = float(freq_s[reaches_floor[0]]) - first_start
    return EdgeReading(cutoff_hz=cutoff, found=True, width_hz=max(width, 0.0))


def calculate_high_frequency_energy(frequencies: np.ndarray, magnitude: np.ndarray) -> float:
    """Calculates energy ratio in high frequencies (> HIGH_FREQ_THRESHOLD).

    Checks for CONTINUOUS presence of energy in high frequencies.

    Args:
        frequencies: Array of frequencies.
        magnitude: Array of magnitudes.

    Returns:
        Average energy ratio in high frequencies.
    """
    high_freq_idx = frequencies > spectral_config.HIGH_FREQ_THRESHOLD
    if not np.any(high_freq_idx):
        return 0.0

    # Analysis by 1 kHz slices
    tranche_energies: list[float] = []
    for f_start in range(spectral_config.HIGH_FREQ_THRESHOLD, int(frequencies[-1]), 1000):
        f_mask = (frequencies >= f_start) & (frequencies < f_start + 1000)
        if np.any(f_mask):
            tranche_energy = float(np.sum(magnitude[f_mask] ** 2))
            total_energy = float(np.sum(magnitude**2))
            tranche_energies.append(tranche_energy / total_energy if total_energy > 0 else 0.0)

    # A real FLAC has energy in ALL slices
    return float(np.mean(tranche_energies)) if tranche_energies else 0.0


def analyze_segment_consistency(  # noqa: C901
    filepath: Path, progressive: bool = True, cache: "Optional[AudioCache]" = None
) -> Tuple[List[float], float]:
    """Analyzes segments of the file to detect cutoff consistency (OPTIMIZED - Progressive).

    Phase 2 Optimization: Progressive analysis
    - Start with 2 segments (Start + End) for quick check
    - If coherent (variance < 500 Hz), STOP (60% of cases)
    - Otherwise, analyze 3 more segments (25%, 50%, 75%)

    PHASE 1 OPTIMIZATION: Uses AudioCache to avoid multiple file reads.

    Segments: Start (5%), 25%, 50%, 75%, End (95%)

    Args:
        filepath: Path to the audio file.
        progressive: If True, use progressive analysis (default). If False, analyze all 5 segments.
        cache: Optional AudioCache instance for optimization.

    Returns:
        Tuple (list_of_cutoffs, cutoff_variance)
    """
    try:
        # Create cache if not provided
        if cache is None:
            from .audio_cache import AudioCache

            cache = AudioCache(filepath)

        info = sf.info(filepath)
        total_duration = info.duration
        samplerate = info.samplerate

        segment_duration = 10.0  # 10 seconds per segment

        def analyze_single_segment(center_ratio: float) -> float:
            """Analyze a single segment and return its cutoff."""
            center_time = total_duration * center_ratio
            start_time = max(0, center_time - (segment_duration / 2))

            # Ensure we don't go past end
            if start_time + segment_duration > total_duration:
                start_time = max(0, total_duration - segment_duration)

            start_frame = int(start_time * samplerate)
            frames_to_read = int(segment_duration * samplerate)

            try:
                # OPTIMIZATION: Use cache instead of direct sf.read
                logger.debug(f"⚡ CACHE: Reading segment at {center_ratio*100:.0f}% via cache")
                data, _ = cache.get_segment(start_frame, frames_to_read)

                if len(data) < frames_to_read and len(data) == 0:
                    return 0.0

                # Convert to mono
                if data.shape[1] > 1:
                    data = np.mean(data, axis=1)
                else:
                    data = data[:, 0]

                # Windowing
                # PHASE 2 OPTIMIZATION: Use cached window
                window = get_hann_window(len(data))
                data_windowed = data * window

                # FFT
                # PHASE 3 OPTIMIZATION: Use parallel FFT
                # Limit FFT to 1 worker
                with set_workers(1):
                    fft_vals = rfft(data_windowed)
                fft_freq = rfftfreq(len(data_windowed), 1 / samplerate)

                magnitude = np.abs(fft_vals)
                magnitude_db = 20 * np.log10(magnitude + 1e-10)

                cutoff = detect_cutoff(fft_freq, magnitude_db)
                return cutoff

            except Exception as e:
                logger.warning(f"Error analyzing segment at {center_ratio*100:.0f}%: {e}")
                return 0.0

        # PHASE 1: Analyze Start + End (2 segments)
        # Analyze Start + End (Sequential)
        cutoffs = [analyze_single_segment(0.05), analyze_single_segment(0.95)]

        # Filter valid cutoffs
        valid_cutoffs = [c for c in cutoffs if c > 0]

        if len(valid_cutoffs) < 2:
            logger.warning(
                "OPTIMIZATION R10: Less than 2 valid segments, cannot determine consistency"
            )
            return cutoffs, 0.0

        # Calculate initial variance
        variance = float(np.std(valid_cutoffs))

        logger.debug(
            f"OPTIMIZATION R10: Phase 1 - Start={cutoffs[0]:.0f} Hz, End={cutoffs[1]:.0f} Hz, Variance={variance:.1f} Hz"
        )

        # PHASE 2: Progressive decision
        if progressive:
            # If variance < 500 Hz, segments are coherent -> STOP
            if variance < 500:
                logger.info(
                    f"⚡ OPTIMIZATION R10: Early stop - Coherent segments (variance {variance:.1f} < 500 Hz)"
                )
                # Return only 2 segments (optimization)
                return cutoffs, variance

            # If variance > 1000 Hz, already know it's dynamic -> STOP
            if variance > 1000:
                logger.info(
                    f"⚡ OPTIMIZATION R10: Early stop - High variance detected ({variance:.1f} > 1000 Hz)"
                )
                return cutoffs, variance

            # Otherwise (500 <= variance <= 1000), need more data
            logger.info(
                f"OPTIMIZATION R10: Expanding to 5 segments (variance {variance:.1f} in grey zone)"
            )

        # PHASE 3: Analyze middle segments (25%, 50%, 75%)
        # Analyze middle segments (Sequential)
        middle_segments = [0.25, 0.50, 0.75]
        results = {r: analyze_single_segment(r) for r in middle_segments}

        # Insert in correct position to maintain order
        cutoffs.insert(1, results[0.25])
        cutoffs.insert(2, results[0.50])
        cutoffs.insert(3, results[0.75])

        # Recalculate variance with all 5 segments
        valid_cutoffs = [c for c in cutoffs if c > 0]

        if len(valid_cutoffs) > 1:
            variance = float(np.std(valid_cutoffs))
        else:
            variance = 0.0

        logger.debug(
            f"OPTIMIZATION R10: Phase 3 - All 5 segments analyzed, final variance={variance:.1f} Hz"
        )

        return cutoffs, variance

    except Exception as e:
        logger.error(f"Segment consistency analysis failed: {e}")
        return [], 0.0
