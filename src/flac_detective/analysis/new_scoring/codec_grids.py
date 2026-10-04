"""Codec grids the fixed 2048-sample reading cannot see: Vorbis block switching and CELT.

Rule 13 was built on one geometry — a 2048-sample long block on a single fixed
grid, read on the mono mix — and it reads ffmpeg AAC and most Vorbis well. Issue #12
brought three files it could not read, and each one failed for a reason that is a
property of the codec, not of the bitrate:

**Vorbis moves its own grid.** A Vorbis encoder switches to 256-sample blocks on
transients, and every run of short blocks shifts the following long blocks by a
multiple of 128 samples (a long block after a long block advances 1024; a run of k
short blocks between two long ones advances 1024 + 128 k). On loud, transient-heavy
material there is therefore no single alignment for the whole file — there are
eight, and the encoder hops between them. A statistic that looks for ONE alignment
spreads the evidence over all eight and reads a weak grid (the issue's ``-q1`` file:
2.43). ``vorbis_switch_ratio`` lets each read frame keep the best of the eight
phases its residue allows, and compares residues against residues: the genuine
null is preserved because every residue is given the same eight chances.

**Vorbis at high quality keeps its zeros per channel.** At ``-q10`` the channels are
coupled losslessly, so a coefficient that is zero in the left channel is rarely zero
in the right one, and the mono mix — which needs both — has none. The left and right
channels are read separately (``-q10``, mono 1.2, left 4.7).

**CELT is reachable after all.** Rule 13's documentation said Opus was out of reach
by construction, because CELT works at 48 kHz and resampling destroys the alignment.
The resampling is not what hid it. The CELT decoder ends with a de-emphasis filter
(y[n] = x[n] + 0.85 y[n-1]), an IIR that smears every zeroed coefficient across its
neighbours. Bring the file back to 48 kHz (160/147, exact for 44.1 kHz), undo the
de-emphasis with its FIR inverse, read 960-sample frames through CELT's own
low-overlap window, and the grid is there: the issue's Opus 64 kbps file reads 3.9
at the same offset as a native 48 kHz decode, its original 1.1.

Both statistics are new and are certified separately from Rule 13's two
hypotheses, against their own genuine population and their own bars (see
``rules.mdct_alignment``). The certified count of the original statistic does not
move: it is still a maximum over the same two draws.

Two choices are for cost and change nothing a bar depends on, since the bars were
calibrated with them in place: the MDCT is computed as a TDAC fold plus a DCT-IV
(exactly the transform, about six times cheaper than the FFT form), and the local
median every hole is measured against is evaluated every 8 bins (every 4 in triage)
and held in between.

The triage that ranks residues before the fine read is where both statistics were
fragile, in opposite ways. CELT triages on the loudest of a wider spread of
positions: three fixed positions, one of them a quiet intro, ranked noise first
and lost the true grid on two Opus files of the bench. Vorbis must NOT pick the
loudest, which are its short-block frames; it triages on evenly spread positions.
"""

from __future__ import annotations

from typing import Callable, List, NamedTuple, Optional, Sequence, Tuple

import numpy as np
from scipy.fft import dct
from scipy.signal import lfilter, resample_poly

from .mdct import vorbis_window

Reader = Callable[[int, int], Optional[np.ndarray]]

# Hole definition, identical to Rule 13's: a coefficient this far under the median
# of its neighbourhood.
HOLE_DEPTH_DB = 40.0
ANALYSIS_BAND_HZ: Tuple[float, float] = (2000.0, 16000.0)

# Triage / fine stage sizes. The triage ranks every residue on the loudest
# N_TRIAGE of 3 * N_TRIAGE spread positions; the fine stage re-reads the best
# N_CANDIDATES residues and N_BASELINE unrelated ones on N_FINE positions.
N_TRIAGE = 4
N_FINE = 16
N_CANDIDATES = 8
N_BASELINE = 12
GUARD = 4
TRIAGE_REF = 9
FINE_REF = 33
MIN_BASELINE_HOLE_FRACTION = 0.001

# Vorbis long block and the step a run of short blocks moves it by.
VORBIS_BLOCK = 2048
VORBIS_SWITCH_STEP = 128

# CELT: 20 ms frames of 960 coefficients at 48 kHz, 120-sample overlap, and the
# decoder's de-emphasis coefficient.
CELT_RATE = 48000
CELT_FRAME = 960
CELT_OVERLAP = 120
CELT_DEEMPHASIS = 0.85
# CELT has 960 residues to rank against Vorbis's 128, so its triage reads more
# positions and keeps more candidates: at 4 / 8 one bench Opus file (t05) lost its
# true residue in triage and read 1.20; at 6 / 16 it reads 6.40.
CELT_TRIAGE = 6
CELT_CANDIDATES = 16
# Vorbis triages on evenly spread positions, NOT the loudest: on transient-heavy
# material the loudest frames are drum hits, coded in short blocks, where the
# long-block grid does not exist. Picking them dropped one bench file in fifteen
# to the null at random (t07, t14, t29 ...); spread positions dropped none.
VORBIS_TRIAGE = 8
VORBIS_CANDIDATES = 8
VORBIS_TRIAGE_LOUDEST = False


def mdct_magnitudes(blocks: np.ndarray, sample_rate: int, band: Tuple[float, float]) -> np.ndarray:
    """|MDCT| of each windowed row, restricted to ``band``.

    Same transform as ``mdct.mdct_basis`` (phase n + 1/2 + N/2), computed as the
    standard TDAC fold followed by a DCT-IV.
    """
    length = blocks.shape[1]
    n = length // 2
    h = n // 2
    a, b, c, d = blocks[:, :h], blocks[:, h:n], blocks[:, n : n + h], blocks[:, n + h :]
    folded = np.concatenate([-c[:, ::-1] - d, a - b[:, ::-1]], axis=1).astype(np.float64)
    lo = max(1, int(band[0] / (sample_rate / 2) * n))
    hi = min(n, int(band[1] / (sample_rate / 2) * n))
    spectrum: np.ndarray = np.abs(dct(folded, type=4, axis=1)[:, lo:hi] / 2)
    return spectrum


def local_median(spec: np.ndarray, size: int, every: int) -> np.ndarray:
    """Running median of ``size`` bins, evaluated every ``every`` bins and held."""
    half = size // 2
    width = spec.shape[1]
    centres = np.arange(0, width, every)
    padded = np.pad(spec, ((0, 0), (half, half)), mode="edge")
    windows = padded[:, centres[:, None] + np.arange(size)[None, :]]
    med = np.partition(windows, half, axis=-1)[..., half]
    index = np.minimum(np.round(np.arange(width) / every).astype(int), len(centres) - 1)
    held: np.ndarray = med[:, index]
    return held


def hole_fractions(
    segment: np.ndarray,
    offsets: np.ndarray,
    window: np.ndarray,
    sample_rate: int,
    ref_size: int,
) -> Optional[np.ndarray]:
    """Fraction of holes in the frame starting at each offset of ``segment``."""
    length = len(window)
    blocks = segment[offsets[:, None] + np.arange(length)[None, :]] * window[None, :]
    spec = mdct_magnitudes(blocks, sample_rate, ANALYSIS_BAND_HZ)
    ref = local_median(spec, ref_size, 8 if ref_size >= 17 else 4)
    if float(ref.mean()) <= 1e-7:
        return None
    fractions: np.ndarray = (spec < ref * 10 ** (-HOLE_DEPTH_DB / 20)).mean(axis=1)
    return fractions


def _circular_distance(a: int, b: int, step: int) -> int:
    return min((a - b) % step, (b - a) % step)


class _Geometry(NamedTuple):
    """One grid hypothesis: window, rate, residue step and what the signal allows."""

    window: np.ndarray
    sample_rate: int
    step: int
    n_total: int

    @property
    def length(self) -> int:
        return len(self.window)

    @property
    def hop(self) -> int:
        return self.length // 2

    @property
    def usable(self) -> int:
        return self.n_total - self.length - self.hop

    def positions(self, count: int) -> List[int]:
        """``count`` evenly spread read positions, whole hops apart."""
        stride = max(self.hop, (self.usable // count) // self.hop * self.hop)
        return [
            f * stride for f in range(count) if f * stride + self.hop + self.length <= self.n_total
        ]

    def accumulate(
        self, read: Reader, residues: Sequence[int], bases: Sequence[int], ref_size: int
    ) -> Optional[np.ndarray]:
        """Mean over read positions of each residue's best phase hole fraction."""
        phases = self.hop // self.step
        res = np.asarray(residues)
        offsets = (res[:, None] + self.step * np.arange(phases)[None, :]).ravel()
        total = np.zeros(res.size)
        used = 0
        for base in bases:
            segment = read(base, self.hop + self.length)
            if segment is None:
                continue
            fractions = hole_fractions(segment, offsets, self.window, self.sample_rate, ref_size)
            if fractions is None:
                continue
            total += fractions.reshape(res.size, phases).max(axis=1)
            used += 1
        return total / used if used else None

    def triage_bases(self, read: Reader, n_triage: int, loudest: bool) -> List[int]:
        """Where the triage reads: the loudest of a wider spread, or the spread itself."""
        pool = self.positions(n_triage * 3 if loudest else n_triage)
        loudness = []
        for base in pool:
            segment = read(base, self.hop + self.length)
            loudness.append(
                -1.0 if segment is None else float(np.mean(np.square(segment, dtype=np.float64)))
            )
        if loudest:
            return [pool[i] for i in sorted(np.argsort(loudness)[::-1][:n_triage])]
        floor = 0.01 * float(np.median([v for v in loudness if v > 0] or [0.0]))
        return [b for b, v in zip(pool, loudness) if v > floor]

    def baseline(self, candidates: Sequence[int]) -> List[int]:
        """Unrelated residues, more than GUARD away from every candidate."""
        spread = np.linspace(0, self.step - 1, N_BASELINE * 3).astype(int)
        far = {
            int(r)
            for r in spread
            if min(_circular_distance(int(r), c, self.step) for c in candidates) > GUARD
        }
        return sorted(far)[:N_BASELINE]


def _fine_ratio(fine: Optional[np.ndarray], candidates: Sequence[int]) -> Tuple[float, int]:
    """Best candidate over the baseline median, or ``(nan, -1)``."""
    if fine is None:
        return float("nan"), -1
    median_base = float(np.median(fine[len(candidates) :]))
    if median_base < MIN_BASELINE_HOLE_FRACTION:
        return float("nan"), -1
    peak_index = int(np.argmax(fine[: len(candidates)]))
    return float(fine[peak_index] / median_base), candidates[peak_index]


def grid_ratio(
    read: Reader,
    n_total: int,
    window: np.ndarray,
    sample_rate: int,
    step: int,
    fine_readers: Optional[Sequence[Reader]] = None,
    n_triage: int = N_TRIAGE,
    n_candidates: int = N_CANDIDATES,
    loudest: bool = True,
) -> Tuple[float, int]:
    """Peak-to-baseline hole ratio over residues modulo ``step``.

    ``step`` equal to the hop is a fixed grid (one phase per residue). A smaller
    ``step`` lets each frame keep the best of the hop / step phases of a residue,
    which is what a block-switching encoder needs. ``read(start, n)`` returns the
    analysis-domain samples [start, start + n); the triage uses ``read`` and the
    fine stage every reader in ``fine_readers`` (default: ``read``), keeping the
    strongest. Returns ``(nan, -1)`` when the statistic cannot be measured.
    """
    geometry = _Geometry(window, sample_rate, step, n_total)
    if geometry.usable <= 0:
        return float("nan"), -1

    triage = geometry.accumulate(
        read, range(step), geometry.triage_bases(read, n_triage, loudest), TRIAGE_REF
    )
    if triage is None:
        return float("nan"), -1
    candidates = sorted(int(r) for r in np.argsort(triage)[::-1][:n_candidates])
    baseline = geometry.baseline(candidates)
    if not baseline:
        return float("nan"), -1

    best = (float("nan"), -1)
    for rd in fine_readers or [read]:
        fine = geometry.accumulate(rd, candidates + baseline, geometry.positions(N_FINE), FINE_REF)
        ratio, residue = _fine_ratio(fine, candidates)
        if np.isfinite(ratio) and (not np.isfinite(best[0]) or ratio > best[0]):
            best = (ratio, residue)
    return best


def vorbis_switch_ratio(audio: np.ndarray, sample_rate: int) -> Tuple[float, int]:
    """Vorbis long-block grid allowed to move by 128, read on the left and right channels.

    The triage runs once, on the left channel: the encoder's block grid is shared
    by both channels, so the residue it finds serves both fine reads.
    """
    data = audio if audio.ndim == 2 else audio[:, None]
    left, right = data[:, 0], data[:, -1]

    # Segments are copied as they are read, never the whole channel.
    def read_left(start: int, n: int) -> np.ndarray:
        return np.asarray(left[start : start + n], dtype=np.float32)

    def read_right(start: int, n: int) -> np.ndarray:
        return np.asarray(right[start : start + n], dtype=np.float32)

    readers: List[Reader] = [read_left, read_right] if data.shape[1] > 1 else [read_left]
    return grid_ratio(
        read_left,
        len(left),
        vorbis_window(VORBIS_BLOCK),
        sample_rate,
        VORBIS_SWITCH_STEP,
        fine_readers=readers,
        n_triage=VORBIS_TRIAGE,
        n_candidates=VORBIS_CANDIDATES,
        loudest=VORBIS_TRIAGE_LOUDEST,
    )


def celt_window(frame: int = CELT_FRAME, overlap: int = CELT_OVERLAP) -> np.ndarray:
    """The CELT low-overlap MDCT window, written over the 2 x frame samples it spans."""
    i = np.arange(overlap)
    rise = np.sin(0.5 * np.pi * np.sin(0.5 * np.pi * (i + 0.5) / overlap) ** 2)
    zeros = (frame - overlap) // 2
    window: np.ndarray = np.concatenate(
        [np.zeros(zeros), rise, np.ones(frame - overlap), rise[::-1], np.zeros(zeros)]
    ).astype(np.float32)
    return window


# Input samples of padding on each side of a resampled segment, in units of 147
# (so a segment always starts on the shared 48 kHz grid).
_RESAMPLE_PAD = 64


def celt_ratio(mono: np.ndarray, sample_rate: int) -> Tuple[float, int]:
    """CELT 960 grid on the 48 kHz, de-emphasis-undone signal.

    44.1 kHz input is resampled segment by segment, each segment starting on a
    multiple of 147 input samples so that every one lands on the same global
    48 kHz grid; 48 kHz input is read as is. Other rates abstain: Opus resamples
    them through rates this has not been measured on.
    """
    signal = mono
    window = celt_window()
    pre_emphasis = [1.0, -CELT_DEEMPHASIS]
    if sample_rate == CELT_RATE:

        def read_native(start: int, n: int) -> Optional[np.ndarray]:
            # One sample of history for the FIR, so the segment is filtered exactly
            # as the whole signal would be.
            lead = 1 if start > 0 else 0
            piece = np.asarray(signal[start - lead : start + n], dtype=np.float64)
            out = lfilter(pre_emphasis, [1.0], piece)[lead:]
            return out.astype(np.float32) if len(out) == n else None

        return grid_ratio(
            read_native,
            len(signal),
            window,
            CELT_RATE,
            CELT_FRAME,
            n_triage=CELT_TRIAGE,
            n_candidates=CELT_CANDIDATES,
        )
    if sample_rate != 44100:
        return float("nan"), -1

    def read_resampled(start48: int, n: int) -> Optional[np.ndarray]:
        first = (start48 * 147 // 160) // 147 * 147
        lead = start48 - first * 160 // 147
        begin = max(0, first - _RESAMPLE_PAD * 147)
        span = (lead + n) * 147 // 160 + 2 * _RESAMPLE_PAD * 147
        piece = np.asarray(signal[begin : begin + span + (first - begin)], dtype=np.float64)
        if len(piece) < 16:
            return None
        up = lfilter(pre_emphasis, [1.0], resample_poly(piece, 160, 147))
        at = (first - begin) * 160 // 147 + lead
        out = up[at : at + n]
        return out.astype(np.float32) if len(out) == n else None

    return grid_ratio(
        read_resampled,
        len(signal) * 160 // 147,
        window,
        CELT_RATE,
        CELT_FRAME,
        n_triage=CELT_TRIAGE,
        n_candidates=CELT_CANDIDATES,
    )
