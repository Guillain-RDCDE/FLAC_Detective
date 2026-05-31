#!/usr/bin/env python3
"""Extract 2-channel (mid+side) mel-spectrograms for a stereo-CNN feasibility
probe on band-limited material — the validation-scale test before committing a
Hetzner GPU retrain.

The question: can an end-to-end CNN on raw mid+side spectrograms beat the 0.68
ceiling that hand-crafted texture features hit on band-limited transcodes — and,
crucially, does the SIDE channel add anything over MID alone? The training script
trains both a 2-channel (mid+side) and a 1-channel (mid-only) model under
GroupKFold; if 2ch ≈ 1ch, the stereo bet is dead and no GPU retrain is warranted.

Saves ml/stereo_probe.npz: X (N,2,128,T) float32, y, groups (source idx), codec.
Channel 0 = mid mel, channel 1 = side mel, each per-channel normalised to [-1,1]
(matching the production mel normalisation). Band-limited (<7k) model-flagged
sources, paired authentic + mp3_128 (strong signal) + mp3_320 (hard ceiling).

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/stereo_probe_features.py --n 250
"""

from __future__ import annotations

import argparse
import csv
import gc
import logging
import multiprocessing as mp
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SR = 44100
SEG = 10.0
N_MELS, N_FFT, HOP = 128, 2048, 512
TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_stereo_tmp"

CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "mp3_320", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "320k"]},
]


def _mel2ch(path: str) -> np.ndarray | None:
    """Return a (2, N_MELS, T) mid+side mel-spec, each channel normalised to [-1,1]."""
    import librosa

    try:
        y, sr = librosa.load(path, sr=SR, mono=False, offset=0.0, duration=SEG)
    except Exception as e:  # noqa: BLE001
        log.debug(f"load fail {path}: {e}")
        return None
    if y.ndim == 1:
        mid = y
        side = np.zeros_like(y)
    else:
        mid = 0.5 * (y[0] + y[1])
        side = 0.5 * (y[0] - y[1])
    tgt = int(SR * SEG)
    chans = []
    for sig in (mid, side):
        sig = np.pad(sig, (0, tgt - len(sig))) if len(sig) < tgt else sig[:tgt]
        mel = librosa.feature.melspectrogram(
            y=sig, sr=sr, n_fft=N_FFT, hop_length=HOP, n_mels=N_MELS, fmax=sr // 2
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        mn, mx = mel_db.min(), mel_db.max()
        chans.append(2 * (mel_db - mn) / max(mx - mn, 1e-6) - 1.0)
    return np.stack(chans, axis=0)


def _transcode(src: str, dst: Path, codec: dict) -> bool:
    tmp = dst.with_suffix(f".tmp.{codec['ext']}")
    enc = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        src,
        "-c:a",
        codec["codec"],
        *codec["args"],
        str(tmp),
    ]
    if subprocess.run(enc, capture_output=True).returncode != 0:
        tmp.unlink(missing_ok=True)
        return False
    dec = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(tmp),
        "-c:a",
        "flac",
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    ok = subprocess.run(dec, capture_output=True).returncode == 0
    tmp.unlink(missing_ok=True)
    return ok


def _process(job):
    idx, entry = job
    out = []  # list of (mel(2,128,T), y, group, codec)

    def emit(label, y, path):
        mel = _mel2ch(path)
        if mel is not None:
            out.append((mel, y, idx, label))

    emit("authentic", 0, entry["path"])
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(entry["path"], dst, codec):
                emit(codec["name"], 1, str(dst))
        finally:
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass
    return out


def main(csv_path: Path, out_npz: Path, n: int, workers: int) -> int:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    band = [r for r in rows if float(r["rolloff_95_hz"]) < 7000 and r["is_fp"] == "1"]
    rng = random.Random(42)
    rng.shuffle(band)
    jobs = list(enumerate(band[:n]))
    log.info(
        f"Extracting 2ch mel for {len(jobs)} band-limited sources ×{len(CODECS)} codecs. "
        f"{workers} workers."
    )
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm

        prog = tqdm(total=len(jobs), unit="src")
    except ImportError:
        prog = None
    X, y, groups, codecs = [], [], [], []
    with mp.Pool(workers) as pool:
        for res in pool.imap_unordered(_process, jobs, chunksize=2):
            for mel, label, grp, cod in res:
                X.append(mel)
                y.append(label)
                groups.append(grp)
                codecs.append(cod)
            if prog:
                prog.update(1)
    if prog:
        prog.close()

    if not X:
        log.error("No features.")
        return 2
    X = np.stack(X).astype(np.float32)
    np.savez_compressed(
        out_npz,
        X=X,
        y=np.array(y, np.int64),
        groups=np.array(groups, np.int64),
        codec=np.array(codecs, dtype=object),
    )
    log.info(
        f"Wrote {out_npz}: X={X.shape} ({X.nbytes/1024**2:.0f} MB), "
        f"{int(np.sum(np.array(y) == 0))} authentic, {int(np.sum(np.array(y) == 1))} transcode"
    )
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/stereo_probe.npz")
    p.add_argument("--n", type=int, default=250)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.n, args.workers))
