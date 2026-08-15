#!/usr/bin/env python3
"""Build the frozen corpus used by ml/rule_audit.py to measure each rule alone.

Why a dedicated corpus rather than reusing ml/build_dataset.py's: the rule audit
asks a different question. The CNN datasets were built to *train* — maximum
volume, whatever the codec mix. Here we need to *measure a rule's discriminative
power*, which requires

  1. genuine files that are certifiably genuine (EAC/XLD/Audiochecker ripper log
     next to them — ml/authentic_files.json records which),
  2. one source per album, so 80 "independent" observations really are 80 and not
     8 albums seen 10 times (the independent-n point Provir's benchmark makes),
  3. a codec grid weighted toward the HIGH-BITRATE end, because that is where the
     current arsenal is measured to fail (ml/README.md: mp3_320 → AUC 0.53).

Layout produced under ``--out``::

    authentic/<slug>.flac              one 60 s excerpt per source album
    fake/<codec>/<slug>.flac           the same excerpt, round-tripped through <codec>
    manifest.json                      sha256 + provenance for every file

Excerpts, not whole tracks: 60 s from the middle of the track, which comfortably
contains the 30 s the pipeline analyses by default while keeping the corpus (and
the scoring pass over it) bounded. This is a deliberate limitation — it prices
the same "constructed transcode" threat model Provir's benchmark does, and no
more. Wild validation is ml/wild_audit.py's job, not this file's.

Usage::

    python ml/build_audit_corpus.py --out C:/Users/loutr/audit_corpus --n 80
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import multiprocessing as mp
import random
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EXCERPT_SEC = 60.0
# Deterministic sampling: the corpus must be reproducible from the manifest alone.
SEED = 20260814


@dataclass(frozen=True)
class Codec:
    """One lossy encoder configuration to round-trip a source through."""

    name: str
    encoder: str
    ext: str
    args: Tuple[str, ...]


# Grid rationale — this deliberately over-samples the high-bitrate end.
#
# Available locally: libmp3lame, ffmpeg native aac (KBD α=4 long windows),
# aac_mf (MediaFoundation — a DIFFERENT AAC implementation, so it tests whether
# a detector learned "AAC" or learned "this one encoder"), libopus, libvorbis.
#
# NOT available in this ffmpeg build, and therefore absent from every number this
# corpus produces: libfdk_aac, qaac/afconvert (Apple constrained-VBR), mpcenc.
# Provir's benchmark has fdk_vbr5 and mpc_q10 rows; we cannot reproduce those.
CODECS: Tuple[Codec, ...] = (
    # MP3 — where FD already converts. Kept as the control group: a rule that
    # cannot separate here is dead beyond argument.
    Codec("mp3_192", "libmp3lame", "mp3", ("-b:a", "192k")),
    Codec("mp3_320", "libmp3lame", "mp3", ("-b:a", "320k")),
    Codec("mp3_V0", "libmp3lame", "mp3", ("-q:a", "0")),
    # AAC — the measured blind spot. 128k is the easy end, 320k the hard one.
    Codec("aac_ff128", "aac", "m4a", ("-b:a", "128k")),
    Codec("aac_ff256", "aac", "m4a", ("-b:a", "256k")),
    Codec("aac_ff320", "aac", "m4a", ("-b:a", "320k")),
    # Same bitrate as aac_ff256, different encoder. Any detector that scores these
    # two very differently has learned an encoder, not a codec.
    Codec("aacmf_256", "aac_mf", "m4a", ("-b:a", "256k")),
    # Opus / Vorbis — non-MDCT-identical filterbanks; the generalisation check.
    Codec("opus_256", "libopus", "opus", ("-b:a", "256k")),
    Codec("vorbis_q8", "libvorbis", "ogg", ("-q:a", "8")),
)


def sha256(path: Path) -> str:
    """Return the SHA-256 of ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(cmd: List[str]) -> bool:
    """Run ``cmd`` silently; return True on success."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if r.returncode != 0:
            log.debug(
                "ffmpeg failed: %s\n%s", " ".join(cmd), r.stderr.decode(errors="replace")[-400:]
            )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as exc:
        log.debug("ffmpeg error: %s", exc)
        return False


def _slug(path: Path, index: int) -> str:
    """Build a filesystem-safe, collision-free name for a source track."""
    stem = re.sub(r"[^A-Za-z0-9]+", "-", path.stem).strip("-")[:48] or "track"
    return f"{index:03d}-{stem}"


def pick_sources_from_dir(source_dir: Path, n: int) -> List[Dict]:
    """Select ``n`` sources from a directory of freely-redistributable FLACs.

    For the exchange corpus. The certified-library path below cannot be used for
    anything that leaves this machine: those are commercial CD rips, and freezing
    a corpus in sha256 does not make it distributable. Internet Archive ``etree``
    material is explicitly licensed for redistribution, so transcodes of it are
    too — which is what makes a blind cross-scoring exchange with another author
    legally possible at all.

    One file per archive item, for the same reason as one track per album: two
    tracks off the same concert share a capture chain and are not two
    observations.
    """
    by_item: Dict[str, List[Path]] = {}
    for f in sorted(source_dir.glob("*.flac")):
        # ml/fetch_wild_authentic.py names files "<item-identifier>__<track>.flac".
        item = f.name.split("__", 1)[0]
        by_item.setdefault(item, []).append(f)

    rng = random.Random(SEED)
    items = sorted(by_item)
    rng.shuffle(items)

    picked: List[Dict] = []
    for item in items:
        if len(picked) >= n:
            break
        f = rng.choice(by_item[item])
        picked.append({"path": str(f), "ripper": None, "item": item})
    return picked


def pick_sources(manifest_json: Path, n: int) -> List[Dict]:
    """Select ``n`` certified-authentic sources, at most one per album.

    One-per-album is the point: two tracks off the same CD share mastering,
    loudness and rolloff, so counting them as two observations inflates every
    confidence interval downstream.
    """
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    files = data["files"]
    by_album: Dict[str, List[Dict]] = {}
    for entry in files:
        album = str(Path(entry["path"]).parent)
        by_album.setdefault(album, []).append(entry)

    rng = random.Random(SEED)
    albums = sorted(by_album)
    rng.shuffle(albums)

    picked: List[Dict] = []
    for album in albums:
        if len(picked) >= n:
            break
        entry = rng.choice(by_album[album])
        if Path(entry["path"]).exists():
            picked.append(entry)
    return picked


def make_excerpt(src: Path, dst: Path) -> bool:
    """Write a 60 s FLAC excerpt from the middle of ``src`` to ``dst``.

    ``-bitexact`` matters more than it looks. Without it ffmpeg stamps an
    ``encoder=Lavf…`` tag, while the transcode path (which passes ``-bitexact``)
    does not — so in a blind set the genuine files would be the only ones
    carrying a tag, and one ffprobe call would hand over every label. Caught by
    ml/freeze_exchange_set.py's tag re-check on its first run.
    """
    dur = _probe_duration(src)
    if dur is None or dur < 20:
        return False
    start = max(0.0, (dur - EXCERPT_SEC) / 2)
    return _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{EXCERPT_SEC:.3f}",
            "-i",
            str(src),
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-bitexact",
            "-c:a",
            "flac",
            str(dst),
        ]
    )


def _probe_duration(path: Path) -> Optional[float]:
    """Return the duration of ``path`` in seconds, or None."""
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            capture_output=True,
            timeout=60,
        )
        return float(r.stdout.decode().strip()) if r.returncode == 0 else None
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return None


def transcode(args: Tuple[Path, Path, Codec]) -> Optional[Tuple[str, str, str]]:
    """Round-trip one excerpt through one codec back into FLAC.

    Metadata is stripped on the way out (``-map_metadata -1``) so no encoder tag
    survives into the FLAC — a detector must read the audio, not a ``Lavf`` string.
    """
    src, dst, codec = args
    if dst.exists():
        return (codec.name, dst.name, sha256(dst))
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        lossy = Path(tmp) / f"x.{codec.ext}"
        ok = _run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src),
                "-map",
                "0:a:0",
                "-map_metadata",
                "-1",
                "-c:a",
                codec.encoder,
                *codec.args,
                str(lossy),
            ]
        )
        if not ok:
            return None
        ok = _run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(lossy),
                "-map",
                "0:a:0",
                "-map_metadata",
                "-1",
                "-bitexact",
                "-c:a",
                "flac",
                "-sample_fmt",
                "s16",
                str(dst),
            ]
        )
        if not ok:
            return None
    return (codec.name, dst.name, sha256(dst))


def main(argv: Optional[List[str]] = None) -> int:
    """Build the audit corpus. Returns a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path, help="corpus root (keep it OFF Dropbox)")
    ap.add_argument("--n", type=int, default=80, help="number of source albums")
    ap.add_argument("--authentic-json", type=Path, default=Path("ml/authentic_files.json"))
    ap.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="build from a directory of freely-redistributable FLACs instead of the "
        "certified library — required for any corpus that will be sent to someone else",
    )
    ap.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 2))
    args = ap.parse_args(argv)

    out: Path = args.out
    (out / "authentic").mkdir(parents=True, exist_ok=True)

    if args.source_dir:
        sources = pick_sources_from_dir(args.source_dir, args.n)
        log.info("Selected %d redistributable sources (one per archive item)", len(sources))
    else:
        sources = pick_sources(args.authentic_json, args.n)
        log.info("Selected %d certified-authentic sources (one per album)", len(sources))

    manifest: Dict[str, object] = {
        "excerpt_sec": EXCERPT_SEC,
        "seed": SEED,
        "codecs": [c.name for c in CODECS],
        "unavailable_encoders": ["libfdk_aac", "qaac", "mpcenc"],
        "redistributable": bool(args.source_dir),
        "sources": [],
    }
    kept: List[Tuple[Path, Dict]] = []
    for i, entry in enumerate(sources):
        src = Path(entry["path"])
        dst = out / "authentic" / f"{_slug(src, i)}.flac"
        if not dst.exists() and not make_excerpt(src, dst):
            log.warning("excerpt failed: %s", src)
            continue
        kept.append((dst, entry))

    log.info("Built %d authentic excerpts", len(kept))

    jobs: List[Tuple[Path, Path, Codec]] = []
    for dst, _ in kept:
        for codec in CODECS:
            jobs.append((dst, out / "fake" / codec.name / dst.name, codec))

    log.info("Transcoding %d files with %d workers…", len(jobs), args.workers)
    done = 0
    with mp.Pool(args.workers) as pool:
        for result in pool.imap_unordered(transcode, jobs, chunksize=4):
            done += 1
            if result is None:
                log.warning("transcode failed (%d/%d)", done, len(jobs))
            if done % 50 == 0:
                log.info("  %d/%d", done, len(jobs))

    for dst, entry in kept:
        manifest["sources"].append(  # type: ignore[union-attr]
            {
                "slug": dst.stem,
                "origin": entry["path"],
                "ripper": entry.get("ripper"),
                "sha256": sha256(dst),
            }
        )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    log.info("Manifest written: %s", out / "manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
