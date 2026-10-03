"""Spectral analysis of audio files."""

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING, List, NamedTuple, Optional, Sequence, Tuple

import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq, set_workers

from ..config import spectral_config
from .window_cache import get_hann_window

if TYPE_CHECKING:
    from .audio_cache import AudioCache

logger = logging.getLogger(__name__)

# Top of the band every "above the edge" reading stops at, as a fraction of
# Nyquist: the last few bins carry the anti-alias filter, not the music.
FLOOR_TOP_FRACTION = 0.993

# A cutoff at or above this fraction of Nyquist (or at the last FFT bin) is
# ``detect_cutoff`` saying "nothing found", not an edge.
_NO_EDGE_FRACTION = 0.999


def _reference_band(samplerate: int) -> Tuple[int, int, int]:
    """(reference low, reference high, scan start) in Hz for this sample rate.

    Standard resolution (44.1/48 kHz) uses the fixed values optimised for MP3
    detection; hi-res (88.2/96/176.4/192 kHz) scales them proportionally,
    truncated to whole Hz as they always were. The ``<= 48000`` boundary and the
    ``int()`` truncation are load-bearing: every cutoff the scan returns lands on
    the grid ``scan_start + k * TRANCHE_SIZE``.
    """
    if samplerate <= 48000:
        return (
            spectral_config.REFERENCE_FREQ_LOW,
            spectral_config.REFERENCE_FREQ_HIGH,
            spectral_config.CUTOFF_SCAN_START,
        )
    scale = samplerate / 44100.0
    return (
        int(spectral_config.REFERENCE_FREQ_LOW * scale),
        int(spectral_config.REFERENCE_FREQ_HIGH * scale),
        int(spectral_config.CUTOFF_SCAN_START * scale),
    )


def _no_edge(cutoff_hz: float, frequencies: np.ndarray, samplerate: int) -> bool:
    """True when ``cutoff_hz`` is ``detect_cutoff``'s "nothing found" reading."""
    return (
        cutoff_hz >= _NO_EDGE_FRACTION * (samplerate / 2.0) or cutoff_hz >= frequencies[-1] - 1e-6
    )


def _magnitude_spectrum(
    data: np.ndarray, samplerate: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Mono-mix, Hann-window and FFT one block of ``(frames, channels)`` audio.

    Returns ``(frequencies, magnitude, magnitude_db)``. The FFT runs on one
    worker: in a process pool, threads inside the FFT multiply instead of adding.
    The expressions are the engine's own, in their original order; nothing here
    may be reassociated, as every cutoff reading rests on them.
    """
    if data.shape[1] > 1:
        mono = np.mean(data, axis=1)
    else:
        mono = data[:, 0]
    windowed = mono * get_hann_window(len(mono))
    with set_workers(1):
        fft_vals = rfft(windowed)
    frequencies = rfftfreq(len(windowed), 1 / samplerate)
    magnitude = np.abs(fft_vals)
    magnitude_db = 20 * np.log10(magnitude + 1e-10)
    return frequencies, magnitude, magnitude_db


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
        top_mask = (freq >= 0.961 * nyq) & (freq <= FLOOR_TOP_FRACTION * nyq)
        if not (np.any(ref_mask) and np.any(top_mask)):
            return float("nan")
        ref = float(np.median(magnitude_db[ref_mask]))
        top = float(np.median(magnitude_db[top_mask]))
        return top - ref
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"Residual floor computation failed: {e}")
        return float("nan")


# Edge-step instrument (Rule 1's gate D, v1.13.15). How far the spectrum FALLS
# across the detected edge, read on the same 250 Hz cells detect_cutoff scans,
# relative to the same 10-14 kHz reference.
#
# Why it exists: detect_cutoff answers WHERE the spectrum first sits 30 dB under
# the reference for two cells. On a codec low-pass that is a wall — the level
# drops 20-40 dB inside 500 Hz. On a master that was rolled off gently (issue #8,
# fourth round: two rips of the same track, both falling ~6 dB/kHz from 12 to
# 19 kHz) the same scan reports 17,250 Hz, and Rule 1's table turns that
# POSITION into a "192 kbps signature". The position of an edge cannot tell a
# slope from a wall; the size of the step across it can. detect_cutoff_detailed's
# transition width cannot either: it measures from the reported edge forward,
# and on a slope that is already 30 dB down when the scan first notices it, both
# ends of the transition are behind the start of the search, so it reads 0 Hz —
# a perfect wall — on the reporter's file. Measured 2026-09-08, ml/edge_step_probe.py.
#
# The reading: over the zone [cutoff - 4 cells, cutoff + 4 cells), the largest
# fall between a cell and the cell two further up (500 Hz). A LAME wall reads
# 18-45 dB there on full-length tracks; the reporter's slope reads 4-6 dB.
EDGE_ZONE_CELLS = 4
EDGE_STEP_CELLS = 2


def cell_profile_db(
    frequencies: np.ndarray, magnitude_db: np.ndarray, samplerate: int = 44100
) -> Tuple[float, List[float]]:
    """Median level of each 250 Hz cell from the scan start up to Nyquist.

    Levels are relative to the median of the 10-14 kHz reference band, on the
    raw (unsmoothed) magnitude, so that a step keeps its size. Returns the
    first cell's start frequency and the list of cell levels; a cell with no
    bins is NaN. Scales with the sample rate the way ``detect_cutoff`` does.
    """
    ref_low, ref_high, first = _reference_band(samplerate)
    ref_mask = (frequencies >= ref_low) & (frequencies <= ref_high)
    if not np.any(ref_mask):
        return float(first), []
    reference = float(np.median(magnitude_db[ref_mask]))
    cell = spectral_config.TRANCHE_SIZE
    cells: List[float] = []
    k = first
    while k + cell <= samplerate / 2.0 + 1:
        sel = (frequencies >= k) & (frequencies < k + cell)
        cells.append(
            float(np.median(magnitude_db[sel]) - reference) if np.any(sel) else float("nan")
        )
        k += cell
    return float(first), cells


def edge_step_db(
    frequencies: np.ndarray, magnitude_db: np.ndarray, cutoff_hz: float, samplerate: int = 44100
) -> float:
    """Largest fall over two adjacent cells within four cells of the edge, in dB.

    NaN — not 0.0 — when there is no edge to read (the cutoff sits at the top
    of the band, so nothing was found) or when the zone has no cells. A NaN
    must be treated as "unknown" by every consumer; Rule 1's gate D lets an
    unknown step through, exactly as gate A lets an unknown wander through.
    """
    if _no_edge(cutoff_hz, frequencies, samplerate):
        return float("nan")
    first, cells = cell_profile_db(frequencies, magnitude_db, samplerate)
    if not cells:
        return float("nan")
    i0 = int((cutoff_hz - first) // spectral_config.TRANCHE_SIZE)
    best = float("nan")
    for i in range(i0 - EDGE_ZONE_CELLS, i0 + EDGE_ZONE_CELLS):
        j = i + EDGE_STEP_CELLS
        if i < 0 or j >= len(cells):
            continue
        fall = cells[i] - cells[j]
        if np.isnan(fall):
            continue
        if np.isnan(best) or fall > best:
            best = fall
    return best


# Floor-above-the-edge instrument (Rule 1's depth gate, v1.13.16). What is LEFT
# above the detected edge, read on the same 250 Hz cells as the step, relative
# to the same 10-14 kHz reference.
#
# Why it exists: gate D reads how far the spectrum falls across two cells, and
# a codec low-pass with a gentle filter falls under its 12 dB bar — two Beatport
# AIFFs of a track whose CD and vinyl editions run to 20.5-21 kHz read 7.7 and
# 8.8 dB at 16 kHz and were cleared as "a roll-off, not a codec wall". Over the
# next 2 kHz they fall 25 dB, then nothing: digital silence to Nyquist. A
# mastering roll-off (issue #8's two rips) keeps falling into an analogue or
# dither floor instead, -41 to -44 dB on the same reading. The step cannot tell
# those apart; the floor above the edge can. Measured 2026-09-15 from the gate
# D probe's cell profiles: 0 of 155 genuine files under -58 dB below 19.5 kHz
# (deepest -55.2, a hard wall), the two Beatport files at -62.8 and -65.1.
# See ml/exchange/DEPTH_GATE_REGISTRATION_2026-09-15.md.
#
# The reading: the median cell level from (cutoff + FLOOR_GAP_HZ) up to
# 0.993 x Nyquist. NaN when fewer than FLOOR_MIN_CELLS fit, which is the case
# from ~19.9 kHz up at 44.1 kHz: there the fixed-band residual floor
# (compute_residual_floor_db) rules and this instrument abstains.
FLOOR_GAP_HZ = 1000.0
FLOOR_MIN_CELLS = 4


def floor_above_edge_db(
    frequencies: np.ndarray, magnitude_db: np.ndarray, cutoff_hz: float, samplerate: int = 44100
) -> float:
    """Median level of the band above the edge, relative to the reference, in dB.

    NaN — not 0.0 — when there is no edge to read or when fewer than
    ``FLOOR_MIN_CELLS`` whole 250 Hz cells fit between ``cutoff + FLOOR_GAP_HZ``
    and ``FLOOR_TOP_FRACTION`` x Nyquist. A NaN must be treated as "unknown"
    by every consumer: Rule 1's depth gate then changes nothing, exactly as an
    unknown step leaves gate D alone.
    """
    nyquist = samplerate / 2.0
    if _no_edge(cutoff_hz, frequencies, samplerate):
        return float("nan")
    first, cells = cell_profile_db(frequencies, magnitude_db, samplerate)
    if not cells:
        return float("nan")
    cell = spectral_config.TRANCHE_SIZE
    lo = int(math.ceil((cutoff_hz + FLOOR_GAP_HZ - first) / cell))
    # The last cell whose whole span sits under the top fraction.
    hi = int((FLOOR_TOP_FRACTION * nyquist - first) // cell) - 1
    lo = max(lo, 0)
    hi = min(hi, len(cells) - 1)
    band = [c for c in cells[lo : hi + 1] if not np.isnan(c)]
    if len(band) < FLOOR_MIN_CELLS:
        return float("nan")
    return float(np.median(band))


# Low-wall instrument (v1.17.0). A codec wall BELOW the reference band.
#
# Why it exists: detect_cutoff measures every cell against the 10-14 kHz
# reference and starts its scan at 14 kHz. Under ~64 kbps an encoder's own
# low-pass sits at 3-11 kHz, so the reference band is itself the codec's
# floor: the scan compares noise with noise, finds no drop, and reports the
# top of the band — "no cutoff". Rule 8 then read that 22,050 Hz as a full
# spectrum and granted -50: the rule that protects full-band recordings was
# protecting files whose music stops at 4 kHz (measured 2026-09-04,
# ml/sbr_arm.py: lc_aac_32k read AUTHENTIC 6 of 6, ceiling 6,746 Hz).
#
# Neither level separates them: a 1920s 78 rpm transfer in the audit corpus
# keeps its 10-14 kHz band as far under its midrange as an AAC 32k does, and
# at the same absolute level. What separates is the SHAPE. A codec stops: the
# spectrum falls 15-50 dB inside 500 Hz and nothing comes back. A dark or old
# recording declines, ~10 dB per 500 Hz at the steepest, into its own floor.
#
# The reading, on 250 Hz cells of the same FFT: at each cell boundary f from
# 2 kHz to 14 kHz, the step = mean of the two cells below f minus mean of the
# two above (500 Hz each side), and the depth = the same "below" level minus
# the 90th percentile of the cells from f + 1 kHz to 16 kHz. The lowest f
# whose step and depth both clear their bars is the wall. The depth stops at
# 16 kHz whatever the sample rate: on a 96 kHz field recording the empty band
# above 20 kHz would otherwise make any tonal dip read as a wall (measured).
#
# Only consulted when detect_cutoff found nothing, so every other reading is
# untouched; and since detect_cutoff never returns a value under 14 kHz, a
# cutoff under 14 kHz is always a low-wall reading (see is_low_wall_reading).
# See ml/exchange/LOW_WALL_REGISTRATION_2026-09-25.md.
LOW_WALL_FROM_HZ = 2000.0
LOW_WALL_TO_HZ = 14000.0
LOW_WALL_DEPTH_TOP_HZ = 16000.0
LOW_WALL_STEP_DB = 15.0
LOW_WALL_DEPTH_DB = 30.0
LOW_WALL_CELL_HZ = 250.0
_LOW_WALL_BASE_HZ = 1000.0


def low_wall_hz(frequencies: np.ndarray, magnitude_db: np.ndarray, samplerate: int) -> float:
    """The frequency of a codec wall below the reference band, or NaN.

    NaN — not a frequency, and not the top of the band — when no boundary in
    [``LOW_WALL_FROM_HZ``, ``LOW_WALL_TO_HZ``] clears both bars. A NaN means
    "no low wall", and the caller keeps detect_cutoff's reading unchanged.
    """
    top = min(LOW_WALL_DEPTH_TOP_HZ, FLOOR_TOP_FRACTION * samplerate / 2.0)
    edges = np.arange(_LOW_WALL_BASE_HZ, top - LOW_WALL_CELL_HZ + 1, LOW_WALL_CELL_HZ)
    lo_idx = np.searchsorted(frequencies, edges)
    hi_idx = np.searchsorted(frequencies, edges + LOW_WALL_CELL_HZ)
    cells = np.array(
        [float(np.median(magnitude_db[a:b])) if b > a else np.nan for a, b in zip(lo_idx, hi_idx)]
    )

    def clears(f: float) -> float:
        """The step at ``f`` if both bars are cleared there, else NaN."""
        i = int((f - _LOW_WALL_BASE_HZ) // LOW_WALL_CELL_HZ)
        if i + 4 >= len(cells) or i < 2:
            return float("nan")
        below = float(np.mean(cells[i - 2 : i]))
        step = below - float(np.mean(cells[i : i + 2]))
        above = cells[i + 4 :]
        above = above[~np.isnan(above)]
        if not above.size or np.isnan(step):
            return float("nan")
        depth = below - float(np.percentile(above, 90))
        if step >= LOW_WALL_STEP_DB and depth >= LOW_WALL_DEPTH_DB:
            return step
        return float("nan")

    f = LOW_WALL_FROM_HZ
    while f <= LOW_WALL_TO_HZ:
        step = clears(f)
        if not math.isnan(step):
            # The two-cell means straddle a wall, so the first boundary to clear
            # the bars sits one cell early. Report the steepest boundary of the
            # run that clears them: where the wall is, not where it is first seen.
            best_f, best_step = f, step
            nxt = f + LOW_WALL_CELL_HZ
            while nxt <= LOW_WALL_TO_HZ:
                s = clears(nxt)
                if math.isnan(s):
                    break
                if s > best_step:
                    best_f, best_step = nxt, s
                nxt += LOW_WALL_CELL_HZ
            return float(best_f)
        f += LOW_WALL_CELL_HZ
    return float("nan")


def is_low_wall_reading(cutoff_hz: float) -> bool:
    """True when a cutoff can only have come from :func:`low_wall_hz`.

    ``detect_cutoff`` scans from ``CUTOFF_SCAN_START`` (14 kHz, scaled up for
    hi-res) and its energy fallback only answers above 15 kHz, so it never
    returns a value in [``LOW_WALL_FROM_HZ``, 14 kHz). A reading there is a
    low wall. 0 (an analysis failure) is not.
    """
    return LOW_WALL_FROM_HZ <= cutoff_hz < spectral_config.CUTOFF_SCAN_START


def _window_bounds(
    i: int, num_samples: int, total_duration: float, sample_duration: float, samplerate: int
) -> Tuple[int, int]:
    """(start frame, frames to read) of window ``i`` of ``num_samples``.

    Windows are centred at ``(i + 1) / (num_samples + 1)`` of the duration and
    clamped at the start of the file.
    """
    start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
    start_time = max(0, start_time)
    return int(start_time * samplerate), int(sample_duration * samplerate)


def _analyze_window(
    full_audio: np.ndarray,
    samplerate: int,
    bounds: Tuple[int, int],
    actual_frames: int,
    i: int,
    num_samples: int,
) -> Tuple[float, float, float, float]:
    """Cutoff, HF energy ratio, edge step and floor above the edge of one window.

    Returns ``(0.0, 0.0, nan, nan)`` for a window that lies entirely beyond the
    audio actually read (partial files).
    """
    start_frame, frames_to_read = bounds
    # Ensure we don't read beyond available data (for partial files)
    if start_frame + frames_to_read > actual_frames:
        frames_to_read = max(0, actual_frames - start_frame)
        if frames_to_read == 0:
            logger.warning(f"Sample {i+1} beyond available data, skipping")
            return 0.0, 0.0, float("nan"), float("nan")

    logger.debug(f"⚡ CACHE: Extracting segment {i+1}/{num_samples} from cached audio")
    data = full_audio[start_frame : start_frame + frames_to_read]
    fft_freq, magnitude, magnitude_db = _magnitude_spectrum(data, samplerate)

    # Detect cutoff frequency (pass samplerate for adaptive detection)
    cutoff_freq = detect_cutoff(fft_freq, magnitude_db, samplerate)

    # Nothing found against the 10-14 kHz reference: look for a codec
    # wall below it before believing a full spectrum (low-wall instrument).
    if _no_edge(cutoff_freq, fft_freq, samplerate):
        wall = low_wall_hz(fft_freq, magnitude_db, samplerate)
        if not math.isnan(wall):
            logger.info(
                f"Low wall at {wall:.0f} Hz under an empty reference band "
                f"(detect_cutoff read {cutoff_freq:.0f} Hz)"
            )
            cutoff_freq = wall

    # Calculate high frequency energy ratio (> 16 kHz)
    energy_ratio = calculate_high_frequency_energy(fft_freq, magnitude)
    # How far the spectrum falls across that edge (Rule 1's gate D).
    step_db = edge_step_db(fft_freq, magnitude_db, cutoff_freq, samplerate)
    # What is left above that edge (Rule 1's depth gate).
    floor_db = floor_above_edge_db(fft_freq, magnitude_db, cutoff_freq, samplerate)
    return cutoff_freq, energy_ratio, step_db, floor_db


def analyze_spectrum(
    filepath: Path, sample_duration: float = 30.0, cache: "Optional[AudioCache]" = None
) -> Tuple[float, float, float, float, float, float]:
    """Analyzes the frequency spectrum of the audio file.

    Takes multiple samples at different times for robustness.
    OPTIMIZED: Uses AudioCache to avoid multiple file reads.

    Args:
        filepath: Path to the audio file.
        sample_duration: Duration in seconds to analyze.
        cache: Optional AudioCache instance for optimization.

    Returns:
        Tuple (cutoff_frequency, energy_ratio, cutoff_std, residual_floor_db,
        edge_step_db, floor_above_db) where:
        - cutoff_frequency: detected cutoff frequency in Hz
        - energy_ratio: energy ratio in high frequencies
        - cutoff_std: cutoff wander across the sampled windows, **NaN when a
          single window was sampled** (files of 90 s or less) — see
          :func:`cutoff_wander`. Callers must treat NaN as "unknown"; it is not 0.
        - residual_floor_db: floor above the ~20.5 kHz wall (NaN unless the cutoff
          sits in the near-Nyquist 320 kbps zone, where Rule 1 needs it)
        - edge_step_db: how far the spectrum falls across the reported edge, read
          on the window that produced the (minimum) cutoff — see
          :func:`edge_step_db`. NaN when no edge was found. Rule 1's gate D.
        - floor_above_db: what is left above that edge — the median level of
          the band from (cutoff + 1 kHz) to 0.993 x Nyquist, on the same
          window — see :func:`floor_above_edge_db`. NaN when no edge was found
          or the band is too narrow (near Nyquist). Rule 1's depth gate.
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

        results = [
            _analyze_window(
                full_audio,
                samplerate,
                _window_bounds(i, num_samples, total_duration, sample_duration, samplerate),
                actual_frames,
                i,
                num_samples,
            )
            for i in range(num_samples)
        ]
        cutoff_freqs = [r[0] for r in results]
        energy_ratios = [r[1] for r in results]
        step_dbs = [r[2] for r in results]
        floor_dbs = [r[3] for r in results]

        # Take the WORST value (min) for cutoff to be more strict
        # A transcoded file will have a low cutoff in ALL samples
        # We use min() because even one sample with low cutoff indicates transcoding
        final_cutoff = min(cutoff_freqs)
        # The step and the floor are read on the window that produced that
        # cutoff: the edge Rule 1 will act on is the one being described.
        min_idx = cutoff_freqs.index(final_cutoff)
        final_step_db = step_dbs[min_idx]
        final_floor_db = floor_dbs[min_idx]

        # For energy, we also take min() to be consistent
        final_energy = min(energy_ratios)

        # Cutoff wander across the sampled windows. NaN when a single window was
        # sampled: see cutoff_wander() — the absence is typed, never 0.0.
        cutoff_std = cutoff_wander(cutoff_freqs)

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
        # v1.13: the computation FLOOR moved 0.90 -> 0.85 x Nyquist. The window
        # gained a consumer below the near-Nyquist zone: gate C-prime accepts an
        # uninformative (PCM-level) container only when the wall proves its
        # depth, and the MP3 signature cells at 18,750-19,750 Hz had no reading
        # under the old floor — the named mechanism of the v1.12 campaign's one
        # missed efficacy prediction (G2, 15/34 vs a registered 20). The TOP
        # stays coupled to Rule 1's 0.94 guard (test_rule1_nearnyquist pins
        # both invariants). Cost: one extra Welch pass on files whose cutoff
        # lands in [0.85, 0.90) x Nyquist.
        if 0.85 * nyquist <= final_cutoff < 0.94 * nyquist:
            residual_floor_db = compute_residual_floor_db(full_audio, samplerate)

        logger.info(
            f"Spectrum analysis: cutoff={final_cutoff:.0f} Hz, "
            f"energy_ratio={final_energy:.6f}, cutoff_std={cutoff_std:.1f}, "
            f"residual_floor_db={residual_floor_db:.1f}, edge_step_db={final_step_db:.1f}, "
            f"floor_above_db={final_floor_db:.1f}, samples={cutoff_freqs}"
        )

        return (
            final_cutoff,
            final_energy,
            cutoff_std,
            residual_floor_db,
            final_step_db,
            final_floor_db,
        )

    except Exception as e:
        logger.debug(f"Spectral analysis error: {e}")
        return 0, 0, 0, float("nan"), float("nan"), float("nan")


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
    nyquist_freq = samplerate / 2.0
    # Reference zone and scan start, scaled for hi-res (see _reference_band).
    reference_freq_low, reference_freq_high, cutoff_scan_start = _reference_band(samplerate)

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
                    # Return start of drop. This is a slice boundary: every cutoff
                    # this branch can return lands on the grid
                    # CUTOFF_SCAN_START + k * TRANCHE_SIZE (14,000 + k x 250 Hz at
                    # 44.1 kHz), so any median of these values is grid-quantized to
                    # its 250 Hz cell. That is how a published Musepack median read
                    # "exactly 18,750 Hz" — a grid point, not the encoder constant
                    # it collided with (found 2026-08-20, answering Provir's check).
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
    energy_cutoff = _energy_fallback_cutoff(frequencies, magnitude_db, nyquist_freq, freq_max)
    if energy_cutoff is not None:
        return energy_cutoff

    # If energy-based also didn't find anything suspicious, truly authentic
    logger.debug(f"No cutoff detected, full spectrum up to {freq_max:.0f} Hz")
    return float(freq_max)


def _energy_fallback_cutoff(
    frequencies: np.ndarray, magnitude_db: np.ndarray, nyquist_freq: float, freq_max: float
) -> Optional[float]:
    """Where 90 % of the cumulative energy is reached, when that reads as a cutoff.

    Returns the energy cutoff when it sits in the realistic MP3 range (15 kHz to
    0.95 x Nyquist); ``freq_max`` when the energy is concentrated below 15 kHz
    (bass, not a cutoff — likely authentic); None when the fallback has nothing
    to say and the caller keeps its own "full spectrum" answer.
    """
    # Convert dB back to linear magnitude: magnitude = 10^(magnitude_db/20)
    magnitude_linear = 10 ** (magnitude_db / 20.0)
    energy = magnitude_linear**2  # Energy is square of linear magnitude
    cumulative_energy = np.cumsum(energy)
    total_energy = cumulative_energy[-1]
    if not total_energy > 0:
        return None
    energy_90_idx = np.where(cumulative_energy >= 0.90 * total_energy)[0]
    if len(energy_90_idx) == 0:
        return None
    energy_cutoff = frequencies[energy_90_idx[0]]
    if 15000 < energy_cutoff < nyquist_freq * 0.95:  # Realistic MP3 range
        logger.debug(
            f"Energy-based cutoff detected at {energy_cutoff:.0f} Hz (90% energy threshold)"
        )
        return float(energy_cutoff)
    if energy_cutoff < 15000:
        logger.debug(f"Energy concentration at {energy_cutoff:.0f} Hz (bass, not cutoff)")
        return float(freq_max)
    return None


class EdgeReading(NamedTuple):
    """What ``detect_cutoff`` cannot say, because it can only return one float.

    ``detect_cutoff`` returns Nyquist in three unrelated situations: the spectrum
    genuinely runs to the top, the energy is concentrated in the bass and no wall
    was looked for, and nothing was found at all. ``found`` is the sentinel that
    separates a measurement from a shrug; ``width_hz`` is how fast the spectrum
    falls across the edge, NaN (never a magic number) when it cannot be read.

    Width was measured on 2026-08-20 and does not become a rule here (AUC
    0.48-0.62 bolted onto our edge-finder). The full record — Provir's figures,
    his retractions and corrections, the three "brickwall" genuine files that
    turned out to be the reporting grid, and the typed-absence rule this class
    embodies — is in ``ml/exchange/EDGE_READING_NOTES_2026-08.md``.

    An absence is TYPED. It is never a value, and never a falsy value. Test
    ``is None`` (or ``math.isnan``); never test a measurement for truth, and
    never coerce one with ``or``: 0.0, 0 and "" are readings.
    ``ml/typed_absence_audit.py`` enforces both shapes on ``src/`` and ``ml/``.
    """

    cutoff_hz: float
    found: bool
    width_hz: float


def cutoff_wander(cutoff_freqs: Sequence[float]) -> float:
    """How far the detected cutoff moves across the sampled windows, or NaN.

    NaN — not 0.0 — when fewer than two windows were sampled, because with one
    window the statistic is **not computable** and 0.0 is a reading. That
    distinction is not academic here; it cost points until v1.13.1.

    ``analyze_spectrum`` samples ``3 if total_duration > 90 else 1`` windows, so
    every file of 90 seconds or less produced exactly one cutoff and the
    not-computable case was returned as ``0.0``. Rule 11's TEST 11D read that
    zero as "cutoff very stable, suspect digital" and subtracted 10 from the
    cassette score — enough, on files whose only cassette evidence was a
    progressive roll-off (11B alone, 20 points), to fall under
    ``CASSETTE_THRESHOLD`` and lose the -40 protection along with Rule 1's
    exemption. An absence, scored, in the direction of conviction. Every file in
    both measurement corpora is 60 seconds, so it fired on all of them:
    ``cutoff_std_hz`` reads 0.0 on 590 of 590 rows of the v2 column file, one
    distinct value.

    Found because Provir reported the mirror defect in his own engine on
    2026-08-29 (``(edge_std or 999) < 160``, where a measured 0.0 became the
    sentinel). His was one-directional and could only lose recall. Ours was not.
    Fourth instance of the species across the two engines; the audit that missed
    it, ``ml/typed_absence_audit.py``, grew a third shape the same day.

    NaN rather than None keeps the return type, matches ``residual_floor_db``
    and ``EdgeReading.width_hz``, and poisons a median loudly instead of
    silently.
    """
    if len(cutoff_freqs) < 2:
        return float("nan")
    return float(np.std(cutoff_freqs))


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

    # detect_cutoff signals "nothing found" by returning the top of the band. That is
    # the ambiguity this function exists to resolve, so it is resolved here rather
    # than by the caller guessing.
    if _no_edge(cutoff, frequencies, samplerate):
        return EdgeReading(cutoff_hz=cutoff, found=False, width_hz=float("nan"))

    ref_low, ref_high, _scan_start = _reference_band(samplerate)

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

    # Analysis by 1 kHz slices. The total is the same sum over the same array for
    # every slice, so it is taken once (an exact hoist, not a reassociation).
    total_energy = float(np.sum(magnitude**2))
    tranche_energies: list[float] = []
    for f_start in range(spectral_config.HIGH_FREQ_THRESHOLD, int(frequencies[-1]), 1000):
        f_mask = (frequencies >= f_start) & (frequencies < f_start + 1000)
        if np.any(f_mask):
            tranche_energy = float(np.sum(magnitude[f_mask] ** 2))
            tranche_energies.append(tranche_energy / total_energy if total_energy > 0 else 0.0)

    # A real FLAC has energy in ALL slices
    return float(np.mean(tranche_energies)) if tranche_energies else 0.0


# Rule 10's segment reader: 10 s windows, and the two std bars of its
# progressive decision (coherent under 500 Hz, dynamic over 1000 Hz).
_R10_SEGMENT_SECONDS = 10.0
_R10_COHERENT_STD_HZ = 500
_R10_DYNAMIC_STD_HZ = 1000


def _segment_cutoff(
    cache: "AudioCache", total_duration: float, samplerate: int, center_ratio: float
) -> float:
    """The cutoff of the 10 s segment centred at ``center_ratio`` of the file, or 0.0.

    0.0 — Rule 10's own "no reading" value, filtered out by its callers — on an
    empty read or any failure. The cutoff is read at the default 44.1 kHz band
    layout whatever the file's rate, as Rule 10 has always been calibrated.
    """
    center_time = total_duration * center_ratio
    start_time = max(0, center_time - (_R10_SEGMENT_SECONDS / 2))
    # Ensure we don't go past end
    if start_time + _R10_SEGMENT_SECONDS > total_duration:
        start_time = max(0, total_duration - _R10_SEGMENT_SECONDS)
    start_frame = int(start_time * samplerate)
    frames_to_read = int(_R10_SEGMENT_SECONDS * samplerate)
    try:
        logger.debug(f"⚡ CACHE: Reading segment at {center_ratio*100:.0f}% via cache")
        data, _ = cache.get_segment(start_frame, frames_to_read)
        if len(data) == 0:
            return 0.0
        fft_freq, _magnitude, magnitude_db = _magnitude_spectrum(data, samplerate)
        return detect_cutoff(fft_freq, magnitude_db)
    except Exception as e:
        logger.warning(f"Error analyzing segment at {center_ratio*100:.0f}%: {e}")
        return 0.0


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

        def analyze_single_segment(center_ratio: float) -> float:
            return _segment_cutoff(cache, total_duration, samplerate, center_ratio)

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
            if variance < _R10_COHERENT_STD_HZ:
                logger.info(
                    f"⚡ OPTIMIZATION R10: Early stop - Coherent segments (variance {variance:.1f} < 500 Hz)"
                )
                # Return only 2 segments (optimization)
                return cutoffs, variance

            # If variance > 1000 Hz, already know it's dynamic -> STOP
            if variance > _R10_DYNAMIC_STD_HZ:
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
