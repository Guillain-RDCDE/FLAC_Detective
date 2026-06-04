#!/usr/bin/env python3
"""Phase 1 of the targeted R12 un-cap: calibrate the high-confidence operating
point. measure_r12_verdict_fullrange.py showed the v4 model detects full-range
AAC-256 / Vorbis (AUC 0.945) but the scoring caps R12 at +30 so those verdicts
never reach actionable. The fix is to let a HIGH-confidence R12 escalate — but
only at a p threshold where the authentic false-positive cost stays low.

This runs the exact production inference (ml_classifier._compute_mel + the
bundled model) on full-range authentics + their AAC-256/Vorbis transcodes, saves
the per-file p_transcoded, and prints the trade-off curve: for each candidate
threshold, the authentic FP rate vs the per-codec recall. The knee of that curve
is the operating point for the Phase-2 scoring change.

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/calibrate_r12_threshold.py --n 180
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

TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_calib_tmp"
BUCKETS = [("7-10k", 7000, 10000), ("10-14k", 10000, 14000), (">=14k", 14000, 1e9)]

# The two codecs the model detects but the capped scoring leaves unactionable.
CODECS = [
    {"name": "aac_256", "codec": "aac", "ext": "m4a", "args": ["-b:a", "256k"]},
    {"name": "vorbis_q5", "codec": "libvorbis", "ext": "ogg", "args": ["-q:a", "5"]},
]


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
    out = []
    r = _predict(entry["path"])
    if r is not None:
        out.append(("authentic", 0, idx, r[0], r[1]))
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(entry["path"], dst, codec):
                rr = _predict(str(dst))
                if rr is not None:
                    out.append((codec["name"], 1, idx, rr[0], rr[1]))
        finally:
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass  # best-effort temp cleanup; ignore if locked or already gone
    return out


def _select(csv_path: Path, n: int) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rng = random.Random(42)
    per = max(1, n // len(BUCKETS))
    picked: list[dict] = []
    for _name, lo, hi in BUCKETS:
        pool = [r for r in rows if lo <= float(r["rolloff_95_hz"]) < hi]
        rng.shuffle(pool)
        picked.extend(pool[:per])
    rng.shuffle(picked)
    return picked


def main(csv_path: Path, out_csv: Path, n: int, workers: int) -> int:
    sources = _select(csv_path, n)
    jobs = list(enumerate(sources))
    log.info(
        f"Calibration: {len(jobs)} full-range sources × (authentic + {len(CODECS)} codecs). "
        f"{workers} workers."
    )
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from tqdm import tqdm

        prog = tqdm(total=len(jobs), unit="src")
    except ImportError:
        prog = None
    recs = []
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

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["codec", "y", "idx", "p_transcoded", "rolloff"])
        w.writerows(recs)

    cod = np.array([r[0] for r in recs], dtype=object)
    p = np.array([r[3] for r in recs], dtype=float)
    auth_p = p[cod == "authentic"]

    log.info(f"\nCalibration curve (full-range, authentic n={len(auth_p)})")
    log.info("Authentic FP = fraction of authentics with p>threshold (the cost).")
    log.info("Codec recall = fraction of that codec's transcodes with p>threshold (the gain).\n")
    header = f"{'p>thr':>6} | {'auth FP':>8} |" + "".join(
        f" {c['name']+' rec':>13} |" for c in CODECS
    )
    log.info(header)
    for thr in [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95]:
        fp = (auth_p > thr).mean()
        cells = f"{thr:>6.2f} | {fp:>7.1%} |"
        for c in CODECS:
            cp = p[cod == c["name"]]
            cells += f" {(cp > thr).mean():>12.1%} |"
        log.info(cells)
    log.info(f"\nWrote {out_csv}")
    return 0


if __name__ == "__main__":
    pa = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    pa.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    pa.add_argument("--out", default="ml/r12_calibration.csv")
    pa.add_argument("--n", type=int, default=180)
    pa.add_argument("--workers", type=int, default=4)
    a = pa.parse_args()
    sys.exit(main(Path(a.csv), Path(a.out), a.n, a.workers))
