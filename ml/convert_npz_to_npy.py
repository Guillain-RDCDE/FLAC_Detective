#!/usr/bin/env python3
"""Convert a compressed .npz dataset (loaded entirely into RAM by np.load)
into a set of mmap-able .npy files, so train.py can stream samples from
disk without loading the full feature tensor into RAM.

Why: on a 62 GB host shared with other services, loading a 27 GB compressed
.npz expands the resident memory above the OOM threshold the moment train.py
also instantiates DataLoader workers. Storing X as a plain .npy lets
`np.load(path, mmap_mode='r')` keep the array on disk and page in chunks.

Trade-off: the uncompressed .npy is ~32 GB on disk, vs ~10 GB for the .npz.
We have 1.4 TB free on Hetzner; this is fine.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main(npz_path: Path, output_dir: Path) -> int:
    if not npz_path.is_file():
        print(f"Not found: {npz_path}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {npz_path} (this peaks RAM at ~size of decompressed arrays)...")
    data = np.load(npz_path, allow_pickle=True)
    X = data["X"]
    y = data["y"]
    paths = data["paths"]
    labels = data["labels"]
    config = data["config"].item() if data["config"].dtype == object else data["config"]

    print(f"  X     : {X.shape} {X.dtype} ({X.nbytes/1024**3:.2f} GB)")
    print(f"  y     : {y.shape} {y.dtype}")
    print(f"  paths : {paths.shape}")
    print(f"  labels: {labels.shape}")

    print(f"Saving uncompressed .npy files to {output_dir}/ ...")
    np.save(output_dir / "X.npy", X)
    np.save(output_dir / "y.npy", y)
    np.save(output_dir / "paths.npy", paths, allow_pickle=True)
    np.save(output_dir / "labels.npy", labels, allow_pickle=True)
    with open(output_dir / "config.json", "w") as f:
        json.dump(dict(config), f, indent=2, default=str)

    total = sum((output_dir / f).stat().st_size for f in
                ("X.npy", "y.npy", "paths.npy", "labels.npy")) / 1024**3
    print(f"Done. Total on-disk: {total:.2f} GB.")
    print(f"\nLoad in train.py with:")
    print(f"  X = np.load('{output_dir}/X.npy', mmap_mode='r')")
    print(f"  y = np.load('{output_dir}/y.npy')   # small, in-RAM is fine")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input", default="features/dataset.npz")
    p.add_argument("--output-dir", default="features/mmap")
    args = p.parse_args()
    sys.exit(main(Path(args.input), Path(args.output_dir)))
