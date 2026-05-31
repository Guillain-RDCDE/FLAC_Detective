#!/usr/bin/env python3
"""Stereo-CNN feasibility verdict. Trains a compact CNN on the 2-channel
(mid+side) mel-specs from stereo_probe_features.py, under GroupKFold by source,
and answers two questions before any Hetzner GPU retrain is justified:

  1. Does an end-to-end CNN beat the 0.68 hand-crafted ceiling on band-limited
     transcodes (mp3_128), and is 320 kbps still ~0.53 (the hard wall)?
  2. THE decisive control: does the SIDE channel add anything over MID alone?
     We train 1-channel (mid) and 2-channel (mid+side) under identical folds.
     If 2ch ≈ 1ch, the stereo bet is dead — the side channel carries no usable
     transcode signal here, and a 65k-sample GPU retrain won't change that.

CPU-friendly: mel is adaptive-pooled to (C,64,128). Small CNN, 12 epochs.

    OMP_NUM_THREADS=4 .venv/Scripts/python.exe ml/stereo_probe_train.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def build_cnn(in_ch: int):
    import torch.nn as nn

    return nn.Sequential(
        nn.Conv2d(in_ch, 16, 3, padding=1),
        nn.BatchNorm2d(16),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(16, 32, 3, padding=1),
        nn.BatchNorm2d(32),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(32, 64, 3, padding=1),
        nn.BatchNorm2d(64),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Dropout(0.3),
        nn.Linear(64, 2),
    )


def run_config(X, y, groups, in_ch, epochs=12):
    """Train/eval under GroupKFold; return mean AUC and balanced accuracy."""
    import torch
    import torch.nn as nn
    from sklearn.metrics import balanced_accuracy_score, roc_auc_score
    from sklearn.model_selection import GroupKFold

    torch.manual_seed(42)
    Xc = X if in_ch == 2 else X[:, :1]  # 1ch = mid only
    aucs, bas = [], []
    for tr, te in GroupKFold(n_splits=5).split(Xc, y, groups):
        net = build_cnn(in_ch)
        opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
        w = torch.tensor(
            [1.0, (y[tr] == 0).sum() / max((y[tr] == 1).sum(), 1)], dtype=torch.float32
        )
        lossf = nn.CrossEntropyLoss(weight=w)
        Xtr = torch.tensor(Xc[tr])
        ytr = torch.tensor(y[tr])
        net.train()
        for _ in range(epochs):
            perm = torch.randperm(len(Xtr))
            for i in range(0, len(Xtr), 32):
                b = perm[i : i + 32]
                opt.zero_grad()
                lossf(net(Xtr[b]), ytr[b]).backward()
                opt.step()
        net.eval()
        with torch.no_grad():
            logits = net(torch.tensor(Xc[te]))
            proba = torch.softmax(logits, 1)[:, 1].numpy()
            pred = logits.argmax(1).numpy()
        if len(set(y[te])) == 2:
            aucs.append(roc_auc_score(y[te], proba))
        bas.append(balanced_accuracy_score(y[te], pred))
    return float(np.mean(aucs)), float(np.mean(bas))


def subset(X, y, groups, codec_arr, codec):
    """Authentics (y=0) + one codec's transcodes (y=1)."""
    mask = (codec_arr == "authentic") | (codec_arr == codec)
    return X[mask], y[mask], groups[mask]


def main(npz_path: Path) -> int:
    import torch

    torch.set_num_threads(4)
    d = np.load(npz_path, allow_pickle=True)
    X, y, groups, codec = d["X"], d["y"], d["groups"], d["codec"]
    log.info(
        f"Loaded {X.shape} ({(codec=='authentic').sum()} auth, "
        f"{(codec!='authentic').sum()} transcode)"
    )

    # Adaptive-pool mel to (C,64,128) for CPU speed.
    import torch.nn.functional as F

    Xt = F.adaptive_avg_pool2d(torch.tensor(X), (64, 128)).numpy().astype(np.float32)

    log.info("\nStereo-CNN feasibility (GroupKFold by source, AUC / balanced-acc)")
    log.info("hand-crafted baselines (texture_probe): mp3_128 AUC 0.68, mp3_320 AUC 0.53\n")
    log.info(
        f"{'codec':>8} | {'1ch mid AUC':>12} | {'2ch +side AUC':>14} | {'Δ side':>7} | verdict"
    )
    for cod in ["mp3_128", "mp3_320"]:
        Xs, ys, gs = subset(Xt, y, groups, codec, cod)
        a1, _ = run_config(Xs, ys, gs, in_ch=1)
        a2, _ = run_config(Xs, ys, gs, in_ch=2)
        delta = a2 - a1
        verdict = "side helps" if delta > 0.03 else "side adds ~nothing"
        log.info(f"{cod:>8} | {a1:>12.3f} | {a2:>14.3f} | {delta:>+7.3f} | {verdict}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--npz", default="ml/stereo_probe.npz")
    args = p.parse_args()
    sys.exit(main(Path(args.npz)))
