#!/usr/bin/env python3
"""Measure the SHIPPED v4 model's per-codec discrimination, to decide whether the
stereo signal the probe found (aac_stereo_probe_*) is already captured by v4 — or
whether a targeted retrain is warranted.

The probe (aac_stereo_probe_train.py) showed a FRESH compact CNN reaches stereo
AUC 0.83 (opus_128) / 0.80 (vorbis_q5) on full-range material, while AAC-256 stays
a wall (0.53). But v4 is ALREADY a stereo (mid+side) model trained on those codecs.
So the actionable question is not "can a stereo model do it" but "does the model we
SHIP already do it". This runs the exact production inference path
(ml_classifier._compute_mel: middle offset + 16-bit quant + per-channel norm, then
the bundled cnn_v4_stereo.ts.pt) on the same 180 full-range sources × 5 codecs, and
reports AUC / recall@0.5 per codec, directly comparable to the probe's numbers.

Two outcomes: (a) v4 ≈ probe ceiling on opus/vorbis → just fix the docs, no GPU;
(b) v4 well below the probe ceiling → real headroom, a targeted retrain is justified.

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/measure_v4_per_codec.py --n 180
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

TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_v4_measure_tmp"

CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "aac_192", "codec": "aac", "ext": "m4a", "args": ["-b:a", "192k"]},
    {"name": "aac_256", "codec": "aac", "ext": "m4a", "args": ["-b:a", "256k"]},
    {"name": "opus_128", "codec": "libopus", "ext": "opus", "args": ["-b:a", "128k"]},
    {"name": "vorbis_q5", "codec": "libvorbis", "ext": "ogg", "args": ["-q:a", "5"]},
]
BUCKETS = [("7-10k", 7000, 10000), ("10-14k", 10000, 14000), (">=14k", 14000, 1e9)]


def _transcode(src: str, dst: Path, codec: dict) -> bool:
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


def _predict(path: str):
    """Run the EXACT shipped v4 inference path; return (p_transcoded, rolloff) or None."""
    # Imported lazily so each spawned worker loads torch + the model once.
    from flac_detective.analysis.new_scoring.rules.ml_classifier import (
        _compute_mel,
        _load_model,
    )

    model = _load_model()
    if model is None:
        return None
    mel, rolloff = _compute_mel(Path(path))
    if mel is None:
        return None
    import torch

    with torch.no_grad():
        probs = torch.softmax(model(torch.from_numpy(mel)), dim=1)[0]
    return float(probs[1].item()), float(rolloff)


def _process(job):
    idx, entry = job
    out = []  # (codec, y, group, p, rolloff)
    res = _predict(entry["path"])
    if res is not None:
        out.append(("authentic", 0, idx, res[0], res[1]))
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(entry["path"], dst, codec):
                r = _predict(str(dst))
                if r is not None:
                    out.append((codec["name"], 1, idx, r[0], r[1]))
        finally:
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass  # best-effort temp cleanup; ignore if locked or already gone
    return out


def _select_sources(csv_path: Path, n: int) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rng = random.Random(42)
    per = max(1, n // len(BUCKETS))
    picked: list[dict] = []
    for name, lo, hi in BUCKETS:
        pool = [r for r in rows if lo <= float(r["rolloff_95_hz"]) < hi]
        rng.shuffle(pool)
        picked.extend(pool[:per])
    rng.shuffle(picked)
    return picked


def main(csv_path: Path, n: int, workers: int) -> int:
    from sklearn.metrics import roc_auc_score

    sources = _select_sources(csv_path, n)
    jobs = list(enumerate(sources))
    log.info(
        f"Measuring shipped v4 on {len(jobs)} sources ×{len(CODECS)} codecs. {workers} workers."
    )
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm

        prog = tqdm(total=len(jobs), unit="src")
    except ImportError:
        prog = None
    recs: list[tuple] = []
    with mp.Pool(workers) as pool:
        for res in pool.imap_unordered(_process, jobs, chunksize=2):
            recs.extend(res)
            if prog:
                prog.update(1)
    if prog:
        prog.close()
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    if not recs:
        log.error("No predictions.")
        return 2

    cod = np.array([r[0] for r in recs], dtype=object)
    p = np.array([r[3] for r in recs], dtype=float)
    roll = np.array([r[4] for r in recs], dtype=float)
    auth_p = p[cod == "authentic"]

    log.info("\nShipped v4 per-codec discrimination (full-range >=7k sources)")
    log.info("Probe stereo ceilings: opus_128 0.83, vorbis_q5 0.80, aac_256 0.53, aac_192 0.87\n")
    log.info(f"{'codec':>10} | {'v4 AUC':>7} | {'recall@.5':>9} | {'gate-abstain%':>13} | {'n':>4}")
    log.info(
        f"{'authentic':>10} | {'—':>7} | {'FP ' + format((auth_p > 0.5).mean(), '.1%'):>9} | "
        f"{format((roll[cod=='authentic'] < 7000).mean(), '.0%'):>13} | {len(auth_p):>4}"
    )
    for c in [x["name"] for x in CODECS]:
        m = cod == c
        if m.sum() == 0:
            continue
        cp = p[m]
        y = np.r_[np.zeros(len(auth_p)), np.ones(len(cp))]
        score = np.r_[auth_p, cp]
        auc = roc_auc_score(y, score) if len(set(y)) == 2 else float("nan")
        recall = (cp > 0.5).mean()
        gate = (roll[m] < 7000).mean()
        log.info(f"{c:>10} | {auc:>7.3f} | {recall:>9.1%} | {gate:>13.0%} | {m.sum():>4}")
    return 0


if __name__ == "__main__":
    pa = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    pa.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    pa.add_argument("--n", type=int, default=180)
    pa.add_argument("--workers", type=int, default=4)
    a = pa.parse_args()
    sys.exit(main(Path(a.csv), a.n, a.workers))
