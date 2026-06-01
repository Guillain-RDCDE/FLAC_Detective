#!/usr/bin/env python3
"""Dump the raw 0-150 score distribution for authentics vs known transcodes, to
check whether the verdict thresholds (AUTHENTIC <=30, WARNING 31-60, SUSPICIOUS
61-85, FAKE_CERTAIN >=86) are well-calibrated — the WARNING band looked wide.

Runs the full pipeline (FLACAnalyzer.analyze_file) on a rolloff-stratified set of
authentics + their MP3/AAC transcodes and records (label, codec, src_bucket,
score, verdict). Analyse the percentiles afterwards to see where each class piles
up and whether the cut points should move.

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/score_distribution.py --per-bucket 24
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
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_scoredist_tmp"
BUCKETS = ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]
CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "mp3_320", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "320k"]},
]


def bucket(hz: float) -> str:
    for e, n in [(4000, "<4k"), (7000, "4-7k"), (10000, "7-10k"), (14000, "10-14k")]:
        if hz < e:
            return n
    return ">=14k"


def _score(path: str):
    from flac_detective.analysis.analyzer import FLACAnalyzer

    try:
        res = FLACAnalyzer().analyze_file(Path(path))
    except Exception as e:  # noqa: BLE001
        log.debug(f"fail {path}: {e}")
        return None
    if res.get("verdict") == "ERROR":
        return None
    return int(res["score"]), res["verdict"]


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
        "-sample_fmt",
        "s16",
        str(dst),
    ]
    ok = subprocess.run(dec, capture_output=True).returncode == 0
    tmp.unlink(missing_ok=True)
    return ok


def _process(job):
    idx, entry = job
    src = entry["path"]
    bkt = bucket(float(entry["rolloff_95_hz"]))
    rows = []
    s = _score(src)
    if s:
        rows.append((idx, "authentic", "authentic", bkt, s[0], s[1]))
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(src, dst, codec):
                s = _score(str(dst))
                if s:
                    rows.append((idx, "transcode", codec["name"], bkt, s[0], s[1]))
        finally:
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass
    return rows


def main(csv_path: Path, out_csv: Path, per_bucket: int, workers: int) -> int:
    allrows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    by = defaultdict(list)
    for r in allrows:
        by[bucket(float(r["rolloff_95_hz"]))].append(r)
    rng = random.Random(7)
    chosen = []
    for b in BUCKETS:
        items = by.get(b, [])
        rng.shuffle(items)
        chosen += items[:per_bucket]
    jobs = list(enumerate(chosen))
    log.info(f"Scoring {len(jobs)} authentics × (1 + {len(CODECS)} transcodes). {workers} workers.")
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from tqdm import tqdm

        prog = tqdm(total=len(jobs), unit="src")
    except ImportError:
        prog = None
    out = []
    with mp.Pool(workers) as pool:
        for rows in pool.imap_unordered(_process, jobs, chunksize=2):
            out.extend(rows)
            if prog:
                prog.update(1)
    if prog:
        prog.close()
    if not out:
        return 2
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "kind", "codec", "src_bucket", "score", "verdict"])
        w.writerows(out)
    log.info(f"Wrote {out_csv} ({len(out)} rows)")
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/score_distribution.csv")
    p.add_argument("--per-bucket", type=int, default=24)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.per_bucket, args.workers))
