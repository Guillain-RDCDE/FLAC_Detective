#!/usr/bin/env python3
"""Measure the model's generalisation gap: in-distribution vs wild AUC.

The shipped CNN was trained only on **ffmpeg** transcodes (libmp3lame / aac /
libopus / libvorbis). Real-world fakes come from other encoders (standalone LAME,
qaac/Apple, Fraunhofer fdkaac, oggenc…) and from the wild. A model that learned an
*encoder* fingerprint rather than a *transcode* fingerprint will score beautifully
on held-out ffmpeg data and then fall over on the real thing. This script
quantifies exactly that drop.

Input: one or more labelled probability CSVs (``p_raw,label`` or
``path,label,p_raw,...`` — produced by ``ml/emit_probs.py`` or
``ml/build_wild_testset.py``), each tagged with a name. It reports, per set:
ROC-AUC, accuracy and balanced accuracy at p=0.5, and the expected calibration
error — then the **AUC drop** of each set relative to the first (the
in-distribution baseline).

No sklearn: AUC is the rank-based Mann-Whitney statistic. Pure numpy.

Usage::

    python ml/measure_auc_drop.py \
        baseline=ffmpeg_probs.csv \
        external=external_probs.csv \
        wild=wild_probs.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np


def _read(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Read p_raw + label from a CSV with a header naming the columns."""
    ps: List[float] = []
    ys: List[float] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise SystemExit(f"{path}: empty CSV")
        # Accept either p_raw or p_cal as the probability column.
        pcol = "p_raw" if "p_raw" in reader.fieldnames else "p_cal"
        if pcol not in reader.fieldnames or "label" not in reader.fieldnames:
            raise SystemExit(f"{path}: need '{pcol}' and 'label' columns, got {reader.fieldnames}")
        for row in reader:
            try:
                ps.append(float(row[pcol]))
                ys.append(float(row["label"]))
            except (ValueError, KeyError):
                continue
    if not ps:
        raise SystemExit(f"{path}: no usable rows")
    return np.asarray(ps), np.asarray(ys)


def roc_auc(p: np.ndarray, y: np.ndarray) -> float:
    """ROC-AUC via the rank-based (Mann-Whitney U) estimator. NaN if single-class."""
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    # Tie-averaged ranks (1-based), so equal probabilities don't bias the statistic.
    _, inv, counts = np.unique(p, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts)
    start = cum - counts
    avg_tie_rank = (start + cum + 1) / 2.0
    ranks = avg_tie_rank[inv]
    rank_sum_pos = ranks[y == 1].sum()
    auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error over equal-width probability bins."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    total, n = 0.0, len(p)
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (p >= lo) & (p < hi) if i < bins - 1 else (p >= lo) & (p <= hi)
        if not np.any(mask):
            continue
        total += (np.sum(mask) / n) * abs(float(np.mean(p[mask])) - float(np.mean(y[mask])))
    return float(total)


def _metrics(p: np.ndarray, y: np.ndarray) -> dict:
    """AUC + accuracy/balanced-accuracy at 0.5 + ECE for one labelled set."""
    pred = (p >= 0.5).astype(float)
    tp = float(np.sum((pred == 1) & (y == 1)))
    tn = float(np.sum((pred == 0) & (y == 0)))
    n_pos = float(np.sum(y == 1))
    n_neg = float(np.sum(y == 0))
    recall = tp / n_pos if n_pos else float("nan")
    spec = tn / n_neg if n_neg else float("nan")
    return {
        "n": len(p),
        "auc": roc_auc(p, y),
        "acc": float(np.mean(pred == y)),
        "bal_acc": (recall + spec) / 2.0,
        "recall": recall,
        "specificity": spec,
        "ece": _ece(p, y),
    }


def main() -> None:
    """Parse ``name=path`` args, print per-set metrics and the AUC drop table."""
    args = sys.argv[1:]
    if not args:
        raise SystemExit("Usage: measure_auc_drop.py name=probs.csv [name2=probs2.csv ...]")
    named = []
    for a in args:
        if "=" not in a:
            raise SystemExit(f"Expected name=path, got {a!r}")
        name, path = a.split("=", 1)
        named.append((name, Path(path)))

    print(
        f"{'set':<14} {'n':>6} {'AUC':>7} {'acc':>7} {'bal_acc':>8} {'recall':>7} "
        f"{'spec':>7} {'ECE':>7}"
    )
    print("-" * 70)
    results = []
    for name, path in named:
        p, y = _read(path)
        m = _metrics(p, y)
        results.append((name, m))
        print(
            f"{name:<14} {m['n']:>6} {m['auc']:>7.3f} {m['acc']:>7.3f} {m['bal_acc']:>8.3f} "
            f"{m['recall']:>7.3f} {m['specificity']:>7.3f} {m['ece']:>7.3f}"
        )

    if len(results) > 1:
        base_name, base = results[0]
        print(
            f"\nAUC drop relative to in-distribution baseline '{base_name}' "
            f"(AUC {base['auc']:.3f}):"
        )
        for name, m in results[1:]:
            drop = base["auc"] - m["auc"]
            flag = "  <-- large drop" if drop >= 0.05 else ""
            print(f"  {name:<14} AUC {m['auc']:.3f}   Δ {drop:+.3f}{flag}")
        print(
            "\nA large drop means the model leans on an in-distribution (ffmpeg) tell "
            "rather than\na general transcode fingerprint — the signal that the training "
            "zoo needs widening."
        )


if __name__ == "__main__":
    main()
