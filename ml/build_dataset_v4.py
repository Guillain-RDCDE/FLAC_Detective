#!/usr/bin/env python3
"""Build a v4 training manifest, stratified by spectral rolloff.

v3 was trained on a sample that under-represented band-limited material, so the
model never learned to tell a *gradual* natural rolloff from a *brickwall*
transcode cliff — hence 57% false positives on rolloff<4k authentics (see
ml/analyze_false_positives.py). v4 fixes the data side: it joins every
certified-authentic FLAC with the rolloff already measured in
fp_analysis_v3.csv, then samples so the band-limited tail is properly present.

Strategies (--strategy):
  all       — every certified file, no rolloff balancing (just lifts v3's cap).
  balanced  — cap each rolloff bucket at --bucket-cap so the band-limited tail
              is over-represented relative to its natural frequency, forcing the
              model to confront the hard cases. Recommended once the abstention
              gate's verdict is known (it may reduce how aggressive this needs).

A per-label cap (--max-per-label) still prevents a single box-set dominating.

Output: a manifest identical in shape to build_dataset.py (so trim_for_upload.py
consumes it unchanged), plus a printed rolloff-bucket breakdown.

    .venv/Scripts/python.exe ml/build_dataset_v4.py \
        --strategy balanced --bucket-cap 1500 --max-per-label 40
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def bucket(hz: float) -> str:
    for edge, name in [(4000, "<4k"), (7000, "4-7k"), (10000, "7-10k"), (14000, "10-14k")]:
        if hz < edge:
            return name
    return ">=14k"


BUCKET_ORDER = ["<4k", "4-7k", "7-10k", "10-14k", ">=14k"]


def main(
    csv_path: Path,
    manifest_in: Path,
    out_path: Path,
    strategy: str,
    bucket_cap: int,
    max_per_label: int | None,
) -> int:
    # rolloff per path from the FP analysis
    rolloff = {
        r["path"]: float(r["rolloff_95_hz"])
        for r in csv.DictReader(open(csv_path, encoding="utf-8"))
    }
    log.info(f"Loaded rolloff for {len(rolloff)} files from {csv_path.name}")

    src = json.loads(manifest_in.read_text(encoding="utf-8"))
    entries = [e for e in src["files"] if e["path"] in rolloff]
    log.info(f"Joined {len(entries)}/{len(src['files'])} manifest entries with rolloff")

    rng = random.Random(42)

    # Optional per-label cap first (diversity), same spirit as build_dataset.py.
    if max_per_label is not None:
        by_label: dict[str, list[dict]] = defaultdict(list)
        for e in entries:
            by_label[e["top_label"]].append(e)
        capped: list[dict] = []
        for items in by_label.values():
            if len(items) > max_per_label:
                items = rng.sample(items, max_per_label)
            capped.extend(items)
        log.info(f"After per-label cap ({max_per_label}): {len(capped)} (from {len(entries)})")
        entries = capped

    # Rolloff bucketing.
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        by_bucket[bucket(rolloff[e["path"]])].append(e)

    if strategy == "balanced":
        selected: list[dict] = []
        for b in BUCKET_ORDER:
            items = by_bucket.get(b, [])
            if len(items) > bucket_cap:
                items = rng.sample(items, bucket_cap)
            selected.extend(items)
    elif strategy == "all":
        selected = entries
    else:
        log.error(f"Unknown strategy: {strategy}")
        return 1

    rng.shuffle(selected)

    # Report.
    log.info("-" * 50)
    log.info(f"Strategy '{strategy}': {len(selected)} files selected")
    log.info("Rolloff distribution (selected vs available):")
    sel_b = Counter(bucket(rolloff[e["path"]]) for e in selected)
    for b in BUCKET_ORDER:
        log.info(f"  {b:>7}: {sel_b.get(b, 0):5d}  (of {len(by_bucket.get(b, [])):5d})")

    out = {
        "root": src["root"],
        "count": len(selected),
        "strategy": strategy,
        "bucket_cap": bucket_cap if strategy == "balanced" else None,
        "max_per_label": max_per_label,
        "rolloff_buckets": dict(sel_b),
        "files": selected,
    }
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"\nWrote {out_path} ({len(selected)} files)")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--csv", default="ml/fp_analysis_v3.csv")
    p.add_argument("--manifest-in", default="ml/authentic_files.json")
    p.add_argument("--out", default="ml/authentic_sampled_v4.json")
    p.add_argument("--strategy", choices=["all", "balanced"], default="balanced")
    p.add_argument(
        "--bucket-cap",
        type=int,
        default=1500,
        help="Max files per rolloff bucket (balanced strategy).",
    )
    p.add_argument("--max-per-label", type=int, default=40)
    args = p.parse_args()
    sys.exit(
        main(
            Path(args.csv),
            Path(args.manifest_in),
            Path(args.out),
            args.strategy,
            args.bucket_cap,
            args.max_per_label,
        )
    )
