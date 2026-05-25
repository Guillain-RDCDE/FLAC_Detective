#!/usr/bin/env python3
"""Export a trained checkpoint to TorchScript for deployment in FLAC Detective.

TorchScript .pt files load without the full PyTorch Python package being
importable at the call site — only torch is needed. Smaller, faster startup,
no dependency on the training-time module layout.

Run on Hetzner after train.py:
    venv/bin/python ml/export_torchscript.py \
        --checkpoint models/cnn_v1/best.pt \
        --output     models/cnn_v1.ts.pt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

# Re-import the architecture so we can wrap the trained weights.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from train import TranscodeCNN  # noqa: E402


def main(checkpoint_path: Path, output_path: Path) -> int:
    if not checkpoint_path.is_file():
        print(f"Checkpoint not found: {checkpoint_path}", file=sys.stderr)
        return 1
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model = TranscodeCNN()
    model.load_state_dict(ckpt["model_state"])
    model.eval()

    # Trace with a representative input shape: (1, 1, 128, 431) for a 10s clip
    # at sr=22050 / hop=512 -> 22050 * 10 / 512 = 431 frames.
    example = torch.randn(1, 1, 128, 431)
    traced = torch.jit.trace(model, example)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    traced.save(str(output_path))

    size_mb = output_path.stat().st_size / 1024**2
    val = ckpt.get("val_metrics", {})
    print(f"Exported {output_path} ({size_mb:.2f} MB)")
    print(f"Best checkpoint epoch={ckpt['epoch']} val_metrics={val}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--checkpoint", default="models/cnn_v1/best.pt")
    p.add_argument("--output",     default="models/cnn_v1.ts.pt")
    args = p.parse_args()
    sys.exit(main(Path(args.checkpoint), Path(args.output)))
