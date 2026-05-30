#!/usr/bin/env python3
"""Analyse texture_temporal.csv — same three views as analyze_texture.py
(paired sign-consistency, population AUC, GroupKFold classifier) but on the
temporal-dynamics features (modulation at MP3 frame/granule rate, per-frame
flatness variance, spectral flux). Answers: does the signal that time-averaging
destroyed live in the temporal dynamics?

    .venv/Scripts/python.exe ml/analyze_temporal.py --csv ml/texture_temporal.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

FEATURES = [
    "mod38_full",
    "mod38_side",
    "mod38_hf",
    "mod76_full",
    "mod76_hf",
    "inband_flat_tstd",
    "side_flat_tstd",
    "side_energy_cv",
    "flux_mean",
    "flux_std",
]
CODECS = ["mp3_128", "mp3_320", "mp3_v0"]


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    allv = np.concatenate([pos, neg])
    ranks = allv.argsort().argsort() + 1
    a = (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    return max(a, 1 - a)


def main(csv_path: Path) -> int:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    for r in rows:
        for k in FEATURES:
            r[k] = float(r[k])
    by_src: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        by_src[r["orig_idx"]][r["kind"]] = r
    log.info(f"{len(by_src)} band-limited sources (rolloff<7k, model-flagged).")

    log.info("\n(1) PAIRED sign-consistency — %% of pairs where transcode > authentic")
    log.info(f"{'feature':>18} | " + " | ".join(f"{c:>8}" for c in CODECS))
    for feat in FEATURES:
        cells = []
        for codec in CODECS:
            d = [
                by_src[s][codec][feat] - by_src[s]["authentic"][feat]
                for s in by_src
                if codec in by_src[s] and "authentic" in by_src[s]
            ]
            cells.append(f"{np.mean([x > 0 for x in d]):>7.0%}" if d else "    n/a")
        log.info(f"{feat:>18} | " + " | ".join(f"{c:>8}" for c in cells))

    log.info("\n(2) POPULATION AUC — feature alone")
    auth = [d["authentic"] for d in by_src.values() if "authentic" in d]
    log.info(f"{'feature':>18} | " + " | ".join(f"{c:>8}" for c in CODECS))
    for feat in FEATURES:
        a_vals = np.array([r[feat] for r in auth])
        cells = [
            f"{auc(np.array([by_src[s][c][feat] for s in by_src if c in by_src[s]]), a_vals):>7.2f}"
            for c in CODECS
        ]
        log.info(f"{feat:>18} | " + " | ".join(f"{c:>8}" for c in cells))

    log.info("\n(3) GROUPED CLASSIFIER — GroupKFold by source")
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import balanced_accuracy_score, roc_auc_score
        from sklearn.model_selection import GroupKFold
    except ImportError:
        log.info("  sklearn unavailable.")
        return 0
    for codec in CODECS + ["all"]:
        codecs_use = CODECS if codec == "all" else [codec]
        X, y, g = [], [], []
        for s, d in by_src.items():
            if "authentic" not in d:
                continue
            X.append([d["authentic"][f] for f in FEATURES])
            y.append(0)
            g.append(s)
            for c in codecs_use:
                if c in d:
                    X.append([d[c][f] for f in FEATURES])
                    y.append(1)
                    g.append(s)
        X, y, g = np.array(X), np.array(y), np.array(g)
        if len(set(y)) < 2:
            continue
        clf = RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1
        )
        bas, aucs = [], []
        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
            clf.fit(X[tr], y[tr])
            bas.append(balanced_accuracy_score(y[te], clf.predict(X[te])))
            if len(set(y[te])) == 2:
                aucs.append(roc_auc_score(y[te], clf.predict_proba(X[te])[:, 1]))
        log.info(f"  {codec:>8} forest: balanced_acc={np.mean(bas):.3f}  AUC={np.mean(aucs):.3f}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/texture_temporal.csv")
    args = p.parse_args()
    sys.exit(main(Path(args.csv)))
