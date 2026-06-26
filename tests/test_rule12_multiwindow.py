"""Rule 12 multi-window inference (#3): the ``_window_offsets`` geometry.

This is pure arithmetic (no torch/librosa), so it runs everywhere and gets the
most cases — it is the part most likely to hide an off-by-one. The probability
aggregation that needs torch lives in ``test_rule12_aggregation.py``.
"""

from __future__ import annotations

import pytest

from flac_detective.analysis.new_scoring.rules import ml_classifier as mc


def test_short_file_single_middle_window():
    """A file shorter than one segment yields exactly one (middle) window."""
    offs = mc._window_offsets(duration=8.0, n_windows=3)
    assert offs == [0.0]


def test_n_windows_one_is_middle():
    """n_windows=1 recovers the single middle-of-file offset."""
    offs = mc._window_offsets(duration=200.0, n_windows=1)
    assert offs == [pytest.approx((200.0 - mc._SEGMENT_SEC) / 2)]


def test_three_windows_are_spread_and_ordered():
    """Three windows on a long file are distinct, ordered, and centred at 25/50/75%."""
    duration = 200.0
    offs = mc._window_offsets(duration=duration, n_windows=3)
    assert len(offs) == 3
    assert offs == sorted(offs)
    half = mc._SEGMENT_SEC / 2
    assert offs[0] == pytest.approx(50.0 - half)
    assert offs[1] == pytest.approx(100.0 - half)
    assert offs[2] == pytest.approx(150.0 - half)


def test_offsets_stay_within_bounds():
    """Every offset leaves a full segment inside the file."""
    duration = 45.0
    for n in (1, 2, 3, 5):
        for off in mc._window_offsets(duration=duration, n_windows=n):
            assert 0.0 <= off <= duration - mc._SEGMENT_SEC + 1e-9


def test_near_identical_offsets_deduped():
    """On a barely-longer-than-a-segment file, near-duplicate windows collapse to one."""
    offs = mc._window_offsets(duration=10.4, n_windows=3)
    assert len(offs) == 1
