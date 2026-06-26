#!/usr/bin/env python3
"""Fit a probability-calibration mapping for Rule 12 (the CNN classifier).

The CNN's softmax output ``p_raw`` is over-confident (the usual cross-entropy
story): at p=0.9 it is right less than 90% of the time. This script fits a
monotonic mapping ``p_raw -> p_cal`` on a labelled held-out set so that a
calibrated p means what it says, and writes it next to the model as
``src/flac_detective/models/cnn_v4_stereo.calibration.json`` — which the runtime
(:mod:`flac_detective.analysis.new_scoring.rules.ml_calibration`) loads.

Two methods, both monotonic (they never reorder files):

* ``platt`` (default) — logistic fit on the logit of p: 2 parameters, robust on
  small sets. Fitted by Newton-Raphson IRLS here (no sklearn dependency).
* ``isotonic`` — non-parametric monotonic step function via the
  pool-adjacent-violators algorithm, stored as (x, y) breakpoints. More
  flexible, needs more data.

Input is a CSV with two columns ``p_raw,label`` (label 1=transcoded, 0=authentic),
one row per held-out file. Produce it from the existing measurement harness, e.g.
``ml/measure_v4_per_codec.py`` already runs the shipped inference per file — emit
``(p_raw, label)`` rows from a balanced authentic+transcode set that the model did
NOT train on.

Usage::

    python ml/calibrate_model.py --input calib_probs.csv --method platt
    python ml/calibrate_model.py --input calib_probs.csv --method isotonic --out custom.json

Reports the Brier score and expected calibration error (ECE) before and after,
so you can see the mapping actually helped. Seeds nothing (deterministic fit).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import numpy as np

# Default destination: bundled next to the TorchScript model.
_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "flac_detective"
    / "models"
    / "cnn_v4_stereo.calibration.json"
)
_EPS = 1e-6


def _read_csv(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Read a ``p_raw,label`` CSV into (p, y) float arrays."""
    ps: List[float] = []
    ys: List[float] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        # Tolerate a header row (non-numeric first cell) or its absence.
        if header is not None:
            try:
                ps.append(float(header[0]))
                ys.append(float(header[1]))
            except (ValueError, IndexError):
                pass
        for row in reader:
            if len(row) < 2:
                continue
            ps.append(float(row[0]))
            ys.append(float(row[1]))
    p = np.clip(np.asarray(ps, dtype=np.float64), _EPS, 1 - _EPS)
    y = np.asarray(ys, dtype=np.float64)
    if p.size == 0:
        raise SystemExit("No (p_raw, label) rows read — check the CSV.")
    return p, y


def _brier(p: np.ndarray, y: np.ndarray) -> float:
    """Mean squared error between probability and label (lower is better)."""
    return float(np.mean((p - y) ** 2))


def _ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error: |confidence - accuracy| averaged over bins."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    n = len(p)
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (p >= lo) & (p < hi) if i < bins - 1 else (p >= lo) & (p <= hi)
        if not np.any(mask):
            continue
        conf = float(np.mean(p[mask]))
        acc = float(np.mean(y[mask]))
        total += (np.sum(mask) / n) * abs(conf - acc)
    return float(total)


def _fit_platt(p: np.ndarray, y: np.ndarray, iters: int = 100) -> Tuple[float, float]:
    """Fit ``p_cal = sigmoid(a * logit(p) + b)`` by Newton-Raphson IRLS."""
    z = np.log(p / (1 - p))  # logit of the raw probability
    a, b = 1.0, 0.0
    for _ in range(iters):
        eta = a * z + b
        q = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(q * (1 - q), 1e-9, None)
        # Gradient of the negative log-likelihood w.r.t. (a, b).
        g_a = float(np.sum((q - y) * z))
        g_b = float(np.sum(q - y))
        # Hessian (2x2).
        h_aa = float(np.sum(w * z * z))
        h_ab = float(np.sum(w * z))
        h_bb = float(np.sum(w))
        det = h_aa * h_bb - h_ab * h_ab
        if abs(det) < 1e-12:
            break
        da = (h_bb * g_a - h_ab * g_b) / det
        db = (h_aa * g_b - h_ab * g_a) / det
        a -= da
        b -= db
        if abs(da) < 1e-9 and abs(db) < 1e-9:
            break
    return a, b


def _apply_platt(p: np.ndarray, a: float, b: float) -> np.ndarray:
    """Apply a fitted Platt mapping to an array of raw probabilities."""
    z = np.log(p / (1 - p))
    return 1.0 / (1.0 + np.exp(-(a * z + b)))


def _fit_isotonic(p: np.ndarray, y: np.ndarray) -> Tuple[List[float], List[float]]:
    """Pool-adjacent-violators isotonic regression; return (x, y) breakpoints."""
    order = np.argsort(p)
    xs = p[order].astype(float)
    ys = y[order].astype(float)
    # PAVA: maintain blocks of (sum, count, value) enforcing non-decreasing means.
    blocks: List[List[float]] = []  # each: [sum, count, value]
    for val in ys:
        blocks.append([val, 1.0, val])
        while len(blocks) > 1 and blocks[-2][2] > blocks[-1][2]:
            s2, c2, _ = blocks.pop()
            s1, c1, _ = blocks.pop()
            s, c = s1 + s2, c1 + c2
            blocks.append([s, c, s / c])
    # Expand block means back to per-sample fitted values.
    fitted = np.empty_like(ys)
    idx = 0
    for s, c, v in blocks:
        for _ in range(int(c)):
            fitted[idx] = v
            idx += 1
    # Compress to breakpoints at x-value changes (keep first/last).
    bx: List[float] = [float(xs[0])]
    by: List[float] = [float(fitted[0])]
    for i in range(1, len(xs)):
        if xs[i] != bx[-1]:
            bx.append(float(xs[i]))
            by.append(float(fitted[i]))
        else:
            by[-1] = float(fitted[i])
    if len(bx) < 2:  # degenerate (all same x) — pad so the runtime can interpolate
        bx = [0.0, 1.0]
        by = [float(fitted[0]), float(fitted[-1])]
    return bx, by


def _apply_isotonic(p: np.ndarray, bx: List[float], by: List[float]) -> np.ndarray:
    """Apply isotonic breakpoints to raw probabilities (linear interpolation)."""
    return np.interp(p, bx, by)


def main() -> None:
    """Fit the calibration mapping and write the JSON file."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path, help="CSV with p_raw,label rows")
    ap.add_argument("--method", choices=["platt", "isotonic"], default="platt")
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="Output JSON path")
    args = ap.parse_args()

    p, y = _read_csv(args.input)
    n = len(p)
    print(f"Loaded {n} rows ({int(y.sum())} transcoded, {int(n - y.sum())} authentic)")
    print(f"Before calibration: Brier={_brier(p, y):.4f}  ECE={_ece(p, y):.4f}")

    if args.method == "platt":
        a, b = _fit_platt(p, y)
        p_cal = _apply_platt(p, a, b)
        payload = {"method": "platt", "a": a, "b": b}
        print(f"Platt fit: a={a:.4f}  b={b:.4f}")
    else:
        bx, by = _fit_isotonic(p, y)
        p_cal = _apply_isotonic(p, bx, by)
        payload = {"method": "isotonic", "x": bx, "y": by}
        print(f"Isotonic fit: {len(bx)} breakpoints")

    print(f"After  calibration: Brier={_brier(p_cal, y):.4f}  ECE={_ece(p_cal, y):.4f}")

    payload.update(
        {
            "model": "cnn_v4_stereo",
            "fit_n": n,
            "fit_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "brier_before": round(_brier(p, y), 5),
            "brier_after": round(_brier(p_cal, y), 5),
            "ece_before": round(_ece(p, y), 5),
            "ece_after": round(_ece(p_cal, y), 5),
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Wrote {args.out}")
    # Sanity: calibration must be monotonic (a Platt 'a' < 0 would invert it).
    if args.method == "platt" and payload["a"] <= 0:
        print("WARNING: fitted slope a<=0 — mapping is non-increasing; check the data!")


if __name__ == "__main__":
    main()
