#!/usr/bin/env python3
"""Decisive confound control for measure_v4_per_codec.py.

That script found the shipped v4 model flags AAC-256 at AUC 0.945 on full-range
material — far above the docs' "near-undetectable" and above the small probe's
0.53. Before believing it, rule out the alternative explanation: v4 is keying on
a benign ffmpeg-pipeline artefact (resample/dither/re-encode), not the lossy
codec. So we run the EXACT same machinery but the "transcode" is a LOSSLESS FLAC
round-trip through ffmpeg — same container/resample ops, NO lossy step.

Read the verdict:
  * AUC ~= 0.5, recall ~= the authentic FP rate -> v4 does NOT react to the
    ffmpeg pipeline; the per-codec detections are real (the codec, not the tool).
  * AUC high / recall high -> CONFOUND: v4 detects "went through ffmpeg", and the
    per-codec AUCs are inflated. Everything downstream must be re-examined.

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/measure_v4_passthrough_control.py --n 60
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

TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_v4_ctrl_tmp"
BUCKETS = [("7-10k", 7000, 10000), ("10-14k", 10000, 14000), (">=14k", 14000, 1e9)]


def _passthrough(src: str, dst: Path) -> bool:
    """Lossless FLAC round-trip through ffmpeg — the SAME container/resample/s16
    ops the real transcodes go through, but with no lossy codec in the middle."""
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        src,
        "-vn",
        "-c:a",
        "flac",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    return subprocess.run(cmd, capture_output=True).returncode == 0


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
    res = _predict(entry["path"])
    if res is not None:
        out.append(("authentic", 0, idx, res[0], res[1]))
    dst = TMP_DIR / f"{idx}_passthrough.flac"
    try:
        if _passthrough(entry["path"], dst):
            r = _predict(str(dst))
            if r is not None:
                out.append(("flac_passthrough", 1, idx, r[0], r[1]))
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
        f"Passthrough control: {len(jobs)} sources, lossless FLAC round-trip. {workers} workers."
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

    cod = np.array([r[0] for r in recs], dtype=object)
    p = np.array([r[3] for r in recs], dtype=float)
    auth_p = p[cod == "authentic"]
    pass_p = p[cod == "flac_passthrough"]
    y = np.r_[np.zeros(len(auth_p)), np.ones(len(pass_p))]
    score = np.r_[auth_p, pass_p]
    auc = roc_auc_score(y, score) if len(set(y)) == 2 else float("nan")

    log.info("\nPassthrough confound control (lossless FLAC round-trip via ffmpeg)")
    log.info(
        f"  authentic    : n={len(auth_p)}, FP@.5 = {(auth_p>0.5).mean():.1%}, mean p = {auth_p.mean():.3f}"
    )
    log.info(
        f"  passthrough  : n={len(pass_p)}, flag@.5 = {(pass_p>0.5).mean():.1%}, mean p = {pass_p.mean():.3f}"
    )
    log.info(f"  AUC(authentic vs passthrough) = {auc:.3f}")
    if auc < 0.6:
        log.info(
            "  VERDICT: no pipeline confound — v4 ignores the lossless round-trip. Per-codec AUCs are real."
        )
    else:
        log.info(
            "  VERDICT: CONFOUND — v4 reacts to the ffmpeg pipeline itself. Re-examine the per-codec numbers."
        )
    return 0


if __name__ == "__main__":
    pa = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    pa.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    pa.add_argument("--n", type=int, default=60)
    pa.add_argument("--workers", type=int, default=4)
    a = pa.parse_args()
    sys.exit(main(Path(a.csv), a.n, a.workers))
