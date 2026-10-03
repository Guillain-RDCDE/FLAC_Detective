"""The MP3 frame grid: an MPEG-1 Layer III analysis filterbank, read back (v1.19.0).

The observable
--------------
A Layer III encoder quantises 576 spectral lines per granule; at the rates
people actually use, many of those lines are quantised to zero. Decoding
turns them back into audio, and the audio keeps no visible trace of them:
the cutoff rules read where the spectrum stops, not which lines inside it
were zeroed. Pass the decoded audio through the SAME analysis filterbank the
encoder used — a 32-band polyphase bank with the standard window, then an
18-point MDCT per subband, the encoder's frequency inversion of odd subbands
and its alias-reduction butterflies — and, at the one alignment where the
granules fall where the encoder's fell, the zeroed lines come back as holes.
At any other alignment they are smeared across neighbours. The statistic is
the hole fraction at the best of the 576 alignments over its median across
all of them: a genuine recording has no preferred alignment.

Why it had to be the real bank
------------------------------
ml/README.md ("MP3 geometry: a negative result") measured a plain MDCT at
MP3's own period — 1152 and 576 samples — and it read MP3 at the null, at
every bitrate from 64 to 320 kbps. The zeros live in the hybrid domain, and
matching the period is not matching the transform. That record ended: "the
real MPEG-1 Layer III analysis filterbank remains the only way in". This is
it. Measured 2026-09-27 on the audit corpus (80 genuine, 80 per arm): AUC
1.00 / 0.99 / 0.97 / 0.98 on mp3_128 / 192 / 320 / V0 in the held-out half,
and at chance on aac_ff256 and vorbis_q8 — it reads MP3 and nothing else.

Independent of the cutoff: it never reads where the spectrum stops, only
which lines inside the band are empty at one alignment.

Prior art, for the record, because the approach is old and public: J. Herre
and M. Schug, "Analysis of Decompressed Audio - The Inverse Decoder", AES
109th Convention, 2000; S. Moehrs, J. Herre and R. Geiger, "Analysing
decompressed audio with the Inverse Decoder - towards an operative
algorithm", AES 112th Convention, 2002. The window is the ISO/IEC 11172-3
analysis window C[i], stored here as C[i] x 2^21 for i = 0..256 (the other
half follows by the standard's symmetry), the form FFmpeg also uses.

See ml/exchange/MP3_GRID_REGISTRATION_2026-09-27.md.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from .mdct import HOLE_DEPTH_DB, REF_SIZE

# ISO/IEC 11172-3 analysis window C[0..256], scaled by 2^21.
_HALF_WINDOW = (
    0,
    -1,
    -1,
    -1,
    -1,
    -1,
    -1,
    -2,
    -2,
    -2,
    -2,
    -3,
    -3,
    -4,
    -4,
    -5,
    -5,
    -6,
    -7,
    -7,
    -8,
    -9,
    -10,
    -11,
    -13,
    -14,
    -16,
    -17,
    -19,
    -21,
    -24,
    -26,
    -29,
    -31,
    -35,
    -38,
    -41,
    -45,
    -49,
    -53,
    -58,
    -63,
    -68,
    -73,
    -79,
    -85,
    -91,
    -97,
    -104,
    -111,
    -117,
    -125,
    -132,
    -139,
    -147,
    -154,
    -161,
    -169,
    -176,
    -183,
    -190,
    -196,
    -202,
    -208,
    213,
    218,
    222,
    225,
    227,
    228,
    228,
    227,
    224,
    221,
    215,
    208,
    200,
    189,
    177,
    163,
    146,
    127,
    106,
    83,
    57,
    29,
    -2,
    -36,
    -72,
    -111,
    -153,
    -197,
    -244,
    -294,
    -347,
    -401,
    -459,
    -519,
    -581,
    -645,
    -711,
    -779,
    -848,
    -919,
    -991,
    -1064,
    -1137,
    -1210,
    -1283,
    -1356,
    -1428,
    -1498,
    -1567,
    -1634,
    -1698,
    -1759,
    -1817,
    -1870,
    -1919,
    -1962,
    -2001,
    -2032,
    -2057,
    -2075,
    -2085,
    -2087,
    -2080,
    -2063,
    2037,
    2000,
    1952,
    1893,
    1822,
    1739,
    1644,
    1535,
    1414,
    1280,
    1131,
    970,
    794,
    605,
    402,
    185,
    -45,
    -288,
    -545,
    -814,
    -1095,
    -1388,
    -1692,
    -2006,
    -2330,
    -2663,
    -3004,
    -3351,
    -3705,
    -4063,
    -4425,
    -4788,
    -5153,
    -5517,
    -5879,
    -6237,
    -6589,
    -6935,
    -7271,
    -7597,
    -7910,
    -8209,
    -8491,
    -8755,
    -8998,
    -9219,
    -9416,
    -9585,
    -9727,
    -9838,
    -9916,
    -9959,
    -9966,
    -9935,
    -9863,
    -9750,
    -9592,
    -9389,
    -9139,
    -8840,
    -8492,
    -8092,
    -7640,
    -7134,
    6574,
    5959,
    5288,
    4561,
    3776,
    2935,
    2037,
    1082,
    70,
    -998,
    -2122,
    -3300,
    -4533,
    -5818,
    -7154,
    -8540,
    -9975,
    -11455,
    -12980,
    -14548,
    -16155,
    -17799,
    -19478,
    -21189,
    -22929,
    -24694,
    -26482,
    -28289,
    -30112,
    -31947,
    -33791,
    -35640,
    -37489,
    -39336,
    -41176,
    -43006,
    -44821,
    -46617,
    -48390,
    -50137,
    -51853,
    -53534,
    -55178,
    -56778,
    -58333,
    -59838,
    -61289,
    -62684,
    -64019,
    -65290,
    -66494,
    -67629,
    -68692,
    -69679,
    -70590,
    -71420,
    -72169,
    -72835,
    -73415,
    -73908,
    -74313,
    -74630,
    -74856,
    -74992,
    75038,
)


def _full_window() -> np.ndarray:
    c = np.zeros(512)
    for i, v in enumerate(_HALF_WINDOW):
        c[i] = v
        if i:
            c[512 - i] = -v if (i & 63) else v
    return c / 2.0**21


WINDOW = _full_window()
_I = np.arange(64)
_K = np.arange(32)
_MATRIX = np.cos((2 * _K[:, None] + 1) * (_I[None, :] - 16) * np.pi / 64)  # (32, 64)
_N = np.arange(36)
_M = np.arange(18)
_SINE36 = np.sin(np.pi / 36 * (_N + 0.5))
_MDCT36 = np.cos(np.pi / 72 * (2 * _N[None, :] + 1 + 18) * (2 * _M[:, None] + 1))  # (18, 36)
_CI = np.array([-0.6, -0.535, -0.33, -0.185, -0.095, -0.041, -0.0142, -0.0037])
_CS = 1.0 / np.sqrt(1.0 + _CI**2)
_CA = _CI / np.sqrt(1.0 + _CI**2)
_AB_A = np.array([[18 * sb - 1 - i for i in range(8)] for sb in range(1, 32)])
_AB_B = np.array([[18 * sb + i for i in range(8)] for sb in range(1, 32)])

GRANULE = 576
# Measured, not tuned in the dark: 48 granules spread over a 30 s excerpt and
# a hole at 40 dB under the local median gave the widest genuine-to-arm gap on
# the development half (see the registration). The hole depth and the
# reference-filter width are Rule 13's own, imported rather than restated.
N_GRANULES = 48
EXCERPT_SECONDS = 30.0


def _polyphase_at(x: np.ndarray, phase: int, t_idx: np.ndarray) -> np.ndarray:
    """Subband samples (len(t_idx), 32); newest input sample of t is phase + 32 t + 31."""
    pad = np.concatenate([np.zeros(512), x])
    newest = 512 + phase + 31 + 32 * t_idx
    z = pad[newest[:, None] - np.arange(512)[None, :]] * WINDOW[None, :]
    result: np.ndarray = z.reshape(len(t_idx), 8, 64).sum(axis=1) @ _MATRIX.T
    return result


def _granule_lines(blk: np.ndarray) -> np.ndarray:
    """(G, 36, 32) subband samples -> (G, 576) alias-reduced lines, as the encoder forms them."""
    b = blk.copy()
    b[:, 1::2, 1::2] *= -1.0  # odd subbands, odd samples: the encoder's frequency inversion
    spec = np.einsum("mn,gnk->gkm", _MDCT36, b * _SINE36[None, :, None])  # (G, 32, 18)
    lines = spec.reshape(len(b), GRANULE)
    bu = lines[:, _AB_A].copy()
    bd = lines[:, _AB_B].copy()
    lines[:, _AB_A] = bu * _CS - bd * _CA
    lines[:, _AB_B] = bd * _CS + bu * _CA
    result: np.ndarray = lines
    return result


def _hole_fraction(lines: np.ndarray) -> float:
    from scipy.ndimage import median_filter

    mag = np.abs(lines)
    ref = median_filter(mag, size=(1, REF_SIZE), mode="nearest")
    energetic = ref.mean(axis=1) > 1e-7
    if not energetic.any():
        return float("nan")
    thr = 10 ** (-HOLE_DEPTH_DB / 20.0)
    return float(((mag < ref * thr).mean(axis=1))[energetic].mean())


def alignment_curve(x: np.ndarray) -> np.ndarray:
    """Hole fraction at each of the 576 granule alignments of a mono signal."""
    x = np.asarray(x, dtype=np.float64)
    curve = np.full(GRANULE, np.nan)
    total_t = len(x) // 32 - 16
    usable = total_t // 18 - 3
    if usable < 2:
        return curve
    stride = max(1, usable // N_GRANULES)
    starts = 18 + 18 * stride * np.arange(N_GRANULES)
    starts = starts[starts + 18 + 36 <= total_t]
    if starts.size == 0:
        return curve
    for phase in range(32):
        need = np.unique((starts[:, None] + np.arange(18 + 36)[None, :]).ravel())
        sub = _polyphase_at(x, phase, need)
        base = np.searchsorted(need, starts)
        for q in range(18):
            rows = base[:, None] + q + np.arange(36)[None, :]
            curve[phase + 32 * q] = _hole_fraction(_granule_lines(sub[rows]))
    return curve


def grid_peak_ratio(audio: np.ndarray, sample_rate: int) -> Tuple[float, int]:
    """(peak ratio, best alignment) on the central excerpt; (nan, -1) when not measurable.

    NaN — not 1.0 — when the excerpt is too short or silent: an unknown grid
    is not an absent one, and a caller must treat NaN as "no reading".
    """
    data = np.asarray(audio)
    mono = data.mean(axis=1) if data.ndim > 1 else data
    n = int(EXCERPT_SECONDS * sample_rate)
    start = max(0, (len(mono) - n) // 2)
    curve = alignment_curve(mono[start : start + n])
    good = curve[~np.isnan(curve)]
    if good.size < GRANULE // 2:
        return float("nan"), -1
    med = float(np.median(good))
    if med <= 0:
        return float("nan"), -1
    return float(np.nanmax(curve) / med), int(np.nanargmax(curve))
