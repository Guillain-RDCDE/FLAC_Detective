#!/usr/bin/env python3
"""Download genuine, freely-distributable lossless FLACs for a WILD specificity test.

Source: the Internet Archive Live Music Archive (collection ``etree``) — taper
recordings explicitly licensed for free distribution, in lossless FLAC. These are
REAL authentic files from *outside* the training corpus, in genres/mastering the
model never saw — the honest test of "does it false-flag real lossless music in
the wild?". Caps total files and per-file size to stay polite and bounded.

After downloading, score them with the full pipeline to read off specificity::

    python ml/fetch_wild_authentic.py --out wild_authentic
    flac-detective wild_authentic --deep --format csv -o wild.csv   # verdict per file

Every file *should* read AUTHENTIC; anything else is a false positive. (A 2026-06-26
run of 45 files scored 39 AUTHENTIC / 5 WARNING / 1 SUSPICIOUS / 0 FAKE_CERTAIN —
86.7 %, on deliberately adversarial audience recordings; see this README.)
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

_UA = {"User-Agent": "flac-detective-research/1.0 (specificity test)"}


def _get(url: str, timeout: int = 60) -> bytes:
    """HTTP GET with the research User-Agent."""
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _search(rows: int) -> list:
    """Return identifiers of etree FLAC items, most-downloaded first.

    Every URL param is encoded — urllib is stricter than a shell ``curl`` and
    rejects a raw space or ``[]`` bracket in the URL.
    """
    params = [
        ("q", "collection:etree AND format:(Flac)"),
        ("fl[]", "identifier"),
        ("rows", str(rows)),
        ("page", "1"),
        ("output", "json"),
        ("sort[]", "downloads desc"),
    ]
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params)
    data = json.loads(_get(url))
    return [d["identifier"] for d in data["response"]["docs"]]


def main() -> None:
    """Download a bounded sample of wild authentic FLACs."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("wild_authentic"), help="Output directory")
    ap.add_argument("--max-files", type=int, default=45, help="Total files to fetch")
    ap.add_argument("--max-per-item", type=int, default=3, help="Files per archive item")
    ap.add_argument(
        "--max-mb", type=int, default=70, help="Skip files larger than this (whole-show dumps)"
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    max_bytes = args.max_mb * 1024 * 1024

    ids = _search(rows=max(60, args.max_files * 2))
    print(f"found {len(ids)} candidate etree items", flush=True)
    got = 0
    for ident in ids:
        if got >= args.max_files:
            break
        try:
            meta = json.loads(_get(f"https://archive.org/metadata/{ident}"))
        except Exception as e:
            print(f"  meta fail {ident}: {e}", flush=True)
            continue
        flacs = [
            f
            for f in meta.get("files", [])
            if str(f.get("format", "")).lower() == "flac"
            and f.get("size")
            and int(f["size"]) < max_bytes
        ]
        per = 0
        for f in flacs:
            if got >= args.max_files or per >= args.max_per_item:
                break
            name = f["name"]
            dst = args.out / f"{ident}__{Path(name).name}"
            if dst.exists():
                continue
            url = f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}"
            try:
                blob = _get(url, timeout=180)
                dst.write_bytes(blob)
                got += 1
                per += 1
                print(f"  [{got}/{args.max_files}] {dst.name} ({len(blob) // 1024} KB)", flush=True)
            except Exception as e:
                print(f"  dl fail {name}: {e}", flush=True)
            time.sleep(0.5)  # be polite to the archive
    print(f"DOWNLOADED {got} wild FLACs -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
