#!/usr/bin/env python3
"""Train a CNN classifier on mel-spectrograms to distinguish authentic vs
transcoded FLAC files.

Architecture: a compact custom CNN (5 conv blocks + GAP + 1 FC).
~700 K parameters, fits in <100 MB VRAM, trains in 30-90 min on RTX 4000 Ada.

VRAM safety: capped at 50% of total via torch.cuda.set_per_process_memory_fraction
so concurrent Whisper inference on the same GPU does not OOM.

Run on Hetzner:
    venv/bin/python ml/train.py \
        --features features/dataset.npz \
        --output models/cnn_v1 \
        --epochs 25 \
        --batch-size 32
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


class MelDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        # X comes as (N, 128, T) float32. Add channel dim for Conv2d -> (N, 1, 128, T)
        self.X = X[:, None, :, :].astype(np.float32)
        self.y = y.astype(np.int64)
        # Per-spectrogram normalisation (mel values are in dB, roughly -80..0)
        # Normalise to [-1, 1] per-sample to make training stable across content.
        mn = self.X.min(axis=(2, 3), keepdims=True)
        mx = self.X.max(axis=(2, 3), keepdims=True)
        rng = np.where((mx - mn) > 1e-6, mx - mn, 1.0)
        self.X = 2 * (self.X - mn) / rng - 1.0

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class TranscodeCNN(nn.Module):
    """Compact 2D CNN classifier for mel-spectrograms.

    Input  : (B, 1, 128, T)  with T ≈ 431 for 10 s @ sr=22050, hop=512
    Output : (B, 2)          logits for {authentic, transcoded}
    """
    def __init__(self):
        super().__init__()
        def block(in_c, out_c, pool=True):
            layers = [
                nn.Conv2d(in_c, out_c, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
            ]
            if pool:
                layers.append(nn.MaxPool2d(2))
            return nn.Sequential(*layers)
        self.feat = nn.Sequential(
            block(1,   32),
            block(32,  64),
            block(64,  128),
            block(128, 128),
            block(128, 128, pool=False),
        )
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.drop = nn.Dropout(0.3)
        self.fc = nn.Linear(128, 2)

    def forward(self, x):
        x = self.feat(x)
        x = self.gap(x).flatten(1)
        x = self.drop(x)
        return self.fc(x)


def stratified_split(y: np.ndarray, val_frac: float = 0.15, test_frac: float = 0.15,
                     seed: int = 42) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-class shuffle then split into train / val / test indices."""
    rng = np.random.default_rng(seed)
    train_idx, val_idx, test_idx = [], [], []
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        n_test = int(round(len(idx) * test_frac))
        n_val  = int(round(len(idx) * val_frac))
        test_idx.extend(idx[:n_test])
        val_idx.extend(idx[n_test:n_test + n_val])
        train_idx.extend(idx[n_test + n_val:])
    return (np.array(train_idx, dtype=np.int64),
            np.array(val_idx, dtype=np.int64),
            np.array(test_idx, dtype=np.int64))


def evaluate(model, loader, device) -> dict:
    model.eval()
    correct = 0
    total = 0
    tp = fp = fn = tn = 0
    loss_sum = 0.0
    crit = nn.CrossEntropyLoss(reduction="sum")
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            logits = model(xb)
            loss_sum += crit(logits, yb).item()
            pred = logits.argmax(1)
            correct += (pred == yb).sum().item()
            total += yb.numel()
            tp += ((pred == 1) & (yb == 1)).sum().item()
            fp += ((pred == 1) & (yb == 0)).sum().item()
            fn += ((pred == 0) & (yb == 1)).sum().item()
            tn += ((pred == 0) & (yb == 0)).sum().item()
    acc = correct / max(total, 1)
    prec = tp / max(tp + fp, 1)
    rec  = tp / max(tp + fn, 1)
    f1   = 2 * prec * rec / max(prec + rec, 1e-9)
    return dict(loss=loss_sum / max(total, 1), acc=acc, precision=prec,
                recall=rec, f1=f1, tp=tp, fp=fp, fn=fn, tn=tn)


def main(features_path: Path, output_dir: Path, epochs: int, batch_size: int,
         lr: float, mem_fraction: float) -> int:
    log.info(f"Loading features from {features_path}")
    data = np.load(features_path, allow_pickle=True)
    X, y = data["X"], data["y"]
    log.info(f"X shape: {X.shape}, y shape: {y.shape}, "
             f"class balance: {np.bincount(y).tolist()}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Device: {device}")
    if device.type == "cuda":
        torch.cuda.set_per_process_memory_fraction(mem_fraction)
        log.info(f"VRAM cap: {mem_fraction*100:.0f}% "
                 f"({mem_fraction * torch.cuda.get_device_properties(0).total_memory/1024**3:.1f} GB)")

    train_idx, val_idx, test_idx = stratified_split(y, val_frac=0.15, test_frac=0.15)
    log.info(f"Split sizes: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

    train_ds = MelDataset(X[train_idx], y[train_idx])
    val_ds   = MelDataset(X[val_idx],   y[val_idx])
    test_ds  = MelDataset(X[test_idx],  y[test_idx])

    # Re-balance train batches: rarer class (authentic, label 0) gets up-weighted.
    train_y = y[train_idx]
    class_counts = np.bincount(train_y)
    class_weights = 1.0 / class_counts
    sample_weights = class_weights[train_y]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(train_y), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)

    model = TranscodeCNN().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    log.info(f"Model: TranscodeCNN, {n_params:,} parameters")

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=3
    )
    criterion = nn.CrossEntropyLoss()

    output_dir.mkdir(parents=True, exist_ok=True)
    best_val_f1 = -1.0
    history = []

    for epoch in range(1, epochs + 1):
        model.train()
        t0 = time.time()
        running = 0.0
        n = 0
        for xb, yb in train_loader:
            xb = xb.to(device, non_blocking=True)
            yb = yb.to(device, non_blocking=True)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            running += loss.item() * yb.numel()
            n += yb.numel()
        train_loss = running / n

        val_metrics = evaluate(model, val_loader, device)
        scheduler.step(val_metrics["f1"])
        dt = time.time() - t0

        log.info(
            f"Epoch {epoch:3d}/{epochs} | "
            f"train_loss={train_loss:.4f} | "
            f"val_loss={val_metrics['loss']:.4f} "
            f"val_acc={val_metrics['acc']:.4f} "
            f"val_f1={val_metrics['f1']:.4f} | "
            f"{dt:.1f}s"
        )
        history.append(dict(epoch=epoch, train_loss=train_loss, **val_metrics, time=dt))

        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            torch.save({"model_state": model.state_dict(),
                        "epoch": epoch, "val_metrics": val_metrics},
                       output_dir / "best.pt")
            log.info(f"  New best (val_f1={best_val_f1:.4f}) saved.")

    # Final test
    ckpt = torch.load(output_dir / "best.pt", weights_only=True)
    model.load_state_dict(ckpt["model_state"])
    test_metrics = evaluate(model, test_loader, device)
    log.info(f"Best checkpoint test metrics: {test_metrics}")

    with open(output_dir / "history.json", "w") as f:
        json.dump({"history": history, "test_metrics": test_metrics,
                   "best_val_f1": best_val_f1, "best_epoch": ckpt["epoch"]}, f, indent=2)
    log.info(f"All artefacts in {output_dir}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--features", default="features/dataset.npz")
    p.add_argument("--output",   default="models/cnn_v1")
    p.add_argument("--epochs",   type=int, default=25)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr",       type=float, default=1e-3)
    p.add_argument("--mem-fraction", type=float, default=0.5,
                   help="Cap GPU VRAM at this fraction (0..1) to coexist with other services")
    args = p.parse_args()
    sys.exit(main(Path(args.features), Path(args.output),
                  args.epochs, args.batch_size, args.lr, args.mem_fraction))
