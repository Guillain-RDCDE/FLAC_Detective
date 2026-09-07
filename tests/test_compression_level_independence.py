"""The same samples at any FLAC compression level must give the same verdict.

Issue #8: one track stored at levels 0 to 3 scored 13, and the same track stored
at levels 4 to 8 scored 63 — AUTHENTIC against FAKE, from bit-identical audio.
Re-saving the level-8 file at level 0 brought the 13 back, which is the reporter
showing, before anyone asked, that the encoder was not the thing that changed.

It is issue #7 in a different coat. Rule 1's container check read the size of the
FILE and called it the bitrate of the AUDIO; a WAV then answered 1411 kbps for any
samples, and a FLAC answered whatever its ripper's level made it. From level 0
to level 8 the file shrinks by 4 to 19 % (mean 11 %) — measured on 24
exchange-set files with flac 1.5.0, not assumed — most of it in the one step
where the encoder starts using linear prediction, while Rule 1's windows are
50 kbps wide. The reporter's file sat on an edge.

The cure is the one 1.13.10 already carried: size the audio by re-encoding it at
ONE fixed level, whatever it arrived in. These tests pin that property from the
compression-level side, so it cannot regress unnoticed the way it once did.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from test_container_independence import SAMPLE_RATE, _reported_signal  # noqa: E402

import flac_detective.analysis.analyzer as analyzer_module  # noqa: E402
from flac_detective.analysis.analyzer import FLACAnalyzer  # noqa: E402
from flac_detective.analysis.audio_formats import flac_equivalent_size  # noqa: E402

# libsndfile takes the level as a fraction of the encoder's 0-8 scale.
LEVELS = (0, 3, 5, 8)


def _signal() -> np.ndarray:
    """Issue #7's shape with its three silent gaps filled in.

    Calibrated rather than guessed, again. The reported signal lands in Rule 1's
    256 kbps cell at ~812 kbps when stored at level 8 and outside it at ~1065 kbps
    at level 0 — the reporter's situation exactly. But its silent gaps also wake
    Rule 7, whose −50 for clean silence cancels Rule 1's +50 to the point, so a
    file-size ruler and a one-ruler engine both read AUTHENTIC 3 at every level
    and the test proves nothing. With the gaps replaced by the music before them,
    Rule 7 has nothing to say and Rule 1's answer reaches the score: measured on
    a file-size ruler, AUTHENTIC 3 at levels 0 and 3 and WARNING 53 at 5 and 8.
    ``test_the_fixture_would_catch_a_file_size_ruler`` keeps that calibration
    honest.
    """
    samples = _reported_signal().copy()
    for start, end in ((12.0, 13.2), (28.0, 29.4), (46.0, 47.6)):
        lo, hi = int(start * SAMPLE_RATE), int(end * SAMPLE_RATE)
        samples[lo:hi] = samples[lo - (hi - lo) : lo]
    return samples


def _write_levels(folder: Path, samples: np.ndarray, stem: str, levels=LEVELS) -> dict:
    """The same samples written as FLAC at each compression level."""
    paths = {}
    for level in levels:
        path = folder / f"{stem}_L{level}.flac"
        with sf.SoundFile(
            str(path),
            mode="w",
            samplerate=SAMPLE_RATE,
            channels=samples.shape[1],
            format="FLAC",
            subtype="PCM_16",
            compression_level=level / 8.0,
        ) as dst:
            dst.write(samples)
        paths[level] = path
    return paths


@pytest.fixture(scope="module")
def levels(tmp_path_factory):
    """The shape Rule 1 actually consults, at four levels."""
    folder = tmp_path_factory.mktemp("levels_issue8")
    return _write_levels(folder, _signal(), "issue8")


def _analyse_all(paths: dict) -> dict:
    """In the mode people actually run: the reporter did not pass --deep."""
    analyzer = FLACAnalyzer(deep=False)
    return {level: analyzer.analyze_file(str(path)) for level, path in paths.items()}


@pytest.fixture(scope="module")
def results(levels):
    """Analysed once."""
    return _analyse_all(levels)


def _verdicts(results: dict) -> dict:
    return {level: (r.get("verdict"), r.get("score")) for level, r in results.items()}


def test_the_fixtures_really_differ_on_disk_and_agree_as_audio(levels):
    """The premise, checked: different bytes, identical samples.

    If libsndfile ever ignored ``compression_level`` every file would be the
    same size and the tests below would pass without testing anything.
    """
    sizes = {level: path.stat().st_size for level, path in levels.items()}
    assert len(set(sizes.values())) > 1, f"les niveaux n'ont pas change la taille: {sizes}"
    reference = None
    for path in levels.values():
        data = sf.read(str(path), always_2d=True, dtype="int16")[0]
        if reference is None:
            reference = data
        else:
            assert np.array_equal(reference, data)


def test_the_measured_size_does_not_depend_on_the_level(levels):
    """One ruler: the re-encoded size is a property of the samples alone."""
    measured = {level: flac_equivalent_size(path) for level, path in levels.items()}
    assert None not in measured.values(), measured
    assert len(set(measured.values())) == 1, f"la taille mesuree suit le niveau: {measured}"


def test_the_verdict_does_not_depend_on_the_level(results):
    """Issue #8's property: same samples, same verdict, whatever the level."""
    for label, key in (
        ("le verdict", "verdict"),
        ("le score", "score"),
        ("la coupure", "cutoff_freq"),
    ):
        seen = {level: r.get(key) for level, r in results.items()}
        assert len(set(seen.values())) == 1, f"{label} depend du niveau: {seen}"

    families = {lvl: tuple(sorted(r.get("evidence_families") or [])) for lvl, r in results.items()}
    assert len(set(families.values())) == 1, f"les temoins different: {families}"


def test_the_fixture_would_catch_a_file_size_ruler(levels, monkeypatch):
    """The negative control: put the old ruler back and the verdict must move.

    A level-independence test that passes on a fixture Rule 1 never consults is
    green on broken code. So the sizer is replaced, for this test only, by the
    file's own size on disk — which is what 1.13.9 did for FLAC input, and what
    1.13.8 did for everything — and the same four files must then disagree.
    Measured when this was written: AUTHENTIC 3 at levels 0 and 3, WARNING 53 at
    levels 5 and 8. If this test ever passes vacuously the fixture has drifted
    out of Rule 1's cell and the two tests above are no longer testing anything.
    """
    monkeypatch.setattr(analyzer_module, "flac_equivalent_size", lambda path: path.stat().st_size)
    seen = _verdicts(_analyse_all(levels))
    assert len(set(seen.values())) > 1, f"le fixture ne discrimine plus: {seen}"
