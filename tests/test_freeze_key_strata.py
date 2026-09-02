"""The answer key must not be able to lose its stratum map in silence.

Set A r2 was frozen on 31 August with a key carrying ``labels`` and nothing
else. Three hours earlier the pre-r2 key had carried a stratum map of 36
sources, 12 of them band-limited. The letter that shipped the set told the other
party that the key labelled those twelve. It did not, and nothing noticed for
two days — the omission surfaced only when the key was read back before release,
by hand.

Nothing failed because nothing checked. These tests are the check: a key is
written with a stratum map, or with a declaration that the set has none, and
never by omission. The digest is written in the same action, because a key
sealed only at release time proves nothing about when it was fixed.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

from freeze_exchange_set import KeyRefused, build_key, write_key  # noqa: E402

SEED = 20260831


def _labels(n_band: int = 2, n_full: int = 3):
    """A label map over ``n_band + n_full`` sources, one file each."""
    labels = {}
    strata = {}
    for i in range(n_band):
        labels[f"f{i:03d}"] = {"label": "genuine", "source_slug": f"s{i:03d}"}
        strata[f"s{i:03d}"] = "band_limited_synthetic"
    for i in range(n_band, n_band + n_full):
        labels[f"f{i:03d}"] = {"label": "mp3_320", "source_slug": f"s{i:03d}"}
        strata[f"s{i:03d}"] = "full_band"
    return labels, strata


def test_silence_about_strata_is_refused():
    """The r2 defect itself: no map, no declaration, and a key written anyway."""
    labels, _ = _labels()
    with pytest.raises(KeyRefused, match="no stratum map"):
        build_key(labels, None, SEED)


def test_a_declared_unstratified_set_is_allowed():
    """Saying so is fine. Not saying is not."""
    labels, _ = _labels()
    key = build_key(labels, None, SEED, no_strata=True)
    assert key["strata"] == {}
    assert key["strata_declared"] is False


def test_a_partial_map_is_refused():
    """A map covering some sources scores some of the set and hides the rest."""
    labels, strata = _labels()
    strata.pop("s000")
    with pytest.raises(KeyRefused, match="misses 1 of 5"):
        build_key(labels, strata, SEED)


def test_declaring_both_is_refused():
    """A map and a declaration of no map is not a decision, it is two."""
    labels, strata = _labels()
    with pytest.raises(KeyRefused, match="decide which"):
        build_key(labels, strata, SEED, no_strata=True)


def test_the_map_reaches_the_key():
    """What the letter said the key contained, the key now contains."""
    labels, strata = _labels(n_band=2, n_full=3)
    key = build_key(labels, strata, SEED)
    assert key["strata_declared"] is True
    assert sum(1 for v in key["strata"].values() if v.startswith("band_limited")) == 2
    assert set(key["strata"]) == {e["source_slug"] for e in labels.values()}
    assert key["n"] == len(labels)
    assert key["seed"] == SEED


def test_the_key_is_sealed_in_the_same_action(tmp_path):
    """The digest is written with the key, not when the key is released."""
    labels, strata = _labels()
    path = tmp_path / "set-LABELS.json"
    digest = write_key(path, build_key(labels, strata, SEED))

    sidecar = tmp_path / "set-LABELS.json.sha256"
    assert sidecar.exists(), "no digest was written beside the key"
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()

    raw = sidecar.read_bytes()
    assert raw == f"{digest}  {path.name}\n".encode("ascii")
    assert b"\r" not in raw, "the digest file must be LF: the other side hashes it as bytes"

    # And the key still parses as the key.
    assert json.loads(path.read_text(encoding="utf-8"))["strata"] == strata
