"""The quality stage reads the file once instead of three times.

Registered before measurement in
``ml/exchange/QUALITY_SINGLE_PASS_REGISTRATION_2026-09-18.md``. The finding: on
a 20-minute track the quality stage was 87% of the analysis, and its three
detectors each streamed the whole file — 13.1 s, 11.7 s, 12.9 s, three shares
that are equal because the three passes are the same pass.

The criterion registered there is **equality, not tolerance**: every field of
the three result dicts must be exactly what the three separate detectors
return. That is meant to be true by construction — the same blocks in the same
order, the same integer count, the same Python float accumulating the same
per-block sum, and each dict built by the detector that owns it — so a test
that only checked "close enough" would be testing the wrong claim and would
hide the case where the reasoning is wrong.

These are the edge cases where an accumulator rewrite goes wrong: a file that
is entirely silent, one that clips on every sample, a DC-shifted one, mono
against stereo, 24-bit, and a file the reader cannot get through at all.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.quality import (  # noqa: E402
    ClippingDetector,
    DCOffsetDetector,
    SilenceDetector,
    scan_quality_in_one_pass,
)

SR = 44_100


def _detectors():
    return ClippingDetector(), DCOffsetDetector(), SilenceDetector()


def _three_separate_passes(path: Path) -> dict:
    """What shipped: each detector streams the file on its own."""
    clipping, dc_offset, silence = _detectors()
    return {
        "clipping": clipping.detect(filepath=path),
        "dc_offset": dc_offset.detect(filepath=path),
        "silence": silence.detect(filepath=path),
    }


def _write(path: Path, samples: np.ndarray, subtype: str = "PCM_16") -> Path:
    sf.write(str(path), samples, SR, subtype=subtype)
    return path


def _music(seconds: float = 3.0, seed: int = 4, channels: int = 2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    shape = (n, channels) if channels > 1 else (n,)
    return rng.normal(0.0, 0.12, size=shape)


CASES = {
    "stereo_music": _music(),
    "mono_music": _music(channels=1),
    "fully_silent": np.zeros((SR * 2, 2)),
    "clipped_everywhere": np.ones((SR, 2)) * 0.999,
    "dc_shifted": np.clip(_music(seed=5) + 0.05, -1.0, 1.0),
    "leading_and_trailing_silence": np.concatenate(
        [np.zeros((SR * 3, 2)), _music(seconds=2.0, seed=6), np.zeros((SR * 3, 2))]
    ),
    "one_frame": _music(seconds=1 / SR),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_one_pass_equals_three_passes(tmp_path, name):
    """Criterion 1 of the registration: equal, field for field, not close."""
    path = _write(tmp_path / f"{name}.flac", CASES[name])

    before = _three_separate_passes(path)
    after = scan_quality_in_one_pass(path, *_detectors())

    assert after is not None, "the scan must succeed on a readable file"
    assert after == before


def test_equality_holds_on_24_bit_too(tmp_path):
    """Bit depth changes the decoded values; the two paths must still agree."""
    path = _write(tmp_path / "deep.flac", _music(seed=7), subtype="PCM_24")

    assert scan_quality_in_one_pass(path, *_detectors()) == _three_separate_passes(path)


def test_the_dc_value_is_equal_at_full_precision(tmp_path):
    """The one field where a rewrite could drift in the last bits.

    ``dc_offset_value`` is published rounded to six decimals, which is exactly
    the kind of rounding that hides a changed sum until the day it does not.
    Compared here before the rounding can help.
    """
    path = _write(tmp_path / "dc.flac", np.clip(_music(seed=8) + 0.003, -1.0, 1.0))

    clipping, dc_offset, silence = _detectors()
    fused_sum = 0.0
    for chunk in __import__(
        "flac_detective.analysis.new_scoring.audio_loader", fromlist=["sf_blocks"]
    ).sf_blocks(str(path), dtype="float32"):
        fused_sum += float(np.sum(chunk))

    info = sf.info(str(path))
    expected = dc_offset.result_from_sum(fused_sum, info.frames * info.channels)
    assert scan_quality_in_one_pass(path, clipping, dc_offset, silence)["dc_offset"] == expected


def test_an_unreadable_file_falls_back_rather_than_guessing(tmp_path):
    """Criterion 3: one shared loop must not cost the per-detector error handling."""
    broken = tmp_path / "broken.flac"
    broken.write_bytes(b"not a FLAC")

    assert scan_quality_in_one_pass(broken, *_detectors()) is None


class _FakeCache:
    """Enough of an AudioCache for ``analyze`` to skip its corruption check.

    That check returns early on a file it cannot open, so a corrupt file never
    reaches the three detectors at all. The fallback this test is about lives
    further in: the file looked readable, the shared scan still failed.
    """

    _is_partial = False

    def get_full_audio(self):
        raise RuntimeError("no audio here")


def test_the_fallback_gives_exactly_what_shipped(tmp_path):
    """Criterion 3: when the shared scan fails, the old three answers come back.

    One loop for three detectors means one exception could take all three down,
    where each used to fail on its own and report its own ``severity: "error"``.
    On a damaged file that difference is the whole behaviour, so the fallback
    must reproduce it exactly.
    """
    from flac_detective.analysis.quality import AudioQualityAnalyzer

    broken = tmp_path / "broken.flac"
    broken.write_bytes(b"not a FLAC either")

    results = AudioQualityAnalyzer().analyze(filepath=broken, cache=_FakeCache())
    expected = _three_separate_passes(broken)
    for key in ("clipping", "dc_offset", "silence"):
        assert results[key] == expected[key]
        assert results[key]["severity" if key != "silence" else "issue_type"] == "error"


def test_the_file_is_read_once_not_three_times(tmp_path, monkeypatch):
    """The whole point, pinned: one traversal, not three.

    Counting the traversals rather than timing them — a timing test would be
    flaky on a loaded machine and would not say WHY it got faster.
    """
    import flac_detective.analysis.quality as quality_mod

    path = _write(tmp_path / "counted.flac", _music(seconds=1.0))
    calls = {"n": 0}
    real = quality_mod.sf_blocks

    def counting(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(quality_mod, "sf_blocks", counting)
    scan_quality_in_one_pass(path, *_detectors())
    assert calls["n"] == 1

    calls["n"] = 0
    _three_separate_passes(path)
    assert calls["n"] == 3, "the old path is what this change removes"
