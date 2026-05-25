#!/usr/bin/env python3
"""Build a manifest of certified-authentic FLAC files from a local music library.

Authentication evidence accepted (in priority order):

  1. EAC log         (Exact Audio Copy) — gold standard CD ripping (Windows)
  2. XLD log         (X Lossless Decoder) — gold standard CD ripping (Mac)
  3. CUERipper log   (open-source CD ripper with AccurateRip)
  4. Audiochecker    — third-party verifier; we only accept tracks marked
                       "CDDA (100%)" in the log (track-by-track filtering)

Strategy:

  * For EAC / XLD / CUERipper: assume all .flac files in the log's directory
    (and any sub-directory, to handle multi-disc albums in CD01/, CD02/) are
    authentic. The ripper would have failed before producing a log otherwise.

  * For Audiochecker: parse the log line by line and only retain .flac entries
    whose status is "CDDA (100%)". Tracks marked as partial / mixed / MPEG
    are skipped.

  * De-duplicate: same .flac can be referenced by multiple logs (e.g. an EAC
    rip that also ran through Audiochecker). Keep one entry per path.

Output: a JSON manifest with the full list of authenticated file paths plus
per-source and per-top-folder breakdowns, ready for upload to a training
server.

Usage:
    python ml/build_dataset.py --root D:/FLAC --output ml/authentic_files.json
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# Signatures detected in the first ~2 KB of a .log file.
RIPPER_SIGNATURES = [
    ("EAC",         ("Exact Audio Copy", "EAC extraction logfile")),
    ("XLD",         ("X Lossless Decoder", "XLD extraction logfile")),
    ("CUERipper",   ("CUERipper",)),
    ("Audiochecker", ("AUDIOCHECKER",)),
]

# Audiochecker log line pattern. Example line:
#   "5 -=- 05 - Track Name.flac -=- CDDA (100%)"
AUDIOCHECKER_LINE = re.compile(
    r"\d+\s*-=-\s*(?P<file>[^\r\n]+\.(?:flac|FLAC))\s*-=-\s*(?P<status>[^\r\n]+)"
)


def detect_ripper(log_path: Path) -> Optional[str]:
    """Return the ripper name based on the log header, or None if unknown."""
    try:
        with open(log_path, "rb") as f:
            head_bytes = f.read(2048)
    except OSError:
        return None
    # Logs can be ANSI, UTF-8, or UTF-16. Decode permissively.
    head = head_bytes.decode("utf-8", errors="replace")
    if "\x00" in head[:200]:
        # Heuristic: UTF-16-encoded log, decode accordingly.
        head = head_bytes.decode("utf-16", errors="replace")

    for ripper, sigs in RIPPER_SIGNATURES:
        if any(sig in head for sig in sigs):
            return ripper
    return None


def parse_audiochecker_tracks(log_path: Path) -> list[tuple[str, str]]:
    """Return [(filename, status), ...] for FLAC entries in an audiochecker log."""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return []
    return [(m.group("file").strip(), m.group("status").strip())
            for m in AUDIOCHECKER_LINE.finditer(content)]


def top_label(log_path: Path, root: Path) -> str:
    """Use the first two path components under `root` as the diversity label.

    Example: D:/FLAC/External/Analog Africa/Album/foo.log -> "External/Analog Africa"
    """
    try:
        rel = log_path.relative_to(root)
    except ValueError:
        return "unknown"
    parts = rel.parts
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]


def collect_from_log(log_path: Path, ripper: str, root: Path) -> list[dict]:
    """Return a list of authentic FLAC entries derived from a single log."""
    label = top_label(log_path, root)
    entries: list[dict] = []

    if ripper == "Audiochecker":
        for fname, status in parse_audiochecker_tracks(log_path):
            if "CDDA (100%)" not in status:
                continue
            flac = (log_path.parent / fname)
            if flac.is_file():
                entries.append({
                    "path": str(flac),
                    "source": "audiochecker_cdda100",
                    "ripper": ripper,
                    "top_label": label,
                })
        return entries

    # EAC / XLD / CUERipper: trust the entire directory tree below the log.
    # rglob to catch CD01/, CD02/, etc.
    for flac in log_path.parent.rglob("*.flac"):
        if flac.is_file():
            entries.append({
                "path": str(flac),
                "source": ripper.lower(),
                "ripper": ripper,
                "top_label": label,
            })
    return entries


def main(root_dir: str, output_path: str, max_per_label: Optional[int]) -> None:
    root = Path(root_dir).resolve()
    log.info(f"Scanning {root} for *.log files (this may take a few minutes)...")

    logs = list(root.rglob("*.log"))
    log.info(f"Found {len(logs)} log files")

    all_entries: list[dict] = []
    ripper_counter: Counter[str] = Counter()
    unknown_logs = 0

    for i, log_path in enumerate(logs, start=1):
        if i % 100 == 0:
            log.info(f"  processed {i}/{len(logs)} logs...")
        ripper = detect_ripper(log_path)
        if not ripper:
            unknown_logs += 1
            continue
        ripper_counter[ripper] += 1
        all_entries.extend(collect_from_log(log_path, ripper, root))

    log.info(f"Logs by ripper: {dict(ripper_counter)}")
    log.info(f"Skipped (unrecognized): {unknown_logs}")
    log.info(f"Raw entries before dedup: {len(all_entries)}")

    # Deduplicate by path. If a file is referenced by both an EAC log and an
    # audiochecker log, prefer the stronger evidence (EAC > XLD > CUERipper > AC).
    rank = {"EAC": 0, "XLD": 1, "CUERipper": 2, "Audiochecker": 3}
    best: dict[str, dict] = {}
    for entry in all_entries:
        path = entry["path"]
        if path not in best or rank[entry["ripper"]] < rank[best[path]["ripper"]]:
            best[path] = entry
    deduped = list(best.values())
    log.info(f"After dedup: {len(deduped)} unique authentic FLAC files")

    # Diversity cap per top-label so a single huge box-set does not dominate
    # the dataset. When max_per_label is None, keep everything.
    label_stats: Counter[str] = Counter(e["top_label"] for e in deduped)
    if max_per_label is not None:
        log.info(f"Applying diversity cap: {max_per_label} files per top-label")
        random.seed(42)
        by_label: dict[str, list[dict]] = {}
        for e in deduped:
            by_label.setdefault(e["top_label"], []).append(e)
        sampled: list[dict] = []
        for label, items in by_label.items():
            if len(items) > max_per_label:
                items = random.sample(items, max_per_label)
            sampled.extend(items)
        deduped = sampled
        log.info(f"After diversity cap: {len(deduped)} files")

    # Source breakdown after dedup & cap
    source_after = Counter(e["source"] for e in deduped)

    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "root": str(root),
        "count": len(deduped),
        "ripper_logs_found": dict(ripper_counter),
        "source_breakdown_after_dedup_and_cap": dict(source_after),
        "top_20_labels": dict(label_stats.most_common(20)),
        "files": deduped,
    }
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    log.info(f"\nManifest written to {output_p}")
    log.info(f"Total file size will be approximately: {len(deduped) * 30 / 1024:.1f} GB at ~30 MB/track")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default="D:/FLAC",
                        help="Root of the music library (default: D:/FLAC)")
    parser.add_argument("--output", default="ml/authentic_files.json",
                        help="Output JSON manifest path")
    parser.add_argument("--max-per-label", type=int, default=None,
                        help="Cap N files per top-label for diversity (default: no cap)")
    args = parser.parse_args()
    sys.exit(main(args.root, args.output, args.max_per_label))
