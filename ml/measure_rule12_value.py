#!/usr/bin/env python3
"""Measure Rule 12's MARGINAL value over the 11 heuristic rules.

The question "is the ML rule a gadget or useful?" is only answerable by its
marginal contribution: on a labelled set, how many transcodes does Rule 12 catch
that the 11 heuristics MISS, and how many authentics does it wrongly flag that the
11 heuristics correctly PASS?

Method: run the full 12-rule pipeline once per file (FLACAnalyzer.analyze_file),
read the total score + verdict, parse Rule 12's point contribution from the reason
string, and derive the 11-rule counterfactual by subtraction — exact, because
Rule 12 runs last and only ADDS points (the heuristic short-circuits happen before
it, so when it fires the rest of the pipeline is identical).

For each file we get verdict_11 (heuristics only) and verdict_12 (with ML). Then:
  * VALUE  = transcodes that were AUTHENTIC under 11 rules but flagged under 12.
  * COST   = authentics that were AUTHENTIC under 11 rules but flagged under 12.
A rule is "useful" if VALUE clearly exceeds COST, especially on codecs where the
spectral cutoff is weak (high-bitrate CBR, VBR, AAC).

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/measure_rule12_value.py --per-bucket 24
"""

from __future__ import annotations

import argparse
import csv
import gc
import logging
import multiprocessing as mp
import random
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_r12val_tmp"
R12_RE = re.compile(r"R12:.*?\+(\d+)\s*pts")
BUCKETS = ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]
CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},
    {"name": "mp3_320", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "320k"]},
    {"name": "mp3_v0", "codec": "libmp3lame", "ext": "mp3", "args": ["-q:a", "0"]},
    {"name": "aac_256", "codec": "aac", "ext": "m4a", "args": ["-b:a", "256k"]},
]
# Optional codec filter via env (read at import so multiprocessing workers see it).
import os  # noqa: E402

_only = os.environ.get("R12_ONLY_CODEC")
if _only:
    CODECS = [c for c in CODECS if c["name"] == _only]


def bucket(hz: float) -> str:
    for e, n in [(4000, "<4k"), (7000, "4-7k"), (10000, "7-10k"), (14000, "10-14k")]:
        if hz < e:
            return n
    return ">=14k"


def _analyze(path: str) -> tuple[str, str] | None:
    """Return (verdict_11, verdict_12) for one file via the full pipeline."""
    from flac_detective.analysis.analyzer import FLACAnalyzer
    from flac_detective.analysis.new_scoring.verdict import determine_verdict

    try:
        res = FLACAnalyzer().analyze_file(Path(path))
    except Exception as e:  # noqa: BLE001
        log.debug(f"analyze fail {path}: {e}")
        return None
    if res.get("verdict") == "ERROR":
        return None
    score12 = int(res["score"])
    verdict12 = res["verdict"]
    m = R12_RE.search(res.get("reason", "") or "")
    r12 = int(m.group(1)) if m else 0
    score11 = max(0, score12 - r12)
    verdict11 = determine_verdict(score11)[0]
    return verdict11, verdict12


def _transcode(src: str, dst: Path, codec: dict) -> bool:
    tmp = dst.with_suffix(f".tmp.{codec['ext']}")
    # -vn drops any embedded cover art: FLACs often carry it as a video stream,
    # and the mp4/m4a muxer tries to re-encode it with libx264 (fails on odd
    # dimensions), corrupting AAC outputs. Audio only.
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
    r = _analyze(src)
    if r:
        rows.append((idx, "authentic", "authentic", bkt, r[0], r[1]))
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(src, dst, codec):
                r = _analyze(str(dst))
                if r:
                    rows.append((idx, "transcode", codec["name"], bkt, r[0], r[1]))
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
    rng = random.Random(42)
    chosen = []
    for b in BUCKETS:
        items = by.get(b, [])
        rng.shuffle(items)
        chosen += items[:per_bucket]
    jobs = list(enumerate(chosen))
    log.info(
        f"Measuring on {len(jobs)} authentics (stratified {per_bucket}/bucket) "
        f"× (1 + {len(CODECS)} transcodes). {workers} workers."
    )
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
        log.error("No results.")
        return 2

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "kind", "codec", "src_bucket", "verdict11", "verdict12"])
        w.writerows(out)

    flagged = lambda v: v != "AUTHENTIC"  # noqa: E731
    auth = [r for r in out if r[1] == "authentic"]
    trans = [r for r in out if r[1] == "transcode"]
    log.info("=" * 64)
    log.info(f"AUTHENTICS ({len(auth)}):")
    fp11 = sum(flagged(r[4]) for r in auth)
    fp12 = sum(flagged(r[5]) for r in auth)
    cost = sum((not flagged(r[4])) and flagged(r[5]) for r in auth)
    log.info(f"  flagged by 11 rules: {fp11} ({fp11/len(auth):.1%})")
    log.info(f"  flagged by 12 rules: {fp12} ({fp12/len(auth):.1%})")
    log.info(f"  >>> Rule 12 COST (authentic clean@11 -> flagged@12): {cost}")
    log.info("-" * 64)
    log.info(f"TRANSCODES ({len(trans)}):")
    d11 = sum(flagged(r[4]) for r in trans)
    d12 = sum(flagged(r[5]) for r in trans)
    value = sum((not flagged(r[4])) and flagged(r[5]) for r in trans)
    log.info(f"  caught by 11 rules: {d11} ({d11/len(trans):.1%})")
    log.info(f"  caught by 12 rules: {d12} ({d12/len(trans):.1%})")
    log.info(f"  >>> Rule 12 VALUE (transcode missed@11 -> caught@12): {value}")
    log.info("-" * 64)
    log.info("Rule 12 VALUE by codec (transcodes caught only thanks to R12):")
    for c in [c["name"] for c in CODECS]:
        ct = [r for r in trans if r[2] == c]
        if ct:
            v = sum((not flagged(r[4])) and flagged(r[5]) for r in ct)
            c11 = sum(flagged(r[4]) for r in ct)
            log.info(f"  {c:>8}: 11-caught {c11}/{len(ct)}  +R12 rescues {v}")
    log.info("=" * 64)
    log.info(
        f"NET: Rule 12 catches {value} more transcodes, at a cost of {cost} "
        f"new false positives on authentics."
    )
    log.info(f"Wrote {out_csv}")
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/rule12_value.csv")
    p.add_argument("--per-bucket", type=int, default=24)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    sys.exit(main(Path(args.csv), Path(args.out), args.per_bucket, args.workers))
