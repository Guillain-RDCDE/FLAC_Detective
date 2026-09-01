"""The freezer's self-audit must actually refuse, not merely log.

Set A shipped in August with its LENGTH naming its arm: 108 of 288 files
identified their own class without a byte being decoded, and two of the eight
classes were identified outright. The repair was a frame-count audit in the
freezer — "a check in the freezer rather than in my attention", as it was
described to Provir.

That check did not work. It wrote its failure into a local named ``ok`` that
nothing read, inside a branch that only ran when sample rates had been collected,
and ``audit_own_output`` returned True regardless. It logged the leak and shipped
the set. These tests exist so that cannot happen silently again.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ml"))

from freeze_exchange_set import audit_own_output  # noqa: E402

LOG = logging.getLogger("freeze-audit-test")


def _labels(classes, per_class=3):
    """One label map with ``per_class`` files in each named class."""
    out = {}
    for cls in classes:
        for i in range(per_class):
            out[f"{cls}-{i}"] = {"label": cls, "source_slug": f"s{i}"}
    return out


def _digests(labels):
    """A distinct digest per file, so the duplicate check never fires here."""
    return {f"d{i:04d}": [fid] for i, fid in enumerate(labels)}


def test_a_uniform_set_is_accepted():
    """The control: one frame count and one rate everywhere must pass."""
    labels = _labels(["genuine", "mp3_320"])
    assert audit_own_output(
        _digests(labels),
        labels,
        LOG,
        sample_rates=dict.fromkeys(labels, 44100),
        frame_counts=dict.fromkeys(labels, 2646000),
    )


def test_a_frame_count_that_names_an_arm_is_REFUSED():
    """The exact August leak: one class with a length no other class has."""
    labels = _labels(["genuine", "mp3_320", "aac_ff256"])
    frames = dict.fromkeys(labels, 2646000)
    for fid in labels:
        if labels[fid]["label"] == "aac_ff256":
            frames[fid] = 2646016  # the AAC family, and nothing else
    assert not audit_own_output(
        _digests(labels),
        labels,
        LOG,
        sample_rates=dict.fromkeys(labels, 44100),
        frame_counts=frames,
    )


def test_the_frame_audit_runs_even_with_no_sample_rates():
    """It used to sit inside ``if sample_rates:`` and never run without them.

    A caller that collected frame counts but not rates got no frame audit at all,
    and no indication that the check had been skipped.
    """
    labels = _labels(["genuine", "mp3_320"])
    frames = dict.fromkeys(labels, 2646000)
    for fid in labels:
        if labels[fid]["label"] == "mp3_320":
            frames[fid] = 2646144
    assert not audit_own_output(_digests(labels), labels, LOG, frame_counts=frames)


def test_a_sample_rate_that_names_an_arm_is_REFUSED():
    """The other half of the same check, which did work — pinned so it stays."""
    labels = _labels(["genuine", "opus_256"])
    rates = dict.fromkeys(labels, 44100)
    for fid in labels:
        if labels[fid]["label"] == "opus_256":
            rates[fid] = 48000
    assert not audit_own_output(_digests(labels), labels, LOG, sample_rates=rates)


def test_duplicate_audio_is_still_refused():
    """The oldest of the three checks, kept under test alongside the new ones."""
    labels = _labels(["genuine", "mp3_320"])
    by_digest = {"same": list(labels)[:2]}
    for i, fid in enumerate(list(labels)[2:]):
        by_digest[f"d{i}"] = [fid]
    assert not audit_own_output(
        by_digest,
        labels,
        LOG,
        sample_rates=dict.fromkeys(labels, 44100),
        frame_counts=dict.fromkeys(labels, 2646000),
    )
