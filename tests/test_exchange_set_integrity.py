"""A blind set must be checked against its own output, not only against leaks.

The 2026-08 exchange set shipped 599 files that were 589 distinct files: ten
byte-identical pairs, which turned out to be one entire source group — all ten of
its arms — present twice under two sets of names. Two archive.org items held the
same taper's same track (`…-matrix-…` and `…-matrix2-…`), and the corpus dedup
keyed on the item identifier rather than on the audio.

The part worth a permanent test is not the duplication. It is that
``ml/freeze_exchange_set.py`` had already **computed** the proof — it hashes every
file on its way out — and wrote those hashes to the manifest without ever
comparing them to each other. It ran a careful check for metadata tags, which
looks *outward* at what might leak, and no check at all on what it had just
produced. Jamie Dodd of Provir found the pairs by sorting the shipped manifest.

Both costs are mild and both are real: per-arm denominators read 60 when one
recording is counted twice, and the repeated hashes leak on their own — anyone
sorting the manifest learns those twenty files carry only ten distinct labels,
without ever touching the audio.

These tests run against the manifest that actually shipped, so they answer "is the
set we handed someone still what we think it is?" rather than "would fresh code
behave?".
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

MANIFEST = Path(__file__).resolve().parent.parent / "ml" / "exchange" / "MANIFEST.sha256"

# The set as shipped. Pinned so a re-freeze that silently changes the corpus size
# has to come past this line and say so.
SHIPPED_ROWS = 599
SHIPPED_DISTINCT = 589


def _entries():
    """(file_id, digest, size) for every manifest row."""
    if not MANIFEST.exists():
        pytest.skip(f"{MANIFEST} not present")
    out = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel, size = line.split()
        out.append((rel.split("/")[-1].replace(".flac", ""), digest, int(size)))
    return out


def test_manifest_row_count_is_the_shipped_one() -> None:
    """The manifest is a sealed artefact; its size is not free to drift."""
    assert len(_entries()) == SHIPPED_ROWS


def test_file_ids_are_unique() -> None:
    """Two rows naming the same id would make the manifest self-contradictory."""
    ids = [fid for fid, _, _ in _entries()]
    repeated = [fid for fid, n in Counter(ids).items() if n > 1]
    assert not repeated, f"file ids appear more than once: {sorted(repeated)[:5]}"


def test_duplicate_content_is_known_and_accounted_for() -> None:
    """The known duplication, pinned — so *new* duplication is distinguishable.

    This deliberately asserts the historical defect rather than asserting zero
    duplicates. The shipped set cannot be un-shipped: verdicts have been exchanged
    against these exact ids, so re-freezing it would invalidate a comparison that
    is already made. What matters is that the count stays exactly what was
    disclosed, so a future change cannot hide behind a number that was already
    wrong.
    """
    entries = _entries()
    by_digest: dict[str, list[str]] = {}
    for fid, digest, _ in entries:
        by_digest.setdefault(digest, []).append(fid)

    distinct = len(by_digest)
    duplicated = {d: ids for d, ids in by_digest.items() if len(ids) > 1}

    assert distinct == SHIPPED_DISTINCT, (
        f"the shipped set holds {distinct} distinct files, not {SHIPPED_DISTINCT}. "
        "If the corpus was re-frozen, the published per-arm denominators and every "
        "rate derived from them need recomputing — and the other side scored the "
        "old ids."
    )
    assert len(duplicated) == SHIPPED_ROWS - SHIPPED_DISTINCT, (
        "the number of byte-identical groups changed. Each duplicated group counts "
        "one recording twice in every arm it appears in."
    )
    assert all(len(ids) == 2 for ids in duplicated.values()), (
        "a digest now appears more than twice, which is a different defect from the "
        "one disclosed: the published correction assumed pairs."
    )


def test_sizes_agree_with_digests() -> None:
    """Byte-identical files must report identical lengths.

    Cheap, and it catches a manifest assembled from two different runs — the size
    column and the digest column coming from different states of the same file is
    exactly the kind of drift a sealed artefact is supposed to make impossible.
    """
    by_digest: dict[str, set[int]] = {}
    for _fid, digest, size in _entries():
        by_digest.setdefault(digest, set()).add(size)
    inconsistent = {d: s for d, s in by_digest.items() if len(s) > 1}
    assert not inconsistent, (
        f"{len(inconsistent)} digest(s) carry more than one byte length. The manifest "
        "was not written from a single consistent state of the audio."
    )
