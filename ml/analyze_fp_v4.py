#!/usr/bin/env python3
"""Real-world false-positive audit of the v4 stereo model, head-to-head with v3.

Reuses the exact file list + rolloff from fp_analysis_v3.csv (which holds v3's
per-file p_transcoded), computes v4's p_transcoded with 2-channel mid+side
inference that reproduces the training extraction EXACTLY (16-bit quantise,
per-channel mel normalised to [-1,1]), and reports false-positive rate by rolloff
bucket for both models. This is the decisive test: does the stereo model fix the
band-limited blind spot on real authentic FLACs?

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/analyze_fp_v4.py --workers 4
"""

from __future__ import annotations

import argparse
import csv
import logging
import multiprocessing as mp
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SR, SEG, N_MELS, N_FFT, HOP = 44100, 10.0, 128, 2048, 512
THRESHOLD = 0.5
MODEL_PATH = Path(__file__).resolve().parent / "cnn_v4_stereo.ts.pt"
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        import torch

        torch.set_num_threads(1)
        _MODEL = torch.jit.load(str(MODEL_PATH), map_location="cpu")
        _MODEL.eval()
    return _MODEL


def _predict_v4(path: str) -> float | None:
    """v4 2-channel inference — matches extract_features_stereo + MelDataset norm."""
    import librosa
    import torch

    try:
        # Middle segment — MUST match training (extract_features_stereo) and the
        # production inference (_compute_mel). An earlier version used offset=0
        # (start), which mismatched both and skewed the audit.
        dur = librosa.get_duration(path=path)
        offset = max(0.0, (dur - SEG) / 2)
        y, sr = librosa.load(path, sr=SR, mono=False, offset=offset, duration=SEG)
    except Exception:  # noqa: BLE001
        return None
    if y.ndim == 1:
        mid, side = y, np.zeros_like(y)
    else:
        mid, side = 0.5 * (y[0] + y[1]), 0.5 * (y[0] - y[1])
    tgt = int(SR * SEG)
    chans = []
    for sig in (mid, side):
        if len(sig) < tgt * 0.5:
            return None
        sig = np.pad(sig, (0, tgt - len(sig))) if len(sig) < tgt else sig[:tgt]
        sig = np.round(sig * 32768.0) / 32768.0  # 16-bit quant (matches training)
        mel = librosa.feature.melspectrogram(
            y=sig, sr=sr, n_fft=N_FFT, hop_length=HOP, n_mels=N_MELS, fmax=sr // 2
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        mn, mx = mel_db.min(), mel_db.max()  # per-channel norm to [-1,1]
        chans.append(2 * (mel_db - mn) / max(mx - mn, 1e-6) - 1.0)
    x = torch.from_numpy(np.stack(chans, axis=0)[None].astype(np.float32))
    with torch.no_grad():
        p = torch.softmax(_get_model()(x), dim=1)[0, 1].item()
    return float(p)


def _job(row: dict) -> dict | None:
    p = _predict_v4(row["path"])
    if p is None:
        return None
    return {
        "rolloff": float(row["rolloff_95_hz"]),
        "p_v3": float(row["p_transcoded"]),
        "is_fp_v3": int(row["is_fp"]),
        "p_v4": round(p, 4),
        "is_fp_v4": int(p >= THRESHOLD),
    }


def bucket(hz: float) -> str:
    for e, n in [(4000, "<4k"), (7000, "4-7k"), (10000, "7-10k"), (14000, "10-14k")]:
        if hz < e:
            return n
    return ">=14k"


def main(csv_path: Path, out_csv: Path, workers: int, limit: int | None) -> int:
    if not MODEL_PATH.is_file():
        log.error(f"Model not found: {MODEL_PATH}")
        return 1
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    if limit:
        rows = rows[:limit]
    log.info(f"Auditing {len(rows)} authentic files with v4 stereo ({workers} workers)...")
    try:
        from tqdm import tqdm

        prog = tqdm(total=len(rows), unit="file")
    except ImportError:
        prog = None
    out = []
    with mp.Pool(workers) as pool:
        for r in pool.imap_unordered(_job, rows, chunksize=4):
            if r:
                out.append(r)
            if prog:
                prog.update(1)
                prog.set_postfix(fp_v4=sum(x["is_fp_v4"] for x in out))
    if prog:
        prog.close()
    if not out:
        return 2

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    n = len(out)
    fp3 = sum(r["is_fp_v3"] for r in out)
    fp4 = sum(r["is_fp_v4"] for r in out)
    log.info("=" * 60)
    log.info(f"Authentic files audited: {n}")
    log.info(f"v3 specificity: {1 - fp3/n:.1%}  ({fp3} FP)")
    log.info(f"v4 specificity: {1 - fp4/n:.1%}  ({fp4} FP)")
    log.info("-" * 60)
    log.info(f"{'rolloff':>8} | {'n':>5} | {'v3 FP%':>7} | {'v4 FP%':>7} | {'Δ':>6}")
    by = defaultdict(list)
    for r in out:
        by[bucket(r["rolloff"])].append(r)
    for b in ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]:
        it = by.get(b, [])
        if not it:
            continue
        v3 = sum(x["is_fp_v3"] for x in it) / len(it)
        v4 = sum(x["is_fp_v4"] for x in it) / len(it)
        log.info(f"{b:>8} | {len(it):>5} | {v3:>6.1%} | {v4:>6.1%} | {v4-v3:>+5.1%}")
    log.info("=" * 60)
    log.info(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/fp_analysis_v4.csv")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.workers, args.limit))
