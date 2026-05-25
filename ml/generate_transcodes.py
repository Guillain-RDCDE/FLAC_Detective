#!/usr/bin/env python3
"""Generate transcoded "fake FLAC" copies of every authentic FLAC.

For each input authentic FLAC, this script produces 7 transcoded versions:

  mp3_128, mp3_192, mp3_256, mp3_320 — MP3 at four standard bitrates
  aac_192, aac_256                  — AAC at two bitrates
  opus_128                          — Opus 128 kbps

The transcoding flow for each:

  FLAC → encode to lossy (mp3/aac/opus) → decode back to PCM → re-encode FLAC

This produces a "fake FLAC" file: lossless container, but the audio
content has been through a lossy compressor. This is exactly what
FLAC Detective's CNN will learn to recognise.

Output layout (under args.output_root):

    transcoded/
        mp3_128/<same relative path>.flac
        mp3_192/<same relative path>.flac
        ...
        opus_128/<same relative path>.flac

Parallelism: defaults to one worker per CPU core, capped at 16 to leave
headroom for the running services. Idempotent: skips files whose output
already exists.

Usage on Hetzner:
    cd /root/flac-detective-ml
    venv/bin/python ml/generate_transcodes.py \
        --input  dataset/authentic \
        --output dataset/transcoded \
        --workers 16
"""

from __future__ import annotations

import argparse
import logging
import multiprocessing as mp
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Codec:
    name: str            # e.g. "mp3_192" — used as output subdir
    ffmpeg_codec: str    # e.g. "libmp3lame"
    ext: str             # intermediate file extension, e.g. "mp3"
    bitrate: str         # e.g. "192k"
    extra: tuple = ()    # extra ffmpeg flags


CODECS = (
    Codec("mp3_128",  "libmp3lame", "mp3",  "128k"),
    Codec("mp3_192",  "libmp3lame", "mp3",  "192k"),
    Codec("mp3_256",  "libmp3lame", "mp3",  "256k"),
    Codec("mp3_320",  "libmp3lame", "mp3",  "320k"),
    Codec("aac_192",  "aac",        "m4a",  "192k"),
    Codec("aac_256",  "aac",        "m4a",  "256k"),
    Codec("opus_128", "libopus",    "opus", "128k"),
)


def transcode_one(args: tuple[Path, Path, Path, Codec]) -> tuple[str, bool, str]:
    """Worker: do one (FLAC, codec) -> fake-FLAC transcode.

    Returns (relative-path-key, ok, message). Errors are non-fatal; the worker
    logs them and continues.
    """
    src, output_root, input_root, codec = args
    try:
        rel = src.relative_to(input_root)
    except ValueError:
        return (str(src), False, "src not under input_root")
    dst = output_root / codec.name / rel
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Idempotency: skip if already done and non-empty.
    if dst.is_file() and dst.stat().st_size > 1024:
        return (f"{codec.name}/{rel}", True, "skipped (exists)")

    tmp_lossy = dst.with_suffix(f".tmp.{codec.ext}")

    # Step 1: FLAC -> lossy
    enc = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(src),
        "-c:a", codec.ffmpeg_codec,
        "-b:a", codec.bitrate,
        *codec.extra,
        str(tmp_lossy),
    ]
    r1 = subprocess.run(enc, capture_output=True, text=True)
    if r1.returncode != 0:
        tmp_lossy.unlink(missing_ok=True)
        return (f"{codec.name}/{rel}", False, f"enc fail: {r1.stderr.strip()[:200]}")

    # Step 2: lossy -> FLAC ("fake FLAC")
    dec = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(tmp_lossy),
        "-c:a", "flac",
        str(dst),
    ]
    r2 = subprocess.run(dec, capture_output=True, text=True)
    tmp_lossy.unlink(missing_ok=True)
    if r2.returncode != 0:
        dst.unlink(missing_ok=True)
        return (f"{codec.name}/{rel}", False, f"dec fail: {r2.stderr.strip()[:200]}")

    return (f"{codec.name}/{rel}", True, "ok")


def collect_jobs(input_root: Path, output_root: Path) -> list:
    jobs = []
    flacs = sorted(input_root.rglob("*.flac"))
    log.info(f"Found {len(flacs)} authentic FLACs under {input_root}")
    for src in flacs:
        for codec in CODECS:
            jobs.append((src, output_root, input_root, codec))
    log.info(f"Planned {len(jobs)} transcoding jobs ({len(flacs)} files × {len(CODECS)} codecs)")
    return jobs


def main(input_root: Path, output_root: Path, workers: int) -> int:
    if shutil.which("ffmpeg") is None:
        log.error("ffmpeg not found on PATH. Install with: apt install ffmpeg")
        return 1
    if not input_root.is_dir():
        log.error(f"Input directory not found: {input_root}")
        return 1
    output_root.mkdir(parents=True, exist_ok=True)

    jobs = collect_jobs(input_root, output_root)

    log.info(f"Starting transcoding with {workers} workers...")
    ok = 0
    fail = 0
    skipped = 0
    try:
        from tqdm import tqdm
        progress = tqdm(total=len(jobs), unit="file")
    except ImportError:
        progress = None

    with mp.Pool(processes=workers) as pool:
        for key, success, msg in pool.imap_unordered(transcode_one, jobs, chunksize=4):
            if success:
                if msg == "skipped (exists)":
                    skipped += 1
                else:
                    ok += 1
            else:
                fail += 1
                log.warning(f"FAIL {key}: {msg}")
            if progress is not None:
                progress.update(1)
                progress.set_postfix(ok=ok, skip=skipped, fail=fail)
    if progress is not None:
        progress.close()

    log.info(f"Done. ok={ok}  skipped={skipped}  fail={fail}  total={len(jobs)}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--input",  default="dataset/authentic",
                   help="Root directory containing authentic FLACs")
    p.add_argument("--output", default="dataset/transcoded",
                   help="Root directory for transcoded outputs (subdirs per codec)")
    p.add_argument("--workers", type=int, default=min(16, mp.cpu_count()),
                   help="Number of parallel ffmpeg workers")
    args = p.parse_args()
    sys.exit(main(Path(args.input), Path(args.output), args.workers))
