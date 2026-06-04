#!/usr/bin/env python3
"""Stereo-CNN feasibility verdict for the tool's blind-spot codecs (AAC/Opus/
Vorbis). Trains a compact CNN on the 2-channel (mid+side) mel-specs from
aac_stereo_probe_features.py, under GroupKFold by source, and answers ONE
question per codec:

    does the SIDE channel (L-R) add detectable transcode signal over MID alone?

We train 1-channel (mid) and 2-channel (mid+side) under identical folds. If
2ch ~= 1ch, the side channel carries nothing for that codec — it really is
near-transparent, and a 65k-sample GPU retrain won't change that. If +side
lifts the AUC meaningfully (the way it did +0.18/+0.20 for MP3), the "AAC is
fundamentally transparent" verdict was a mono artefact and a stereo v5 is on
the table.

mp3_128 is the CONTROL: it MUST come back ~0.72 stereo / big +side delta,
reproducing the known band-limited result on this harness. If it doesn't, the
harness is broken and every AAC number below is meaningless — do not trust them.

CPU-friendly: mel is adaptive-pooled to (C,64,128). Small CNN, 12 epochs.

    OMP_NUM_THREADS=4 .venv/Scripts/python.exe ml/aac_stereo_probe_train.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

CODEC_ORDER = ["mp3_128", "aac_192", "aac_256", "opus_128", "vorbis_q5"]


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

    log.info("\nStereo-CNN feasibility on blind-spot codecs (GroupKFold by source)")
    log.info("CONTROL: mp3_128 must reproduce ~0.72 stereo / big +side, or harness is broken.")
    log.info("MP3 stereo reference (band-limited probe): +side was +0.18 (128k), +0.20 (320k)\n")
    log.info(
        f"{'codec':>10} | {'1ch mid AUC':>12} | {'2ch +side AUC':>14} | {'Δ side':>7} | verdict"
    )
    present = [c for c in CODEC_ORDER if (codec == c).any()]
    for cod in present:
        Xs, ys, gs = subset(Xt, y, groups, codec, cod)
        if len(set(ys)) < 2:
            log.info(f"{cod:>10} | (only one class present, skipped)")
            continue
        a1, _ = run_config(Xs, ys, gs, in_ch=1)
        a2, _ = run_config(Xs, ys, gs, in_ch=2)
        delta = a2 - a1
        if delta > 0.05:
            verdict = "SIDE HELPS — stereo v5 worth a GPU run"
        elif delta > 0.03:
            verdict = "side helps marginally"
        else:
            verdict = "side adds ~nothing (codec transparent here)"
        log.info(f"{cod:>10} | {a1:>12.3f} | {a2:>14.3f} | {delta:>+7.3f} | {verdict}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--npz", default="ml/aac_stereo_probe.npz")
    args = p.parse_args()
    sys.exit(main(Path(args.npz)))
