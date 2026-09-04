"""Gates for the offset probe — the instrument that will produce the next number.

``ml/read_offset_fixed_window.py`` measures whether this engine's read-position
defect is deterministic. Its output is going into a letter, which is precisely
the situation ``tests/test_exchange_harness.py`` was written for: excellent gates
on the engine, none on the thing generating the evidence.

Every case below can fail. Each either feeds something wrong and demands the
right refusal, or has a known answer that differs from the obvious one. In
particular there is a test for the failure this probe actually shipped with on
its first run — a control that printed its reassuring conclusion while its
denominator was zero.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

ML = Path(__file__).resolve().parent.parent / "ml"
sys.path.insert(0, str(ML))

import read_offset_fixed_window as probe  # noqa: E402
import score_v3_return  # noqa: E402

RATE = 44100


class Args:
    """The two fields ``report`` reads off the argparse namespace."""

    address_tol = probe.ADDRESS_TOL_HZ


def make_flac(path: Path, seconds: float = 3.0, seed: int = 0) -> Path:
    """A short 16-bit stereo FLAC of reproducible noise."""
    rng = np.random.default_rng(seed)
    frames = int(seconds * RATE)
    data = (rng.integers(-20000, 20000, size=(frames, 2))).astype(np.int32) << 16
    sf.write(str(path), data, RATE, subtype="PCM_16", format="FLAC")
    return path


def row(population, offset, verdict, score_value, cutoff, name="f.flac"):
    return {
        "file": name,
        "population": population,
        "offset_samples": offset,
        "offset_s": offset / RATE,
        "window_s": 60.0,
        "verdict": verdict,
        "score": score_value,
        "cutoff_hz": cutoff,
        "families": "",
        "slice_exact": "yes",
    }


# --------------------------------------------------------------------------
# The verdict ladder must not drift away from the one used in the exchange
# --------------------------------------------------------------------------


def test_verdict_ladder_matches_the_exchange_scorer():
    """Pin the ladder to the exchange scorer's.

    Two copies of "what counts as a conviction" is how one report quietly means
    something different from another report of the same experiment.
    """
    assert probe.CONVICTION == score_v3_return.CONVICTION
    assert probe.SIGNALED == score_v3_return.SIGNALED


# --------------------------------------------------------------------------
# The slicing step must not be an intervention
# --------------------------------------------------------------------------


def test_slice_is_sample_exact_at_an_awkward_offset(tmp_path):
    """Slice at a prime offset and compare the PCM sample for sample.

    A prime offset, not a round one: an off-by-a-frame bug survives offsets that
    happen to land on block boundaries and dies on this.
    """
    src = make_flac(tmp_path / "src.flac", seconds=3.0, seed=1)
    out = tmp_path / "cut.flac"
    start, length = 4409, 22051
    probe.slice_to_flac(src, start, length, out)

    reference, _ = sf.read(str(src), start=start, frames=length, dtype="int32")
    produced, _ = sf.read(str(out), dtype="int32")
    assert produced.shape == reference.shape
    assert np.array_equal(reference, produced)
    assert probe.slice_is_exact(src, start, length, out) is True


def test_the_exactness_check_can_actually_fail(tmp_path):
    """The exactness check must be able to say no.

    A checker that always returns True is not a checker. Hand it a window
    written from the wrong offset and it must say so.
    """
    src = make_flac(tmp_path / "src.flac", seconds=3.0, seed=2)
    out = tmp_path / "cut.flac"
    probe.slice_to_flac(src, 10000, 20000, out)
    assert probe.slice_is_exact(src, 10000, 20000, out) is True
    assert probe.slice_is_exact(src, 10001, 20000, out) is False


# --------------------------------------------------------------------------
# A failed read must not be able to impersonate a perfect result
# --------------------------------------------------------------------------


def test_spread_of_nothing_is_not_zero():
    """An unmeasurable spread must not read as a perfect one.

    Zero spread is the strongest result this probe can report. If an
    unmeasurable file also produced 0.0, the best and the worst outcome would
    print identically.
    """
    assert probe.spread([]) == -1.0
    assert probe.spread(["", None]) == -1.0
    assert probe.spread([15000]) == 0.0


def test_spread_ignores_blanks_but_keeps_the_numbers():
    assert probe.spread([15000, "", 15250, None]) == 250.0
    assert probe.spread(["ECHEC", "x"]) == -1.0


def test_spread_does_not_count_booleans_as_numbers():
    """Booleans are not measurements.

    ``True`` is an int in Python, so a boolean leaking into a numeric column
    would silently widen or narrow a spread.
    """
    assert probe.spread([True, False]) == -1.0


# --------------------------------------------------------------------------
# Sharding must partition, not sample
# --------------------------------------------------------------------------


def test_shards_are_disjoint_and_cover_everything():
    files = [(Path(f"{i}.flac"), "positive" if i % 2 else "lawful") for i in range(20)]
    seen = []
    for spec in ("1/3", "2/3", "3/3"):
        seen.extend(probe.shard_files(files, *probe.parse_shard(spec)))
    assert sorted(p.name for p, _ in seen) == sorted(p.name for p, _ in files)
    assert len(seen) == len(files)


def test_each_shard_carries_both_populations():
    """Every shard must contain both populations.

    Stride, not blocks. The real file list is all positives then all lawful, so
    a block split would give one process only transcodes, and a shard that died
    would take a whole population with it.
    """
    files = [(Path(f"p{i}.flac"), "positive") for i in range(9)]
    files += [(Path(f"g{i}.flac"), "lawful") for i in range(9)]
    for spec in ("1/3", "2/3", "3/3"):
        shard = probe.shard_files(files, *probe.parse_shard(spec))
        assert {pop for _, pop in shard} == {"positive", "lawful"}, spec


def test_shard_one_of_one_is_everything():
    assert probe.parse_shard("1/1") == (1, 1)


# --------------------------------------------------------------------------
# THE ONE THAT MATTERS - the control must not conclude on an empty denominator
# --------------------------------------------------------------------------


def test_empty_lawful_pool_refuses_to_conclude_on_precision(capsys):
    """The defect this probe shipped with on its first run.

    With no lawful files at all it printed "the defect costs recall, never
    precision" — a reassuring sentence derived from zero observations. That is
    the fifth instance of the guard-that-guards-nothing pattern in this
    repository, and it is the reason this test exists.
    """
    rows = [row("positive", 0, "WARNING", 50, 15000)]
    probe.report(rows, Args())
    out = capsys.readouterr().out
    assert "CONTROLE NON EXECUTE" in out
    assert "coute du RAPPEL" not in out


def test_clean_lawful_pool_does_conclude(capsys):
    """With lawful windows present and none convicted, it must conclude.

    Otherwise the previous test would pass by making the probe say nothing ever.
    """
    rows = [
        row("positive", 0, "WARNING", 50, 15000, "p.flac"),
        row("lawful", 0, "AUTHENTIC", 0, 21000, "g.flac"),
        row("lawful", 661500, "AUTHENTIC", 0, 21000, "g.flac"),
    ]
    probe.report(rows, Args())
    out = capsys.readouterr().out
    assert "coute du RAPPEL" in out
    assert "CONTROLE NON EXECUTE" not in out


def test_a_convicted_lawful_window_stops_everything(capsys):
    """A lawful window convicted at any offset stops everything.

    The criterion written in advance: a false positive manufactured by moving
    the window is a precision defect and must be reported as one.
    """
    rows = [
        row("lawful", 0, "AUTHENTIC", 0, 21000, "g.flac"),
        row("lawful", 661500, probe.CONVICTION, 85, 15900, "g.flac"),
    ]
    probe.report(rows, Args())
    out = capsys.readouterr().out
    assert "defaut de PRECISION" in out
    assert "coute du RAPPEL" not in out


# --------------------------------------------------------------------------
# Address and magnitude are reported apart, and the reading follows the data
# --------------------------------------------------------------------------


def test_pinned_address_with_moving_verdict_is_named_a_threshold_problem(capsys):
    rows = [
        row("positive", 0, "AUTHENTIC", 0, 15000, "p.flac"),
        row("positive", 661500, "WARNING", 50, 15020, "p.flac"),
        row("lawful", 0, "AUTHENTIC", 0, 21000, "g.flac"),
    ]
    probe.report(rows, Args())
    out = capsys.readouterr().out
    assert "probleme de SEUIL" in out


def test_moving_address_is_named_as_such(capsys):
    rows = [
        row("positive", 0, "WARNING", 50, 15000, "p.flac"),
        row("positive", 661500, "WARNING", 50, 19000, "p.flac"),
        row("lawful", 0, "AUTHENTIC", 0, 21000, "g.flac"),
    ]
    probe.report(rows, Args())
    out = capsys.readouterr().out
    assert "l'adresse bouge" in out
    # The verdict never moved, so this must NOT be read as a threshold problem.
    assert "probleme de SEUIL" not in out


# --------------------------------------------------------------------------
# Selection must exclude short files loudly rather than fold them in
# --------------------------------------------------------------------------


def test_files_too_short_for_the_grid_are_excluded(tmp_path, capsys):
    make_flac(tmp_path / "long.flac", seconds=4.0, seed=3)
    make_flac(tmp_path / "short.flac", seconds=1.0, seed=4)
    kept = probe.collect(tmp_path, "positive", needed=int(2.0 * RATE))
    names = [p.name for p, _ in kept]
    assert names == ["long.flac"]
    assert "ecartes" in capsys.readouterr().out


# --------------------------------------------------------------------------
# A failing analysis is a result, not a crash and not a clean verdict
# --------------------------------------------------------------------------


class Exploding:
    def analyze_file(self, _path):
        raise RuntimeError("boom")


class Fixed:
    def __init__(self, payload):
        self.payload = payload

    def analyze_file(self, _path):
        return self.payload


def test_a_failed_analysis_is_recorded_not_swallowed():
    result = probe.score(Exploding(), Path("x.flac"))
    assert result["verdict"] == "ECHEC:RuntimeError"
    assert result["score"] == ""
    assert result["cutoff_hz"] == ""
    assert result["verdict"] not in probe.SIGNALED


def test_missing_fields_do_not_become_a_verdict():
    """An analyzer returning an empty dict must read as unknown, never as clean."""
    result = probe.score(Fixed({}), Path("x.flac"))
    assert result["verdict"] == "?"
    assert result["verdict"] != "AUTHENTIC"


def test_evidence_families_are_carried_through():
    payload = {
        "verdict": "WARNING",
        "score": 50,
        "cutoff_freq": 15000,
        "evidence_families": ["spectral", "temporal"],
    }
    assert probe.score(Fixed(payload), Path("x.flac"))["families"] == "spectral|temporal"


# --------------------------------------------------------------------------
# The fine grid must actually span one frame
# --------------------------------------------------------------------------


def test_fine_grid_walks_exactly_one_mp3_frame():
    assert probe.FINE_OFFSETS_SAMPLES[0] == 0
    assert probe.FINE_OFFSETS_SAMPLES[-1] == probe.MP3_FRAME_SAMPLES == 1152
    steps = {b - a for a, b in zip(probe.FINE_OFFSETS_SAMPLES, probe.FINE_OFFSETS_SAMPLES[1:])}
    assert steps == {probe.MP3_FRAME_SAMPLES // 8}


def test_coarse_grid_is_strictly_increasing_and_starts_at_zero():
    assert probe.COARSE_OFFSETS_S[0] == 0.0
    assert list(probe.COARSE_OFFSETS_S) == sorted(set(probe.COARSE_OFFSETS_S))


@pytest.mark.parametrize("bad", ["0/3", "4/3", "-1/2", "3", "", "a/3", "1/0", "1/b", "/3"])
def test_invalid_shard_is_refused(bad):
    """Every malformed shard spec must raise rather than fall back.

    A misparsed shard still runs, still writes a CSV, and silently covers the
    wrong files.
    """
    with pytest.raises(ValueError):
        probe.parse_shard(bad)
