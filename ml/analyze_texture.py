#!/usr/bin/env python3
"""Analyse texture_probe.csv: does ANY texture feature separate band-limited
authentic FLACs from their transcodes — where the cliff, the CNN and Rule 9 fail?

Three views, weakest assumption to strongest:
  1. PAIRED sign-consistency — for each feature x codec, the fraction of sources
     whose transcode shifts the SAME direction vs its own authentic. Controls for
     the source; the most sensitive "is there any signal" test. >~85% = real.
  2. POPULATION AUC — can the feature alone rank a single file (no paired
     original, as at deployment)? 0.5 = useless, 1.0 = perfect.
  3. GROUPED CLASSIFIER — RandomForest + LogisticRegression on all features, with
     GroupKFold by source (a source's authentic and transcodes never split across
     folds -> no leakage). Reports per-codec balanced accuracy & AUC.

    .venv/Scripts/python.exe ml/analyze_texture.py --csv ml/texture_probe.csv
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
    "side_mid_ratio",
    "lr_corr",
    "side_to_mid_rolloff",
    "holes_inband",
    "flatness_inband",
    "side_flatness_inband",
    "terrace_peakfrac",
    "preecho_pct",
    "aliasing_corr",
    "mp3_pattern",
]
CODECS = ["mp3_128", "mp3_320", "mp3_v0"]


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC: P(pos ranked above neg). Symmetric reported as max(a,1-a)."""
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
    stereo_srcs = [
        s for s, d in by_src.items() if "authentic" in d and d["authentic"]["is_stereo"] == "1"
    ]
    log.info(
        f"{len(by_src)} sources ({len(stereo_srcs)} genuinely stereo). "
        f"All sources rolloff<7k, model-flagged."
    )

    # 1. PAIRED sign-consistency (transcode vs its own authentic).
    log.info("\n" + "=" * 72)
    log.info("(1) PAIRED sign-consistency  —  %% of pairs where transcode > authentic")
    log.info("    (50%% = no signal; far from 50%% either way = consistent shift)")
    log.info(f"{'feature':>22} | " + " | ".join(f"{c:>9}" for c in CODECS))
    for feat in FEATURES:
        cells = []
        for codec in CODECS:
            deltas = [
                by_src[s][codec][feat] - by_src[s]["authentic"][feat]
                for s in by_src
                if codec in by_src[s] and "authentic" in by_src[s]
            ]
            deltas = [d for d in deltas if not np.isnan(d)]
            frac = np.mean([d > 0 for d in deltas]) if deltas else 0.5
            cells.append(f"{frac:>8.0%}")
        log.info(f"{feat:>22} | " + " | ".join(f"{c:>9}" for c in cells))

    # 2. POPULATION AUC (feature alone, authentic vs transcode pooled).
    log.info("\n" + "=" * 72)
    log.info("(2) POPULATION AUC  —  feature alone discriminating one file")
    auth = [d["authentic"] for d in by_src.values() if "authentic" in d]
    log.info(f"{'feature':>22} | " + " | ".join(f"{c:>9}" for c in CODECS) + " |   pooled")
    for feat in FEATURES:
        a_vals = np.array([r[feat] for r in auth])
        cells = []
        for codec in CODECS:
            t_vals = np.array([by_src[s][codec][feat] for s in by_src if codec in by_src[s]])
            cells.append(f"{auc(t_vals, a_vals):>8.2f}")
        t_all = np.array([by_src[s][c][feat] for s in by_src for c in CODECS if c in by_src[s]])
        log.info(
            f"{feat:>22} | "
            + " | ".join(f"{c:>9}" for c in cells)
            + f" |   {auc(t_all, a_vals):.2f}"
        )

    # 3. GROUPED CLASSIFIER (no source leakage).
    log.info("\n" + "=" * 72)
    log.info("(3) GROUPED CLASSIFIER  —  GroupKFold by source, balanced acc / AUC")
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import balanced_accuracy_score, roc_auc_score
        from sklearn.model_selection import GroupKFold
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        log.info("  sklearn unavailable — skipping.")
        return 0

    for codec in CODECS + ["all"]:
        X, y, g = [], [], []
        codecs_use = CODECS if codec == "all" else [codec]
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
        gkf = GroupKFold(n_splits=5)
        for name, clf in [
            (
                "logreg",
                make_pipeline(
                    StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")
                ),
            ),
            (
                "forest",
                RandomForestClassifier(
                    n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1
                ),
            ),
        ]:
            bas, aucs = [], []
            for tr, te in gkf.split(X, y, g):
                clf.fit(X[tr], y[tr])
                pred = clf.predict(X[te])
                proba = clf.predict_proba(X[te])[:, 1]
                bas.append(balanced_accuracy_score(y[te], pred))
                if len(set(y[te])) == 2:
                    aucs.append(roc_auc_score(y[te], proba))
            log.info(
                f"  {codec:>8} {name:>7}: balanced_acc={np.mean(bas):.3f}  AUC={np.mean(aucs):.3f}"
            )

    # Feature importance from a forest on all data.
    from sklearn.ensemble import RandomForestClassifier as RF

    X, y = [], []
    for d in by_src.values():
        if "authentic" not in d:
            continue
        X.append([d["authentic"][f] for f in FEATURES])
        y.append(0)
        for c in CODECS:
            if c in d:
                X.append([d[c][f] for f in FEATURES])
                y.append(1)
    rf = RF(n_estimators=300, random_state=42, class_weight="balanced").fit(
        np.array(X), np.array(y)
    )
    log.info("\n  Feature importance (forest, all codecs):")
    for f, imp in sorted(zip(FEATURES, rf.feature_importances_), key=lambda t: -t[1]):
        log.info(f"    {f:>22}: {imp:.3f}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/texture_probe.csv")
    args = p.parse_args()
    sys.exit(main(Path(args.csv)))
