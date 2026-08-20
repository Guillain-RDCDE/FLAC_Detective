"""Content-level dedup of exchange sources — the 599-that-were-589 repair.

The 2026-08 exchange set shipped one source group twice because its dedup keyed
on the archive-item identifier: two etree items carried the same taper's same
track. The repair hashes 30 s of decoded PCM at pick time, so the same audio
under different filenames, tags or FLAC re-encodes collapses to one row. This
test builds that exact trap — one recording under two item names, plus one
genuinely distinct recording — and pins that the picker keeps two, not three.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

soundfile = pytest.importorskip("soundfile")

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="needs ffmpeg to decode fingerprints"
)

_PATH = Path(__file__).resolve().parent.parent / "ml" / "build_audit_corpus.py"
_SPEC = importlib.util.spec_from_file_location("build_audit_corpus", _PATH)
bac = importlib.util.module_from_spec(_SPEC)
sys.modules["build_audit_corpus"] = bac
_SPEC.loader.exec_module(bac)


def _write_flac(path: Path, audio: np.ndarray, rate: int = 44100) -> None:
    soundfile.write(str(path), audio, rate, subtype="PCM_16")


def test_same_audio_under_two_items_collapses_to_one(tmp_path):
    rng = np.random.default_rng(20260820)
    recording = (0.1 * rng.standard_normal(44100 * 2)).astype(np.float32)
    other = (0.1 * rng.standard_normal(44100 * 2)).astype(np.float32)

    # The historical trap: same audio, two archive-item identifiers.
    _write_flac(tmp_path / "023-gd-matrix-01__intro.flac", recording)
    _write_flac(tmp_path / "026-gd-matrix2-01__intro.flac", recording)
    _write_flac(tmp_path / "047-calexico-01__song.flac", other)

    picked = bac.pick_sources_from_dir(tmp_path, n=10)
    assert len(picked) == 2, (
        f"expected the duplicate recording to collapse, got {len(picked)} rows: "
        f"{[p['path'] for p in picked]}"
    )
    digests = [p["pcm_digest"] for p in picked]
    assert len(set(digests)) == 2


def test_distinct_audio_is_kept(tmp_path):
    rng = np.random.default_rng(7)
    for i in range(3):
        audio = (0.1 * rng.standard_normal(44100 * 2)).astype(np.float32)
        _write_flac(tmp_path / f"item{i}__track.flac", audio)
    picked = bac.pick_sources_from_dir(tmp_path, n=10)
    assert len(picked) == 3
