"""MPEG-1 Layer III analysis filterbank probe (ml/mp3_hybrid_filterbank.py), several hole depths.

The derivation tool behind ml/exchange/MP3_GRID_REGISTRATION_2026-09-27.md; the
shipped instrument is src/flac_detective/analysis/new_scoring/mp3_grid.py.

Polyphase 32-band analysis with the standard window C[512], then per subband an
18-point MDCT over 36 samples (sine window, long blocks), with the encoder's
frequency inversion of odd subbands, then the encoder's alias-reduction
butterflies. Output: 576 lines per granule at a given granule alignment.

Prior art for the approach: J. Herre, M. Schug, "Analysis of Decompressed
Audio - The Inverse Decoder", AES 109th Convention, 2000; S. Moehrs, J. Herre,
R. Geiger, "Analysing decompressed audio with the Inverse Decoder - towards an
operative algorithm", AES 112th Convention, 2002.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from flac_detective.analysis.new_scoring.mp3_grid import WINDOW  # noqa: E402

C = WINDOW
_I = np.arange(64)
_K = np.arange(32)
M = np.cos((2 * _K[:, None] + 1) * (_I[None, :] - 16) * np.pi / 64)  # (32, 64)

_n = np.arange(36)
_m = np.arange(18)
SINE36 = np.sin(np.pi / 36 * (_n + 0.5))
MDCT36 = np.cos(np.pi / 72 * (2 * _n[None, :] + 1 + 18) * (2 * _m[:, None] + 1))  # (18, 36)

_CI = np.array([-0.6, -0.535, -0.33, -0.185, -0.095, -0.041, -0.0142, -0.0037])
CS = 1.0 / np.sqrt(1.0 + _CI**2)
CA = _CI / np.sqrt(1.0 + _CI**2)


def polyphase(x: np.ndarray, phase: int) -> np.ndarray:
    """Subband samples (T, 32) for input blocks whose newest sample is phase + 32 t + 31."""
    x = np.asarray(x, dtype=np.float64)
    pad = np.concatenate([np.zeros(512), x])
    first = 512 + phase + 31
    count = (len(pad) - first) // 32
    if count <= 0:
        return np.zeros((0, 32))
    newest = first + 32 * np.arange(count)
    idx = newest[:, None] - np.arange(512)[None, :]  # X[i] = x[n - i]
    z = pad[idx] * C[None, :]
    y = z.reshape(count, 8, 64).sum(axis=1)
    return y @ M.T


def granules(sub: np.ndarray, q: int, n_granules: int, stride: int = 1) -> np.ndarray:
    """576 lines per granule; granule g uses subband samples [q+18(g*stride)-18, q+18(g*stride)+18)."""
    out = []
    t = sub.shape[0]
    for g in range(n_granules):
        start = q + 18 * (g * stride)
        if start < 0 or start + 36 > t:
            break
        blk = sub[start : start + 36].copy()  # (36, 32)
        blk[1::2, 1::2] *= -1.0  # frequency inversion: odd subbands, odd samples
        spec = (MDCT36 @ (blk * SINE36[:, None])).T  # (32, 18)
        lines = spec.reshape(576)
        for sb in range(1, 32):
            for i in range(8):
                a, b = 18 * sb - 1 - i, 18 * sb + i
                bu, bd = lines[a], lines[b]
                lines[a] = bu * CS[i] - bd * CA[i]
                lines[b] = bd * CS[i] + bu * CA[i]
        out.append(lines)
    return np.asarray(out)


def hole_fraction(lines: np.ndarray, depth_db: float = 30.0, ref_size: int = 33) -> float:
    """Share of lines far under their local median, over energetic granules."""
    from scipy.ndimage import median_filter

    mag = np.abs(lines)
    ref = median_filter(mag, size=(1, ref_size), mode="nearest")
    energetic = ref.mean(axis=1) > 1e-7
    if not energetic.any():
        return float("nan")
    thr = 10 ** (-depth_db / 20.0)
    return float(((mag < ref * thr).mean(axis=1))[energetic].mean())


def polyphase_at(x: np.ndarray, phase: int, t_idx: np.ndarray) -> np.ndarray:
    """Subband samples only at the requested indices t (newest input sample phase + 32 t + 31)."""
    pad = np.concatenate([np.zeros(512), np.asarray(x, dtype=np.float64)])
    newest = 512 + phase + 31 + 32 * t_idx
    idx = newest[:, None] - np.arange(512)[None, :]
    z = pad[idx] * C[None, :]
    return z.reshape(len(t_idx), 8, 64).sum(axis=1) @ M.T


def hole_fractions(lines: np.ndarray, depths=(20.0, 30.0, 40.0), ref_size: int = 33) -> np.ndarray:
    from scipy.ndimage import median_filter

    mag = np.abs(lines)
    ref = median_filter(mag, size=(1, ref_size), mode="nearest")
    energetic = ref.mean(axis=1) > 1e-7
    if not energetic.any():
        return np.full(len(depths), np.nan)
    return np.array(
        [float(((mag < ref * 10 ** (-d / 20.0)).mean(axis=1))[energetic].mean()) for d in depths]
    )


def alignment_curves(x: np.ndarray, n_granules: int = 48, depths=(20.0, 30.0, 40.0)) -> np.ndarray:
    """(len(depths), 576) hole-fraction curves, one filterbank pass."""
    total_t = len(x) // 32 - 16
    usable = total_t // 18 - 3
    out = np.full((len(depths), 576), np.nan)
    if usable < 2:
        return out
    stride = max(1, usable // max(1, n_granules))
    starts = 18 + 18 * stride * np.arange(n_granules)
    starts = starts[starts + 18 + 36 <= total_t]
    for phase in range(32):
        need = np.unique((starts[:, None] + np.arange(18 + 36)[None, :]).ravel())
        sub_all = polyphase_at(x, phase, need)
        base = np.searchsorted(need, starts)
        for q in range(18):
            rows = base[:, None] + q + np.arange(36)[None, :]
            out[:, phase + 32 * q] = hole_fractions(_granules_lines(sub_all[rows]), depths)
    return out


def alignment_curve(x: np.ndarray, n_granules: int = 24, depth_db: float = 30.0) -> np.ndarray:
    """Hole fraction at each of the 576 granule alignments (phase + 32 q).

    Only the subband samples the sampled granules need are computed: for
    granule g at alignment (phase, q), subband samples q + 18 (g*stride) .. +35.
    """
    total_t = len(x) // 32 - 16
    usable = total_t // 18 - 3
    if usable < 2:
        return np.full(576, np.nan)
    stride = max(1, usable // max(1, n_granules))
    starts = 18 + 18 * stride * np.arange(n_granules)
    starts = starts[starts + 18 + 36 <= total_t]
    curve = np.full(576, np.nan)
    for phase in range(32):
        # every t any q may need: starts + q + 0..35, q in 0..17
        need = np.unique((starts[:, None] + np.arange(18 + 36)[None, :]).ravel())
        sub_all = polyphase_at(x, phase, need)
        pos = {int(t): i for i, t in enumerate(need)}
        lut = np.array([pos[int(t)] for t in need])  # identity, kept explicit
        base = np.searchsorted(need, starts)
        for q in range(18):
            rows = base[:, None] + q + np.arange(36)[None, :]  # (G, 36): need is contiguous per start
            blk = sub_all[lut[rows]]  # (G, 36, 32)
            curve[phase + 32 * q] = hole_fraction(_granules_lines(blk), depth_db)
    return curve


_AB_A = np.array([[18 * sb - 1 - i for i in range(8)] for sb in range(1, 32)])
_AB_B = np.array([[18 * sb + i for i in range(8)] for sb in range(1, 32)])


def _granules_lines(blk: np.ndarray) -> np.ndarray:
    """(G, 36, 32) subband samples -> (G, 576) alias-reduced lines."""
    b = blk.copy()
    b[:, 1::2, 1::2] *= -1.0
    spec = np.einsum("mn,gnk->gkm", MDCT36, b * SINE36[None, :, None])  # (G, 32, 18)
    lines = spec.reshape(len(b), 576)
    bu = lines[:, _AB_A].copy()
    bd = lines[:, _AB_B].copy()
    lines[:, _AB_A] = bu * CS - bd * CA
    lines[:, _AB_B] = bd * CS + bu * CA
    return lines


def _granule_lines(blk36: np.ndarray) -> np.ndarray:
    blk = blk36.copy()
    blk[1::2, 1::2] *= -1.0
    lines = (MDCT36 @ (blk * SINE36[:, None])).T.reshape(576)
    for sb in range(1, 32):
        a = 18 * sb - 1 - np.arange(8)
        b = 18 * sb + np.arange(8)
        bu, bd = lines[a].copy(), lines[b].copy()
        lines[a] = bu * CS - bd * CA
        lines[b] = bd * CS + bu * CA
    return lines


def peak_ratio(curve: np.ndarray) -> tuple:
    c = curve[~np.isnan(curve)]
    if c.size < 10 or np.median(c) <= 0:
        return float("nan"), -1
    best = int(np.nanargmax(curve))
    return float(np.nanmax(curve) / np.median(c)), best
