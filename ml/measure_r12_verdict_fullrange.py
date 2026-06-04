#!/usr/bin/env python3
"""Resolve the tension: the v4 MODEL detects full-range AAC/Opus/Vorbis well
(measure_v4_per_codec.py: AUC 0.94-0.99, AAC-256 recall 82%), yet the older
measure_rule12_value.py found "Rule 12 barely moves AAC verdicts". Hypothesis:
the model fires (adds points) but the VERDICT doesn't escalate to actionable,
because the heuristic baseline on these codecs is low and R12 is capped at +30 —
not enough to cross SUSPICIOUS (55) on its own.

This captures, per file, score+verdict BOTH without R12 (11 heuristics, by
subtraction) and with it, then breaks the verdict transitions down by codec —
separately for FULL-RANGE (>=7k) vs band-limited. It also reports the authentic
COST at each verdict level, because any "let R12 escalate harder" lever pays for
itself in false SUSPICIOUS verdicts on the model's 6.7% authentic FP.

    OMP_NUM_THREADS=1 .venv/Scripts/python.exe ml/measure_r12_verdict_fullrange.py --per-bucket 30
"""

from __future__ import annotations

import argparse
import csv
import gc
import logging
import multiprocessing as mp
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TMP_DIR = Path(tempfile.gettempdir()) / "flac_detective_r12verdict_tmp"
R12_RE = re.compile(r"R12:.*?\+(\d+)\s*pts")
ALL_BUCKETS = ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]
FULLRANGE = {"7-10k", "10-14k", ">=14k"}
ACTIONABLE = {"SUSPICIOUS", "FAKE_CERTAIN"}

CODECS = [
    {"name": "mp3_128", "codec": "libmp3lame", "ext": "mp3", "args": ["-b:a", "128k"]},  # control
    {"name": "aac_256", "codec": "aac", "ext": "m4a", "args": ["-b:a", "256k"]},  # hard case
    {"name": "opus_128", "codec": "libopus", "ext": "opus", "args": ["-b:a", "128k"]},
    {"name": "vorbis_q5", "codec": "libvorbis", "ext": "ogg", "args": ["-q:a", "5"]},
]


def bucket(hz: float) -> str:
    for e, n in [(4000, "<4k"), (7000, "4-7k"), (10000, "7-10k"), (14000, "10-14k")]:
        if hz < e:
            return n
    return ">=14k"


_DEEP = os.environ.get("R12_DEEP") == "1"


def _analyze(path: str):
    """Return (score11, verdict11, score12, verdict12) for one file, or None."""
    from flac_detective.analysis.analyzer import FLACAnalyzer
    from flac_detective.analysis.new_scoring.verdict import determine_verdict

    try:
        res = FLACAnalyzer(deep=_DEEP).analyze_file(Path(path))
    except Exception as e:  # noqa: BLE001
        log.debug(f"analyze fail {path}: {e}")
        return None
    if res.get("verdict") == "ERROR":
        return None
    score12 = int(res["score"])
    verdict12 = res["verdict"]
    # Sum ALL R12 contributions: with the high-confidence WARNING floor, R12 can
    # emit two "+N pts" reasons (the CNN score and the floor bump). Subtracting only
    # the first would over-count the 11-rule counterfactual.
    r12 = sum(int(x) for x in R12_RE.findall(res.get("reason", "") or ""))
    score11 = max(0, score12 - r12)
    verdict11 = determine_verdict(score11)[0]
    return score11, verdict11, score12, verdict12


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


def _process(job):
    idx, entry = job
    src = entry["path"]
    bkt = bucket(float(entry["rolloff_95_hz"]))
    rows = []
    r = _analyze(src)
    if r:
        rows.append((idx, "authentic", bkt, *r))
    for codec in CODECS:
        dst = TMP_DIR / f"{idx}_{codec['name']}.flac"
        try:
            if _transcode(src, dst, codec):
                r = _analyze(str(dst))
                if r:
                    rows.append((idx, codec["name"], bkt, *r))
        finally:
            gc.collect()
            try:
                dst.unlink(missing_ok=True)
            except OSError:
                pass  # best-effort temp cleanup; ignore if locked or already gone
    return rows


def _select(csv_path: Path, per_bucket: int) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        allrows = list(csv.DictReader(f))
    by = defaultdict(list)
    for r in allrows:
        by[bucket(float(r["rolloff_95_hz"]))].append(r)
    rng = random.Random(42)
    chosen = []
    for b in ALL_BUCKETS:
        items = by.get(b, [])
        rng.shuffle(items)
        chosen += items[:per_bucket]
    return chosen


def _report(rows, regime_name, keep_fullrange):
    sel = [r for r in rows if (r[2] in FULLRANGE) == keep_fullrange]
    if not sel:
        return
    auth = [r for r in sel if r[1] == "authentic"]
    log.info("=" * 70)
    log.info(f"{regime_name}  (authentic n={len(auth)})")
    if auth:
        a_act11 = sum(r[4] in ACTIONABLE for r in auth)
        a_act12 = sum(r[6] in ACTIONABLE for r in auth)
        a_flag11 = sum(r[4] != "AUTHENTIC" for r in auth)
        a_flag12 = sum(r[6] != "AUTHENTIC" for r in auth)
        log.info(
            f"  AUTHENTIC cost: any-flag {a_flag11}->{a_flag12}, "
            f"actionable(SUSP+) {a_act11}->{a_act12}  (R12 adds "
            f"{a_act12 - a_act11} false SUSPICIOUS)"
        )
    log.info(f"  {'codec':>10} | {'11-rule verdicts':>34} | {'12-rule verdicts':>34}")
    order = ["AUTHENTIC", "WARNING", "SUSPICIOUS", "FAKE_CERTAIN"]
    for c in [x["name"] for x in CODECS]:
        ct = [r for r in sel if r[1] == c]
        if not ct:
            continue
        v11 = Counter(r[4] for r in ct)
        v12 = Counter(r[6] for r in ct)
        f11 = "/".join(f"{v11.get(v,0)}" for v in order)
        f12 = "/".join(f"{v12.get(v,0)}" for v in order)
        act11 = sum(r[4] in ACTIONABLE for r in ct)
        act12 = sum(r[6] in ACTIONABLE for r in ct)
        log.info(
            f"  {c:>10} | A/W/S/F {f11:>24} | A/W/S/F {f12:>24}  "
            f"actionable {act11}->{act12}/{len(ct)}"
        )


def main(csv_path: Path, out_csv: Path, per_bucket: int, workers: int) -> int:
    chosen = _select(csv_path, per_bucket)
    jobs = list(enumerate(chosen))
    log.info(
        f"Analyzing {len(jobs)} sources × (1 + {len(CODECS)} codecs), full 12-rule pipeline. "
        f"{workers} workers."
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
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    if not out:
        log.error("No results.")
        return 2

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "codec", "bucket", "score11", "verdict11", "score12", "verdict12"])
        w.writerows(out)

    log.info(
        "\nVerdict counts are A/W/S/F = AUTHENTIC/WARNING/SUSPICIOUS/FAKE_CERTAIN. "
        "Actionable = SUSPICIOUS+.\n"
    )
    _report(out, "FULL-RANGE (>=7 kHz) — the regime where the model is strong", True)
    _report(out, "BAND-LIMITED (<7 kHz) — gate abstains; for contrast", False)
    log.info("=" * 70)
    log.info(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--out", default="ml/r12_verdict_fullrange.csv")
    p.add_argument("--per-bucket", type=int, default=30)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    sys.exit(main(Path(a.csv), Path(a.out), a.per_bucket, a.workers))
