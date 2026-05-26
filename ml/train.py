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
    """Mel-spectrogram dataset with optional SpecAugment data augmentation.

    SpecAugment (Park et al., 2019) randomly masks frequency bands and time
    steps during training. It has been shown to substantially improve
    generalisation on audio classification tasks with limited training data.
    Applied only when `augment=True`.
    """

    def __init__(self, X: np.ndarray, y: np.ndarray, augment: bool = False,
                 freq_mask: int = 15, time_mask: int = 20, n_masks: int = 2):
        # X comes as (N, 128, T) float32. Add channel dim for Conv2d -> (N, 1, 128, T)
        self.X = X[:, None, :, :].astype(np.float32)
        self.y = y.astype(np.int64)
        # Per-spectrogram normalisation (mel values are in dB, roughly -80..0)
        # Normalise to [-1, 1] per-sample to make training stable across content.
        mn = self.X.min(axis=(2, 3), keepdims=True)
        mx = self.X.max(axis=(2, 3), keepdims=True)
        rng = np.where((mx - mn) > 1e-6, mx - mn, 1.0)
        self.X = 2 * (self.X - mn) / rng - 1.0
        self.augment = augment
        self.freq_mask = freq_mask
        self.time_mask = time_mask
        self.n_masks = n_masks
        # RNG: per-instance so different workers don't share state.
        self._rng = np.random.default_rng()

    def __len__(self):
        return len(self.y)

    def _spec_augment(self, x: np.ndarray) -> np.ndarray:
        """Apply SpecAugment in-place on a copy of `x` (shape (1, n_mels, T))."""
        x = x.copy()
        n_mels = x.shape[1]
        n_time = x.shape[2]
        for _ in range(self.n_masks):
            # Frequency mask
            if self.freq_mask > 0:
                f = self._rng.integers(0, self.freq_mask + 1)
                if f > 0:
                    f0 = self._rng.integers(0, max(n_mels - f, 1))
                    x[:, f0:f0 + f, :] = -1.0  # masked = our normalisation's minimum
            # Time mask
            if self.time_mask > 0:
                t = self._rng.integers(0, self.time_mask + 1)
                if t > 0:
                    t0 = self._rng.integers(0, max(n_time - t, 1))
                    x[:, :, t0:t0 + t] = -1.0
        return x

    def __getitem__(self, idx):
        x = self.X[idx]
        if self.augment:
            x = self._spec_augment(x)
        return x, self.y[idx]


class FocalLoss(nn.Module):
    """Focal loss (Lin et al., 2017) with per-class alpha weighting.

    For binary classification with class imbalance, focal loss focuses
    training on the hard examples by down-weighting easy ones:

        FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    The `alpha` tensor (one weight per class) up-weights the rarer class.
    `gamma` controls how aggressively we discount easy examples (gamma=2 is
    the value from the paper, well-tuned for most use cases).
    """

    def __init__(self, alpha: torch.Tensor, gamma: float = 2.0):
        super().__init__()
        self.register_buffer("alpha", alpha)
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        # log-softmax for numerical stability
        log_probs = F.log_softmax(logits, dim=1)
        probs = log_probs.exp()
        # Gather the per-sample p_t and log p_t
        gathered_log = log_probs.gather(1, target.unsqueeze(1)).squeeze(1)
        gathered_p   = probs.gather(1, target.unsqueeze(1)).squeeze(1)
        alpha_t      = self.alpha.gather(0, target)
        focal_factor = (1 - gathered_p).pow(self.gamma)
        loss = -alpha_t * focal_factor * gathered_log
        return loss.mean()


class TranscodeCNN(nn.Module):
    """ResNet-18 pretrained on ImageNet, fine-tuned for binary mel-spec classification.

    Input  : (B, 1, 128, T)  with T ≈ 431 for 10 s @ sr=22050, hop=512
    Output : (B, 2)          logits for {authentic, transcoded}

    Why pretrained ResNet rather than a from-scratch custom CNN:
      * Mel-spectrograms are images. ResNet has learnt to recognise edges,
        textures and shapes on ImageNet — those primitives are exactly what
        distinguishes the spectral signature of a transcode from a real
        recording.
      * 11M parameters vs ~700K for the custom CNN — far more expressive,
        avoids the convergence collapses we saw in v2 attempts #1-#3.
      * Standard baseline for audio classification in 2026.

    We adapt the 3-channel ImageNet input to our single-channel mel input by
    averaging the first conv layer's weights across the RGB axis. This keeps
    the pretrained features alive while accepting a 1-channel tensor.
    """

    def __init__(self):
        super().__init__()
        try:
            from torchvision.models import resnet18, ResNet18_Weights
            backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        except (ImportError, Exception):
            # Fallback: untrained ResNet (no internet at runtime is fine)
            from torchvision.models import resnet18
            backbone = resnet18(weights=None)
            logger = logging.getLogger(__name__)
            logger.warning("ResNet-18 pretrained weights unavailable; training from scratch")

        # Adapt first conv to accept 1-channel input by averaging RGB weights.
        # Shape was (64, 3, 7, 7) → becomes (64, 1, 7, 7).
        old_conv = backbone.conv1
        new_conv = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        with torch.no_grad():
            new_conv.weight.copy_(old_conv.weight.mean(dim=1, keepdim=True))
        backbone.conv1 = new_conv

        # Replace 1000-class ImageNet head with binary classifier.
        backbone.fc = nn.Linear(backbone.fc.in_features, 2)

        self.backbone = backbone

    def forward(self, x):
        return self.backbone(x)


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
    # Balanced accuracy = mean of per-class recall. Crucial for imbalanced
    # datasets: if the model just predicts the majority class, raw `acc` and
    # F1-on-class-1 stay high, but balanced_acc collapses to 0.5 (random).
    # We use this as the model-selection criterion.
    recall_pos = tp / max(tp + fn, 1)             # = recall on transcoded
    recall_neg = tn / max(tn + fp, 1)             # = specificity = recall on authentic
    balanced_acc = (recall_pos + recall_neg) / 2
    return dict(loss=loss_sum / max(total, 1), acc=acc, precision=prec,
                recall=rec, f1=f1, balanced_acc=balanced_acc,
                recall_pos=recall_pos, recall_neg=recall_neg,
                tp=tp, fp=fp, fn=fn, tn=tn)


def main(features_path: Path, output_dir: Path, epochs: int, batch_size: int,
         lr: float, mem_fraction: float, early_stop_patience: int = 8) -> int:
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

    # Augmentation only at train time. Validation and test must see the
    # un-augmented signal so metrics reflect real-world inference behaviour.
    train_ds = MelDataset(X[train_idx], y[train_idx], augment=True)
    val_ds   = MelDataset(X[val_idx],   y[val_idx],   augment=False)
    test_ds  = MelDataset(X[test_idx],  y[test_idx],  augment=False)

    # Re-balance train batches: rarer class (authentic, label 0) gets up-weighted.
    train_y = y[train_idx]
    class_counts = np.bincount(train_y)
    sampler_weights = (1.0 / class_counts)[train_y]
    sampler = WeightedRandomSampler(sampler_weights, num_samples=len(train_y), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds, batch_size=batch_size, shuffle=False,
                              num_workers=2, pin_memory=True)

    model = TranscodeCNN().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    log.info(f"Model: TranscodeCNN, {n_params:,} parameters")
    log.info(f"Augmentation: SpecAugment(freq=15, time=20, n_masks=2) on train split")

    # Class balancing strategy: WeightedRandomSampler (above) already ensures
    # each batch is ~50/50 authentic/transcoded. Stacking focal loss with
    # alpha weighting on top — as the previous v2 attempt did — caused a
    # double-correction that made the model collapse to "always predict
    # authentic". Plain CrossEntropy on balanced batches is the correct
    # combination here.
    log.info(f"Class counts (train): {class_counts.tolist()} (handled by WeightedRandomSampler)")

    # Lower LR than v1 — the previous v2 run oscillated wildly between
    # "predict all authentic" and "predict all transcoded" with lr=1e-3.
    # 3e-4 gives smoother convergence on this imbalanced setup.
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=4
    )
    criterion = nn.CrossEntropyLoss()

    output_dir.mkdir(parents=True, exist_ok=True)
    # Track balanced_acc (mean of per-class recalls) for model selection.
    # This is robust to class imbalance, unlike raw accuracy or F1-on-class-1.
    best_metric = -1.0
    best_epoch = 0
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
        # Step on balanced_acc, not F1 (which is biased on imbalanced sets).
        scheduler.step(val_metrics["balanced_acc"])
        dt = time.time() - t0

        log.info(
            f"Epoch {epoch:3d}/{epochs} | "
            f"train_loss={train_loss:.4f} | "
            f"val_loss={val_metrics['loss']:.4f} "
            f"bal_acc={val_metrics['balanced_acc']:.4f} "
            f"(auth={val_metrics['recall_neg']:.3f}, trans={val_metrics['recall_pos']:.3f}) "
            f"f1={val_metrics['f1']:.4f} | "
            f"{dt:.1f}s"
        )
        history.append(dict(epoch=epoch, train_loss=train_loss, **val_metrics, time=dt))

        if val_metrics["balanced_acc"] > best_metric:
            best_metric = val_metrics["balanced_acc"]
            best_epoch = epoch
            torch.save({"model_state": model.state_dict(),
                        "epoch": epoch, "val_metrics": val_metrics},
                       output_dir / "best.pt")
            log.info(f"  New best (balanced_acc={best_metric:.4f}) saved.")

        # Early stopping: bail out if no improvement for `early_stop_patience` epochs.
        if epoch - best_epoch >= early_stop_patience:
            log.info(f"Early stopping at epoch {epoch}: no improvement for "
                     f"{early_stop_patience} epochs (best was epoch {best_epoch}).")
            break

    # Final test
    ckpt = torch.load(output_dir / "best.pt", weights_only=True)
    model.load_state_dict(ckpt["model_state"])
    test_metrics = evaluate(model, test_loader, device)
    log.info(f"Best checkpoint test metrics: {test_metrics}")

    with open(output_dir / "history.json", "w") as f:
        json.dump({"history": history, "test_metrics": test_metrics,
                   "best_balanced_acc": best_metric, "best_epoch": ckpt["epoch"]}, f, indent=2)
    log.info(f"All artefacts in {output_dir}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--features", default="features/dataset.npz")
    p.add_argument("--output",   default="models/cnn_v2")
    p.add_argument("--epochs",   type=int, default=50)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr",       type=float, default=3e-4)
    p.add_argument("--early-stop-patience", type=int, default=8,
                   help="Stop if val_f1 hasn't improved in N epochs")
    p.add_argument("--mem-fraction", type=float, default=0.5,
                   help="Cap GPU VRAM at this fraction (0..1) to coexist with other services")
    args = p.parse_args()
    sys.exit(main(Path(args.features), Path(args.output),
                  args.epochs, args.batch_size, args.lr, args.mem_fraction,
                  args.early_stop_patience))
