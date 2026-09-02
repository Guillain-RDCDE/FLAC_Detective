#!/usr/bin/env python3
"""Freeze a corpus into a blind, hash-keyed exchange set for a third party.

The point of a blind exchange is that the other author scores files without
knowing the answers, and neither side gets to choose the terrain. That only works
if the *files themselves* leak nothing:

* **Names carry no label.** ``fake/aac_ff320/000-Foo.flac`` announces its own
  answer. Everything is flattened into one directory of opaque ids.
* **Order carries no label.** A deterministic shuffle keyed by a fixed seed, so
  neighbouring ids are unrelated and the set is still reproducible from here.
* **Tags carry no label.** The corpus builder already strips metadata
  (``-map_metadata -1``), and this re-checks rather than assuming.
* **Duration carries no label** — every file is the same excerpt length.

What it cannot hide, stated so nobody discovers it later and calls it a trick:
**file size**. A FLAC of decoded 320 kbps AAC compresses differently from a FLAC
of the original, so sizes are weakly informative. Padding them would corrupt the
audio, so the honest move is to disclose it. Provir's own frozen corpus has the
same property.

Three outputs:

``<out>/audio/``      the files, named ``<prefix>-0001.flac`` …
``<out>/MANIFEST.sha256``  id + sha256 + bytes — goes to the recipient
``<out>/README.md``   what the set is, how to return verdicts, licensing
``<out>/../<name>-LABELS.json``  the answer key — stays here, gitignored

The labels file is written OUTSIDE the shipped directory on purpose, so that
"zip the folder and send it" cannot accidentally include the answers.

Usage::

    python ml/freeze_exchange_set.py --corpus C:/Users/loutr/exchange_corpus \\
        --out C:/Users/loutr/fd-exchange-2026-08 --name fd-exchange-2026-08
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import soundfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

SEED = 20260815


class KeyRefused(Exception):
    """The key cannot be written as asked. Raised instead of shipping a silent gap."""


def build_key(
    labels: Dict[str, Dict[str, str]],
    strata: Optional[Dict[str, str]],
    seed: int,
    *,
    no_strata: bool = False,
) -> Dict[str, object]:
    """Assemble the answer key, refusing to leave the stratum map to chance.

    Set A r2 shipped with a key carrying ``labels`` and nothing else, three hours
    after the pre-r2 key that did carry a stratum map — and the letter announcing
    the set said the key labelled the band-limited sources. It did not. Nothing
    failed, because nothing checked: this function is the check.

    A stratum map is therefore not optional, it is a decision. Either one is
    supplied and it must cover every source in the set, or the caller states in
    so many words that this set has no strata. Silence is refused.

    Args:
        labels: file id -> {"label": …, "source_slug": …}, as the freeze loop built it.
        strata: source_slug -> stratum name, or None.
        seed: The shuffle seed, recorded in the key.
        no_strata: Explicit declaration that this set is unstratified.

    Returns:
        The key payload, ready to serialise.

    Raises:
        KeyRefused: if no decision was made about strata, if both were given, or
            if the map does not cover every source in the set.
    """
    slugs = {entry.get("source_slug", "") for entry in labels.values()}
    if strata and no_strata:
        raise KeyRefused("a stratum map was supplied AND declared absent — decide which")
    if strata is None and not no_strata:
        raise KeyRefused(
            "no stratum map and no --no-strata declaration. Set A r2 shipped without "
            "one while its letter said otherwise; say which this set is."
        )
    if strata is not None:
        uncovered = sorted(s for s in slugs if s not in strata)
        if uncovered:
            raise KeyRefused(
                f"the stratum map misses {len(uncovered)} of {len(slugs)} sources "
                f"({', '.join(uncovered[:3])}…) — a partial map scores a partial set"
            )
    return {
        "seed": seed,
        "n": len(labels),
        "labels": labels,
        "strata": strata if strata is not None else {},
        "strata_declared": bool(strata),
    }


def write_key(path: Path, payload: Dict[str, object]) -> str:
    """Write the key and seal it in the same action. Returns the digest.

    The hash is written at BUILD time, beside the key, so it can be published with
    the manifest before either side has scored anything. Neither party in v3 could
    prove their key predated the other's verdicts; a digest that only appears when
    the key is released proves nothing about when the key was fixed.

    The digest file is sha256sum-style with LF, which is what the other side reads.
    """
    body = (json.dumps(payload, indent=1) + "\n").encode("utf-8")
    path.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    path.with_suffix(path.suffix + ".sha256").write_bytes(
        f"{digest}  {path.name}\n".encode("ascii")
    )
    return digest


def sha256(path: Path) -> str:
    """Return the SHA-256 of ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def has_tags(path: Path) -> bool:
    """True if ffprobe finds any metadata tag on ``path``, or cannot tell.

    Checked rather than trusted: a single surviving ``encoder`` tag would hand
    the recipient the answer for that file, and one leaked label is enough to
    make a blind set arguable.

    Two repairs, 2026-09-02, both of the species this exchange keeps finding:

    **A failure to check was reported as a clean file.** ffprobe missing, timing
    out or erroring returned False — "no tags" — so the freeze continued and
    shipped a file nobody had actually inspected. An unverifiable file is not a
    clean one, and the safe direction is the one that stops the freeze. It now
    returns True and says why, which aborts the freeze rather than the check.

    **Only FORMAT tags were read.** ffmpeg writes an encoder string into stream
    tags too, and Provir's set B carried exactly that shape of leak in its WAV
    headers — a LIST/INFO chunk naming the muxer, identical on all 280 files, so
    harmless there only by luck. ``stream_tags`` is now read as well.
    """
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format_tags:stream_tags",
                "-of",
                "default=nw=1",
                str(path),
            ],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.error("cannot verify tags on %s (%s) — treating it as tagged", path.name, exc)
        return True
    if r.returncode != 0:
        log.error(
            "ffprobe failed on %s (exit %d) — treating it as tagged",
            path.name,
            r.returncode,
        )
        return True
    return bool(r.stdout.decode(errors="replace").strip())


def normalise(src: Path, dst: Path) -> bool:
    """Copy ``src`` to ``dst`` with the container normalised and tags stripped.

    A stream copy, so the audio is bit-identical; only the container header
    changes. This does not trust the corpus builder to have produced uniform
    files, and the first run proved why: the genuine excerpts carried an
    ``encoder=Lavf…`` tag that the transcodes did not, which meant a single
    ffprobe call revealed every label in the set.
    """
    try:
        r = subprocess.run(
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
                "-c:a",
                "copy",
                "-map_metadata",
                "-1",
                "-bitexact",
                str(dst),
            ],
            capture_output=True,
            timeout=300,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def collect(corpus: Path) -> List[Tuple[Path, str, str]]:
    """Return ``(path, label, slug)`` for every file in the corpus.

    ``label`` is "genuine" or the codec name; it goes to the answer key only.
    """
    items: List[Tuple[Path, str, str]] = []
    for f in sorted((corpus / "authentic").glob("*.flac")):
        items.append((f, "genuine", f.stem))
    for codec_dir in sorted((corpus / "fake").glob("*")):
        if codec_dir.is_dir():
            for f in sorted(codec_dir.glob("*.flac")):
                items.append((f, codec_dir.name, f.stem))
    return items


def audit_own_output(
    by_digest: Dict[str, List[str]],
    labels: Dict[str, Dict[str, str]],
    log: logging.Logger,
    sample_rates: Optional[Dict[str, int]] = None,
    frame_counts: Optional[Dict[str, int]] = None,
) -> bool:
    """Check the frozen set against ITSELF. Returns False if it must not ship.

    The 2026-08 set shipped with ten byte-identical pairs — one entire source
    group, all ten of its arms, present twice under two sets of names. Two
    archive.org items held the same taper's same track (…-matrix-… and
    …-matrix2-…), and the corpus dedup keyed on the item identifier rather than on
    the audio, so both passed as independent recordings.

    The freeze had already COMPUTED the evidence: it hashes every file on the way
    out. It wrote those hashes to the manifest and never compared them to each
    other. The tag check looks outward, at what might leak; nothing looked inward,
    at what had just been produced. Jamie Dodd of Provir found the pairs by sorting
    the shipped manifest, which is all it ever took.

    Two costs, both mild and both real: per-arm denominators say 60 when one
    recording is counted twice, and the repeated hashes leak by themselves —
    sorting the manifest reveals that those twenty files carry only ten distinct
    labels, without touching the audio.
    """
    duplicates = {d: ids for d, ids in by_digest.items() if len(ids) > 1}
    if duplicates:
        for digest, ids in sorted(duplicates.items(), key=lambda kv: kv[1]):
            log.error("  byte-identical: %s  (%s…)", " == ".join(ids), digest[:16])
        log.error(
            "%d digests appear more than once. A blind set cannot ship with duplicate "
            "audio: the denominators are wrong and the repeated hashes are visible in "
            "the manifest. Deduplicate the CORPUS by content, not by source "
            "identifier, and re-freeze.",
            len(duplicates),
        )
        return False

    # A source contributing fewer arms than its peers skews that arm's denominator
    # the same way, and is just as invisible once the ids are shuffled.
    per_slug: Dict[str, int] = {}
    for entry in labels.values():
        per_slug[entry["source_slug"]] = per_slug.get(entry["source_slug"], 0) + 1
    if per_slug:
        expected = max(per_slug.values())
        short = {slug: n for slug, n in per_slug.items() if n != expected}
        if short:
            log.warning(
                "%d source(s) contributed fewer than %d arms: %s. Not fatal, but every "
                "arm they are missing from has a smaller denominator than the others.",
                len(short),
                expected,
                ", ".join(f"{k}={v}" for k, v in sorted(short.items())[:5]),
            )

    # Both audits run, THEN the verdict — so a set with two leaks reports two
    # rather than stopping at the first and hiding the second behind a re-freeze.
    ok = True
    if frame_counts and not _audit_frame_counts(labels, frame_counts, log):
        ok = False
    if sample_rates and not _audit_sample_rates(labels, sample_rates, log):
        ok = False
    return ok


def _audit_frame_counts(
    labels: Dict[str, Dict[str, str]],
    frame_counts: Dict[str, int],
    log: logging.Logger,
) -> bool:
    """Refuse a set whose LENGTH names its arm. Returns False if it must not ship.

    The 2026-08-31 set A shipped with three distinct frame counts across eight
    classes, and two of them were pure labels: 2,646,144 samples meant mp2_256
    and nothing else, 2,646,016 meant the AAC family and nothing else. **108 of
    288 files announced their arm without a byte being decoded.**

    The cause is that an arm is built by encode-then-decode and every codec adds
    its own delay and padding, so the decoded length is characteristic of the
    codec. The README promised "all excerpts are the same length"; they were not,
    and nobody checked because nothing checked.

    Provir found the same species in his own set B build the same evening — his
    partitioned six of eight classes by byte size — and sent the mechanism before
    scoring rather than after, which is the only moment it is worth anything. It
    is his warning that produced this function.
    """
    counts: Dict[int, set] = {}
    for file_id, frames in frame_counts.items():
        label = labels.get(file_id, {}).get("label", "?")
        counts.setdefault(frames, set()).add(label)
    if len(counts) == 1:
        return True
    log.error(
        "%d distinct frame counts across the set — LENGTH IS A LABEL and the set " "cannot ship:",
        len(counts),
    )
    leaked = False
    for frames, labs in sorted(counts.items()):
        n = sum(1 for v in frame_counts.values() if v == frames)
        marker = "  <-- identifies the arm outright" if len(labs) == 1 else ""
        log.error("  %d samples: %s (%d files)%s", frames, sorted(labs), n, marker)
        if len(labs) == 1:
            leaked = True
    log.error(
        "Trim every file to an identical sample count before freezing. %s",
        "At least one length is a single class." if leaked else "",
    )
    return False


def _audit_sample_rates(
    labels: Dict[str, Dict[str, str]],
    sample_rates: Dict[str, int],
    log: logging.Logger,
) -> bool:
    """Refuse a set where an arm is identifiable from its sample rate alone.

    The 2026-08 set shipped with its Opus arm at 48 kHz on 100 % of files while
    every other arm and the genuine files kept the source rate (78 % at 44.1 kHz).
    Opus/CELT works at 48 kHz whatever you feed it, and the round-trip never came
    back to the source rate — so every Opus file was identifiable *without decoding
    a sample*. Provir's return duly carried an AI_SR_48000 flag on 100 % of them.

    Third instance of one species: the encoder tags that leaked first, the repeated
    digests that leaked second, and now a container property. Each time the freeze
    checked what it had thought of and not what it had produced. So the rule here is
    the general one — no arm may have a sample-rate distribution that the genuine
    arm does not also have — rather than a special case for Opus.

    Note the milder version this also catches: an encoder with a rate ceiling (MP3
    tops out at 48 kHz) silently downsamples 96 kHz sources, so "48 kHz with no
    96 kHz counterpart" becomes a partial tell for that arm too.
    """
    per_arm: Dict[str, Dict[int, int]] = {}
    for file_id, entry in labels.items():
        rate = sample_rates.get(file_id)
        if rate is None:
            continue
        per_arm.setdefault(entry["label"], {}).setdefault(rate, 0)
        per_arm[entry["label"]][rate] += 1

    genuine = per_arm.get("genuine")
    if not genuine:
        log.warning("no genuine arm found; skipping the sample-rate leak audit")
        return True

    genuine_total = sum(genuine.values())
    leaked = False
    for arm, rates in sorted(per_arm.items()):
        if arm == "genuine":
            continue
        total = sum(rates.values())
        for rate, count in sorted(rates.items()):
            share = count / total
            genuine_share = genuine.get(rate, 0) / genuine_total
            # A rate carrying most of an arm while being rare among genuine files
            # is a label, not a property of the music.
            if share >= 0.9 and genuine_share <= 0.5:
                log.error(
                    "  arm %s is %.0f%% at %d Hz, but only %.0f%% of genuine files are "
                    "— identifiable without decoding a sample",
                    arm,
                    100 * share,
                    rate,
                    100 * genuine_share,
                )
                leaked = True

    if leaked:
        log.error(
            "A blind set cannot ship with an arm identifiable from its container. "
            "Resample the round-trip back to the source rate, or drop the arm."
        )
        return False
    return True


README_TEMPLATE = """# {name} — blind exchange set

{n_files} lossless FLAC files, {seconds:g}-second excerpts, 16-bit.

Some are genuine and some have been round-tripped through a lossy encoder and
back to FLAC. **The labels are withheld.** Which is which, and how many of each,
is not disclosed here — that is the point.

## Provenance and licensing

Every source recording comes from the Internet Archive Live Music Archive
(collection `etree`), which is explicitly licensed for free redistribution. The
derived transcodes inherit that, so this set can be passed around without a
licensing problem. One source file per archive item, so the sources are
independent recordings rather than tracks off the same show.

## What is deliberately hidden

- Filenames are opaque ids in a shuffled order; nothing in a name or its
  position indicates a label.
- Metadata is stripped; every file was re-checked with ffprobe after freezing.
- All excerpts are the same length.

## What is NOT hidden, disclosed rather than discovered

**File size carries a little signal.** A FLAC of decoded lossy audio compresses
differently from a FLAC of the original, and that cannot be fixed without
altering the audio. Measured on this set, byte size alone separates genuine from
transcoded at **AUC 0.557** (on the 2026-08 set) — barely above the 0.5 coin flip, but not zero.

It is quoted rather than hand-waved so that nobody has to wonder whether it was
noticed. Anyone can verify it from `MANIFEST.sha256`, which carries the byte
length of every file precisely so this is checkable rather than asserted.

## Integrity

`MANIFEST.sha256` lists every file as `<sha256>  <path>  <bytes>` — three
columns, because the byte length is part of what is being attested. That third
column means **plain `sha256sum -c` cannot read it**: it takes everything after
the digest as the filename and reports "FAILED open or read" on every line. Said
here rather than left for the recipient to discover, which is what happened with
the 2026-08 set. Verify with either of:

```sh
awk '{{print $1 "  " $2}}' MANIFEST.sha256 | sha256sum -c   # GNU coreutils
python - <<'EOF'
import hashlib, pathlib
for line in pathlib.Path("MANIFEST.sha256").read_text().splitlines():
    digest, rel, size = line.split()
    data = pathlib.Path(rel).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, rel
    assert len(data) == int(size), rel
print("all files verified")
EOF
```

If a hash does not match, the file changed in transit and its verdict is void.

## What to send back

A CSV or JSON keyed by the `id` column of the manifest, with your verdict per
file. Whatever tiering your engine uses is fine — just say which of your states
count as "flagged" and which as "convicted", so the two are never mixed.

Scoring is done by whoever holds the key, against the answers, and the answers
are published to the other side afterwards either way — including on the rows
where the key-holder's own tool does badly.
"""


def main(argv: Optional[List[str]] = None) -> int:
    """Freeze the corpus. Returns a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", required=True, type=Path, help="built by ml/build_audit_corpus.py")
    ap.add_argument("--out", required=True, type=Path, help="directory to create and ship")
    ap.add_argument("--name", default="fd-exchange", help="id prefix and set name")
    ap.add_argument("--seconds", type=float, default=60.0, help="excerpt length, for the README")
    ap.add_argument(
        "--skip-tag-check", action="store_true", help="skip the ffprobe metadata re-check"
    )
    ap.add_argument(
        "--strata",
        type=Path,
        help="JSON map source_slug -> stratum, folded into the key. Must cover every source.",
    )
    ap.add_argument(
        "--no-strata",
        action="store_true",
        help="declare that this set is unstratified. Required when --strata is absent.",
    )
    args = ap.parse_args(argv)

    items = collect(args.corpus)
    if not items:
        log.error("no files under %s", args.corpus)
        return 1

    rng = random.Random(SEED)
    rng.shuffle(items)
    log.info("Freezing %d files from %s", len(items), args.corpus)

    audio_dir = args.out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    manifest_lines: List[str] = []
    labels: Dict[str, Dict[str, str]] = {}
    tagged: List[str] = []
    # Every digest computed below, so the set can be checked against ITSELF before
    # it ships. See the audit at the end of this function.
    by_digest: Dict[str, List[str]] = {}
    # Container properties leak too — see _audit_sample_rates and
    # _audit_frame_counts.
    sample_rates: Dict[str, int] = {}
    frame_counts: Dict[str, int] = {}

    for index, (src, label, slug) in enumerate(items, 1):
        file_id = f"{args.name}-{index:04d}"
        dst = audio_dir / f"{file_id}.flac"
        if not dst.exists() and not normalise(src, dst):
            log.error("could not normalise %s", src)
            return 1
        digest = sha256(dst)
        by_digest.setdefault(digest, []).append(file_id)
        try:
            info = soundfile.info(str(dst))
            sample_rates[file_id] = int(info.samplerate)
            frame_counts[file_id] = int(info.frames)
        except Exception:  # an unreadable rate must not abort the freeze
            pass
        manifest_lines.append(f"{digest}  audio/{file_id}.flac  {dst.stat().st_size}")
        labels[file_id] = {"label": label, "source_slug": slug}
        if not args.skip_tag_check and has_tags(dst):
            tagged.append(file_id)
        if index % 100 == 0:
            log.info("  %d/%d", index, len(items))

    if tagged:
        log.error(
            "%d files still carry metadata tags (%s…) — a blind set cannot ship "
            "with tags that may name the encoder",
            len(tagged),
            ", ".join(tagged[:3]),
        )
        return 1

    if not audit_own_output(by_digest, labels, log, sample_rates, frame_counts):
        return 1

    (args.out / "MANIFEST.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    (args.out / "README.md").write_text(
        README_TEMPLATE.format(name=args.name, n_files=len(items), seconds=args.seconds),
        encoding="utf-8",
    )

    # The key lives OUTSIDE the shipped directory, so that zipping the folder
    # cannot include the answers.
    key_path = args.out.parent / f"{args.name}-LABELS.json"
    strata: Optional[Dict[str, str]] = None
    if args.strata:
        strata = json.loads(args.strata.read_text(encoding="utf-8"))
        strata = strata.get("strata", strata)  # accept a bare map or a wrapped one
    try:
        payload = build_key(labels, strata, SEED, no_strata=args.no_strata)
    except KeyRefused as exc:
        log.error("refusing to write the answer key: %s", exc)
        return 1
    digest = write_key(key_path, payload)

    counts: Dict[str, int] = {}
    for entry in labels.values():
        counts[entry["label"]] = counts.get(entry["label"], 0) + 1
    log.info("Shipped set : %s (%d files)", args.out, len(items))
    log.info("Answer key  : %s  — DO NOT SEND", key_path)
    log.info("Key sha256  : %s  — publish this WITH the manifest, before scoring", digest)
    log.info(
        "Strata      : %s",
        f"{len(payload['strata'])} sources mapped" if payload["strata_declared"] else "declared none",
    )
    log.info("Composition (key-side only): %s", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
