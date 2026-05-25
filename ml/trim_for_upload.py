#!/usr/bin/env python3
"""Trim each authentic FLAC to a 30-second clip from the middle.

The training pipeline only ever looks at 10 seconds of each file
(``extract_features.py`` -- see SEGMENT_SEC). Uploading entire albums to the
training server wastes hours of bandwidth. This script:

  * reads ``ml/authentic_sampled.json`` (the dataset manifest)
  * for each source FLAC, extracts 30 seconds (offset 30s into the file)
  * re-encodes with FLAC compression_level 8 (maximum)
  * writes to ``ml/trimmed/<relative path>`` preserving the directory tree

Result: ~3-4 GB to upload instead of ~21 GB.

Run from the project root:
    python ml/trim_for_upload.py --workers 16
"""

from __future__ import annotations

import argparse
import json
import logging
import multiprocessing as mp
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _trim_one(args: tuple[Path, Path, Path]) -> tuple[str, bool, str]:
    """ffmpeg-trim one file. Returns (path, ok, message)."""
    src, src_root, dst_root = args
    try:
        rel = src.relative_to(src_root)
    except ValueError:
        return (str(src), False, "src not under src_root")
    dst = dst_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Idempotency: skip if output already exists and is non-empty.
    if dst.is_file() and dst.stat().st_size > 1024:
        return (str(rel), True, "skipped (exists)")

    # Take 30 s starting 30 s into the file. ffmpeg returns whatever it has if
    # the file is shorter; we accept that — short tracks (intros, interludes)
    # are rare in the dataset.
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", "30",
        "-i", str(src),
        "-t", "30",
        "-c:a", "flac",
        "-compression_level", "8",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # Maybe the file is shorter than 30s — retry without -ss to capture whatever exists
        dst.unlink(missing_ok=True)
        cmd_short = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src),
            "-t", "30",
            "-c:a", "flac",
            "-compression_level", "8",
            str(dst),
        ]
        r2 = subprocess.run(cmd_short, capture_output=True, text=True)
        if r2.returncode != 0:
            dst.unlink(missing_ok=True)
            return (str(rel), False, f"both attempts failed: {r2.stderr.strip()[:160]}")

    if not dst.is_file() or dst.stat().st_size < 1024:
        return (str(rel), False, "output empty or missing")
    return (str(rel), True, "ok")


def main(manifest_path: Path, source_root: Path, output_root: Path,
         workers: int, clean: bool) -> int:
    if shutil.which("ffmpeg") is None:
        log.error("ffmpeg not found on PATH")
        return 1
    if clean and output_root.exists():
        log.info(f"Cleaning {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    jobs = []
    for entry in manifest["files"]:
        p = Path(entry["path"])
        if p.is_file():
            jobs.append((p, source_root, output_root))
    log.info(f"Found {len(jobs)} files to trim (workers={workers})")
    if not jobs:
        log.error("No input files.")
        return 1

    try:
        from tqdm import tqdm
        progress = tqdm(total=len(jobs), unit="file")
    except ImportError:
        progress = None

    ok = fail = skipped = 0
    with mp.Pool(processes=workers) as pool:
        for rel, success, msg in pool.imap_unordered(_trim_one, jobs, chunksize=4):
            if success:
                if msg == "skipped (exists)":
                    skipped += 1
                else:
                    ok += 1
            else:
                fail += 1
                log.warning(f"FAIL {rel}: {msg}")
            if progress is not None:
                progress.update(1)
                progress.set_postfix(ok=ok, skip=skipped, fail=fail)
    if progress is not None:
        progress.close()

    # Final size report
    total = 0
    count = 0
    for f in output_root.rglob("*.flac"):
        total += f.stat().st_size
        count += 1
    log.info(f"Trimmed dataset: {count} files, {total/1024**3:.2f} GB at {output_root}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--manifest", default="ml/authentic_sampled.json")
    p.add_argument("--source-root", default="D:/FLAC")
    p.add_argument("--output", default="ml/trimmed")
    p.add_argument("--workers", type=int, default=min(16, mp.cpu_count()))
    p.add_argument("--clean", action="store_true", help="Delete output dir first")
    args = p.parse_args()
    sys.exit(main(Path(args.manifest), Path(args.source_root),
                  Path(args.output), args.workers, args.clean))
