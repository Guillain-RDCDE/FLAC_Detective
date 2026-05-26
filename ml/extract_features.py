#!/usr/bin/env python3
"""Extract mel-spectrogram features from authentic + transcoded FLAC files.

Output structure: a single .npz file (compressed npy archive) containing:

  X      : float32 array, shape (N, 128, T)   — mel-spectrograms (128 mel bins,
                                                T time frames)
  y      : int64   array, shape (N,)          — 0 for authentic, 1 for transcoded
  paths  : object  array, shape (N,)          — relative source paths
  labels : object  array, shape (N,)          — "authentic" / "mp3_192" / ...
  config : dict                                — sample-rate, hop, fmax, etc.

Sampling strategy: take a single ~10 second clip from the middle of each file.
The middle of the track is the most musically representative segment — avoids
fade-ins, intros, and silent tails.

Run on Hetzner after generate_transcodes.py:
    venv/bin/python ml/extract_features.py \
        --input dataset --output features/dataset.npz --workers 12
"""

from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SAMPLE_RATE = 44100   # CRITICAL: keep full spectrum up to ~22kHz.
                      # MP3 transcodes leave their signature ("cliff") at 14-21 kHz
                      # depending on bitrate. Resampling to 22050 (Nyquist 11kHz)
                      # erases exactly the signal we are trying to learn.
SEGMENT_SEC = 10.0
N_MELS = 128
N_FFT = 2048
HOP = 512


def _extract_one(args: tuple[Path, int, str, Path]) -> tuple[np.ndarray | None, int, str, str]:
    """Worker: extract mel-spectrogram for one audio file.

    Returns (mel, label, label_name, rel_path) or (None, ...) on failure.
    """
    flac_path, label, label_name, root = args
    try:
        import librosa
    except ImportError:
        return (None, label, label_name, str(flac_path))

    try:
        # Load 10 seconds from the middle of the track.
        info = librosa.get_duration(path=str(flac_path))
        offset = max(0.0, (info - SEGMENT_SEC) / 2)
        y, sr = librosa.load(str(flac_path), sr=SAMPLE_RATE,
                             offset=offset, duration=SEGMENT_SEC, mono=True)
        if len(y) < SAMPLE_RATE * SEGMENT_SEC * 0.5:
            # Less than half the expected length — too short, skip.
            return (None, label, label_name, str(flac_path))

        # Pad / truncate to exactly the expected length so all mel-specs have
        # the same shape.
        target_len = int(SAMPLE_RATE * SEGMENT_SEC)
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)))
        else:
            y = y[:target_len]

        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_fft=N_FFT, hop_length=HOP, n_mels=N_MELS, fmax=sr // 2,
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        rel = flac_path.relative_to(root).as_posix() if root in flac_path.parents else str(flac_path)
        return (mel_db, label, label_name, rel)
    except Exception as e:
        log.warning(f"Failed {flac_path}: {e}")
        return (None, label, label_name, str(flac_path))


def collect_jobs(input_root: Path) -> list:
    """Build the worker arg list: (path, label, label_name, root)."""
    jobs = []
    auth_root = input_root / "authentic"
    if auth_root.is_dir():
        for p in auth_root.rglob("*.flac"):
            jobs.append((p, 0, "authentic", input_root))

    trans_root = input_root / "transcoded"
    if trans_root.is_dir():
        for codec_dir in sorted(trans_root.iterdir()):
            if not codec_dir.is_dir():
                continue
            label_name = codec_dir.name  # e.g. "mp3_192"
            for p in codec_dir.rglob("*.flac"):
                jobs.append((p, 1, label_name, input_root))
    return jobs


def main(input_root: Path, output_path: Path, workers: int) -> int:
    if not input_root.is_dir():
        log.error(f"Input dir not found: {input_root}")
        return 1
    jobs = collect_jobs(input_root)
    log.info(f"Collected {len(jobs)} files: "
             f"{sum(1 for j in jobs if j[1] == 0)} authentic, "
             f"{sum(1 for j in jobs if j[1] == 1)} transcoded")

    if not jobs:
        log.error("No files to process.")
        return 1

    try:
        from tqdm import tqdm
        progress = tqdm(total=len(jobs), unit="file")
    except ImportError:
        progress = None

    mels: list[np.ndarray] = []
    labels: list[int] = []
    label_names: list[str] = []
    paths: list[str] = []
    skipped = 0

    with mp.Pool(processes=workers) as pool:
        for result in pool.imap_unordered(_extract_one, jobs, chunksize=8):
            mel, label, label_name, rel = result
            if mel is None:
                skipped += 1
            else:
                mels.append(mel)
                labels.append(label)
                label_names.append(label_name)
                paths.append(rel)
            if progress is not None:
                progress.update(1)
                progress.set_postfix(ok=len(mels), skip=skipped)
    if progress is not None:
        progress.close()

    if not mels:
        log.error("No features extracted.")
        return 2

    X = np.stack(mels, axis=0)
    y = np.array(labels, dtype=np.int64)
    log.info(f"Final X shape: {X.shape}, dtype {X.dtype}, size {X.nbytes/1024**2:.1f} MB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        X=X, y=y,
        paths=np.array(paths, dtype=object),
        labels=np.array(label_names, dtype=object),
        config=dict(sample_rate=SAMPLE_RATE, segment_sec=SEGMENT_SEC,
                    n_mels=N_MELS, n_fft=N_FFT, hop=HOP),
    )
    log.info(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input",  default="dataset")
    p.add_argument("--output", default="features/dataset.npz")
    p.add_argument("--workers", type=int, default=12)
    args = p.parse_args()
    sys.exit(main(Path(args.input), Path(args.output), args.workers))
