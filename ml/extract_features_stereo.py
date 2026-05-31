#!/usr/bin/env python3
"""Extract 2-channel (mid+side) mel-spectrograms for the v4 stereo experiment.

Motivated by a validation probe (ml/stereo_probe_*.py): on band-limited material
a MONO mel-spec CNN is a coin flip (AUC ~0.51), but adding the stereo SIDE
channel (L-R) — where MP3 joint-stereo coding leaves a fingerprint the mono
representation literally cannot see — lifts AUC to ~0.72 at both 128 and 320 kbps.
The v3 model is mono, so it's blind to this. This extractor feeds a 2-channel
(mid, side) model.

Two design points that matter:

  * 16-BIT QUANTISATION. The transcodes on disk are 24-bit (s32) while the
    authentic sources are 16-bit. A stereo model could cheat by reading that
    bit-depth difference off the side channel's noise floor — a pipeline
    artefact, not a generalisable MP3 signature. We quantise BOTH to 16-bit
    before the mel so the model can only learn the real joint-stereo fingerprint.
    (The probe confirmed the signal survives matched-16-bit, so this is safe.)

  * DIRECT MEMMAP OUTPUT. A 2-channel float32 tensor for ~65 k samples is ~57 GB
    — np.stack-ing it (as the mono extractor does) would OOM the shared 62 GB
    host. We write each sample straight into a pre-allocated float16 memmap, so
    peak RAM is one sample. train.py reads the dir with mmap_mode='r'.

Output dir: X.npy (N, 2, 128, T) float16 raw mel_db (train.py normalises
per-channel at load), y.npy, paths.npy, labels.npy, config.json.

    venv/bin/python ml/extract_features_stereo.py \
        --input dataset --output-dir features_v4_stereo --workers 12
"""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SAMPLE_RATE = 44100  # MUST match ml/extract_features.py — full spectrum to ~22 kHz
SEGMENT_SEC = 10.0
N_MELS = 128
N_FFT = 2048
HOP = 512
T_FRAMES = int(SAMPLE_RATE * SEGMENT_SEC) // HOP + 1  # 862


def _quant16(sig: np.ndarray) -> np.ndarray:
    """Quantise float audio to the 16-bit grid (neutralise bit-depth confound)."""
    return np.round(sig * 32768.0) / 32768.0


def _extract_one(args):
    """Worker: return (mel(2,128,T) float16 | None, label, label_name, rel_path)."""
    flac_path, label, label_name, root = args
    try:
        import librosa
    except ImportError:
        return (None, label, label_name, str(flac_path))
    try:
        dur = librosa.get_duration(path=str(flac_path))
        offset = max(0.0, (dur - SEGMENT_SEC) / 2)
        y, sr = librosa.load(
            str(flac_path), sr=SAMPLE_RATE, offset=offset, duration=SEGMENT_SEC, mono=False
        )
        if y.ndim == 1:
            mid = y
            side = np.zeros_like(y)
        else:
            mid = 0.5 * (y[0] + y[1])
            side = 0.5 * (y[0] - y[1])
        target = int(SAMPLE_RATE * SEGMENT_SEC)
        chans = []
        for sig in (mid, side):
            if len(sig) < target * 0.5:
                return (None, label, label_name, str(flac_path))
            sig = np.pad(sig, (0, target - len(sig))) if len(sig) < target else sig[:target]
            sig = _quant16(sig)
            mel = librosa.feature.melspectrogram(
                y=sig, sr=sr, n_fft=N_FFT, hop_length=HOP, n_mels=N_MELS, fmax=sr // 2
            )
            chans.append(librosa.power_to_db(mel, ref=np.max).astype(np.float16))
        mel2 = np.stack(chans, axis=0)  # (2, 128, T)
        if mel2.shape != (2, N_MELS, T_FRAMES):
            return (None, label, label_name, str(flac_path))
        rel = (
            flac_path.relative_to(root).as_posix() if root in flac_path.parents else str(flac_path)
        )
        return (mel2, label, label_name, rel)
    except Exception as e:  # noqa: BLE001
        log.warning(f"Failed {flac_path}: {e}")
        return (None, label, label_name, str(flac_path))


def collect_jobs(input_root: Path) -> list:
    jobs = []
    auth = input_root / "authentic"
    if auth.is_dir():
        for p in auth.rglob("*.flac"):
            jobs.append((p, 0, "authentic", input_root))
    trans = input_root / "transcoded"
    if trans.is_dir():
        for codec_dir in sorted(trans.iterdir()):
            if codec_dir.is_dir():
                for p in codec_dir.rglob("*.flac"):
                    jobs.append((p, 1, codec_dir.name, input_root))
    return jobs


def main(input_root: Path, out_dir: Path, workers: int, limit_per_class: int = 0) -> int:
    if not input_root.is_dir():
        log.error(f"Input dir not found: {input_root}")
        return 1
    jobs = collect_jobs(input_root)
    if limit_per_class:  # smoke test: first L authentic + first L transcoded
        auth = [j for j in jobs if j[1] == 0][:limit_per_class]
        trans = [j for j in jobs if j[1] == 1][:limit_per_class]
        jobs = auth + trans
        log.info(f"--limit-per-class {limit_per_class}: {len(jobs)} jobs (smoke test)")
    n = len(jobs)
    log.info(
        f"Collected {n} files: {sum(1 for j in jobs if j[1]==0)} authentic, "
        f"{sum(1 for j in jobs if j[1]==1)} transcoded"
    )
    if not jobs:
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    # Pre-allocate the memmap for the upper bound (n jobs); valid samples are
    # written compacted from index 0, and y/paths are saved for the valid count.
    X = np.lib.format.open_memmap(
        out_dir / "X.npy", mode="w+", dtype=np.float16, shape=(n, 2, N_MELS, T_FRAMES)
    )
    ys, label_names, paths = [], [], []

    try:
        from tqdm import tqdm

        progress = tqdm(total=n, unit="file")
    except ImportError:
        progress = None

    k, skipped = 0, 0
    with mp.Pool(processes=workers) as pool:
        for mel2, label, label_name, rel in pool.imap_unordered(_extract_one, jobs, chunksize=8):
            if mel2 is None:
                skipped += 1
            else:
                X[k] = mel2
                ys.append(label)
                label_names.append(label_name)
                paths.append(rel)
                k += 1
            if progress is not None:
                progress.update(1)
                progress.set_postfix(ok=k, skip=skipped)
    if progress is not None:
        progress.close()

    X.flush()
    if k == 0:
        log.error("No features extracted.")
        return 2
    # X.npy has n rows; only the first k are valid and align with y. train.py
    # indexes by len(y)=k, so the trailing rows are simply never read.
    np.save(out_dir / "y.npy", np.array(ys, dtype=np.int64))
    np.save(out_dir / "paths.npy", np.array(paths, dtype=object), allow_pickle=True)
    np.save(out_dir / "labels.npy", np.array(label_names, dtype=object), allow_pickle=True)
    with open(out_dir / "config.json", "w") as f:
        json.dump(
            dict(
                sample_rate=SAMPLE_RATE,
                segment_sec=SEGMENT_SEC,
                n_mels=N_MELS,
                n_fft=N_FFT,
                hop=HOP,
                channels=2,
                layout="mid_side",
                quant_bits=16,
                valid=k,
                allocated=n,
            ),
            f,
            indent=2,
        )
    log.info(
        f"Wrote {out_dir}/ : {k} valid samples (skipped {skipped}), "
        f"X allocated {X.nbytes/1024**3:.1f} GB float16"
    )
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input", default="dataset")
    p.add_argument("--output-dir", default="features_v4_stereo")
    p.add_argument("--workers", type=int, default=12)
    p.add_argument(
        "--limit-per-class",
        type=int,
        default=0,
        help="Cap authentic & transcoded jobs to N each (smoke test).",
    )
    args = p.parse_args()
    sys.exit(main(Path(args.input), Path(args.output_dir), args.workers, args.limit_per_class))
