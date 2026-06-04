#!/usr/bin/env python3
"""Extract 2-channel (mid+side) mel-spectrograms for a stereo-CNN feasibility
probe on the codecs the tool is BLIND to — AAC / Opus / Vorbis at high bitrate.

The reasoning. The stereo side-channel insight that overturned the "band-limited
is a fundamental wall" conclusion (see ml/README.md, "The fifth attempt that
worked") was only ever tested against MP3 (stereo_probe_features.py covers
mp3_128 / mp3_320). But AAC also codes stereo aggressively (M/S per scalefactor
band, intensity stereo, PNS), and so do Opus and Vorbis. The "AAC is near-
transparent, ~6 % caught" verdict was reached with a MONO model (v3) and mono
hand-crafted features — the exact representation the stereo result proved is the
wrong microphone. So the open question, never run by the decisive method:

    does the SIDE channel (L-R) carry a transcode fingerprint for AAC/Opus/Vorbis,
    the way it does for MP3?

This is the cheap, falsifiable, no-GPU probe that answers it. The companion
aac_stereo_probe_train.py trains a compact CNN twice per codec under GroupKFold
by source — once on mid alone, once on mid+side — and reads off the delta. If
2ch ~= 1ch on AAC, the side channel is empty here and a GPU retrain won't help.

mp3_128 is kept as a CONTROL anchor: the harness must reproduce its known ~0.72
stereo AUC, or no AAC number is trustworthy (the project's recurring lesson:
verify the path before you trust the metric).

Sources: full-range (>=7 kHz rolloff) authentic FLACs, stratified across the
7-10 / 10-14 / >=14 kHz buckets. Full-range on purpose — AAC's transparency is
claimed for material WITH high-frequency content but no sharp MP3 cliff, so the
ONLY available tell there is the stereo coding. Band-limited material would
confound the codec fingerprint with the source's own roll-off.

Saves ml/aac_stereo_probe.npz: X (N,2,128,T) float32, y, groups (source idx),
codec. Channel 0 = mid mel, channel 1 = side mel, each per-channel normalised to
[-1,1] (matching the production mel normalisation).

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/aac_stereo_probe_features.py --n 240
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
TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_aac_stereo_tmp"

# mp3_128 = control anchor (must reproduce ~0.72 stereo). The rest = the tool's
# measured blind spot: high-bitrate AAC, Opus, Vorbis.
CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "aac_192", "codec": "aac", "ext": "m4a", "args": ["-b:a", "192k"]},
    {"name": "aac_256", "codec": "aac", "ext": "m4a", "args": ["-b:a", "256k"]},
    {"name": "opus_128", "codec": "libopus", "ext": "opus", "args": ["-b:a", "128k"]},
    {"name": "vorbis_q5", "codec": "libvorbis", "ext": "ogg", "args": ["-q:a", "5"]},
]

# Full-range strata (>=7 kHz rolloff).
BUCKETS = [("7-10k", 7000, 10000), ("10-14k", 10000, 14000), (">=14k", 14000, 1e9)]


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
    """Encode src to the lossy codec, then decode back to FLAC s16 @44.1k.

    -vn on the encode drops any embedded cover art, which otherwise makes the
    m4a/ogg muxer try to re-encode the picture as video and fail (the documented
    generate_transcodes.py bug). -ar 44100 on the decode normalises Opus (always
    internally 48 kHz) back to the common rate.
    """
    tmp = dst.with_suffix(f".tmp.{codec['ext']}")
    enc = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        src,
        "-vn",
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
        "-ar",
        "44100",
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
                pass  # best-effort temp cleanup; ignore if locked or already gone
    return out


def _select_sources(csv_path: Path, n: int) -> list[dict]:
    """Full-range authentic sources, stratified evenly across the 3 rolloff buckets."""
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rng = random.Random(42)
    per = max(1, n // len(BUCKETS))
    picked: list[dict] = []
    for name, lo, hi in BUCKETS:
        pool = [r for r in rows if lo <= float(r["rolloff_95_hz"]) < hi]
        rng.shuffle(pool)
        take = pool[:per]
        picked.extend(take)
        log.info(f"  bucket {name:>7}: pool={len(pool)}, took {len(take)}")
    rng.shuffle(picked)
    return picked


def main(csv_path: Path, out_npz: Path, n: int, workers: int) -> int:
    sources = _select_sources(csv_path, n)
    jobs = list(enumerate(sources))
    log.info(
        f"Extracting 2ch mel for {len(jobs)} full-range sources ×{len(CODECS)} codecs "
        f"(+authentic). {workers} workers."
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
    codec_arr = np.array(codecs, dtype=object)
    by_codec = {c: int((codec_arr == c).sum()) for c in ["authentic", *[c["name"] for c in CODECS]]}
    log.info(f"Wrote {out_npz}: X={X.shape} ({X.nbytes/1024**2:.0f} MB). Per-class: {by_codec}")
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/aac_stereo_probe.npz")
    p.add_argument("--n", type=int, default=240)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.n, args.workers))
