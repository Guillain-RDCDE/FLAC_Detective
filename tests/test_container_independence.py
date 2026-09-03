"""Identical samples in different lossless containers must give an identical verdict.

Asked for in issue #7: a report that the same audio read SUSPICIOUS as FLAC and
ALAC but AUTHENTIC as WAV and AIFF, with the decoded PCM verified identical by
``ffmpeg -f s16le | sha256sum``.

The property is worth pinning whatever the outcome of that report. A verdict that
changes with the wrapper is a verdict about the wrapper, and the engine claims to
read audio.

One warning, learned by falling into it while investigating that issue. An
`-f s16le` hash converts to 16 bits before hashing, so it **cannot distinguish a
24-bit file from its own 16-bit truncation** — which is precisely the pair you
get when the WAV was made from the FLAC. Measured: a 24-bit FLAC and the 16-bit
WAV derived from it hash identically under that check, while the engine reads
them as different audio, because truncating eight bits is not nothing. (Two files
whose 24-bit content is unrelated do hash differently, so the check is not blind
in general — only to the case that matters here.)

Reproducing the report that way produced a container "difference" that was
entirely bit depth, and the first root cause found was wrong. So these fixtures
assert the sample arrays are equal AS READ, and that the subtypes match, which is
the check that would have caught it.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.analyzer import FLACAnalyzer  # noqa: E402

# Containers libsndfile can write, so the test needs no external tool. ALAC is
# excluded for that reason and not because it is uninteresting.
CONTAINERS = (("FLAC", ".flac"), ("WAV", ".wav"), ("AIFF", ".aiff"))
SAMPLE_RATE = 44_100


def _signal(seconds: float = 6.0) -> np.ndarray:
    """Deterministic stereo audio with a spectral edge, silence and dither.

    Shaped to give the rules something to read: a tone pair, a band-limited noise
    floor, and two seconds of near-silence, which is what the silence rule wants.
    """
    rng = np.random.default_rng(20260903)
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n) / SAMPLE_RATE
    left = 0.20 * np.sin(2 * np.pi * 440.0 * t) + 0.05 * np.sin(2 * np.pi * 6_000.0 * t)
    right = 0.18 * np.sin(2 * np.pi * 441.5 * t) + 0.04 * np.sin(2 * np.pi * 9_000.0 * t)
    noise = rng.normal(0.0, 0.0015, size=(n, 2))
    audio = np.stack([left, right], axis=1) + noise
    quiet = slice(int(SAMPLE_RATE * 2.0), int(SAMPLE_RATE * 4.0))
    audio[quiet] *= 0.0008
    # Quantise once, so every container stores exactly the same 16-bit samples.
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


@pytest.fixture(scope="module")
def containers(tmp_path_factory):
    """The same 16-bit samples written into each container."""
    folder = tmp_path_factory.mktemp("containers")
    samples = _signal()
    paths = {}
    for fmt, suffix in CONTAINERS:
        path = folder / f"same{suffix}"
        sf.write(str(path), samples, SAMPLE_RATE, subtype="PCM_16", format=fmt)
        paths[fmt] = path
    return paths


def test_the_fixtures_really_hold_the_same_samples(containers):
    """The premise, checked rather than assumed — and checked as READ.

    An `-f s16le` hash would pass here even if one file were 24-bit. Comparing
    the arrays soundfile returns is what distinguishes a container difference
    from a bit-depth difference, and that distinction is the whole subject.
    """
    arrays, subtypes = [], []
    for fmt, path in containers.items():
        data, rate = sf.read(str(path), always_2d=True, dtype="int16")
        assert rate == SAMPLE_RATE, fmt
        arrays.append(data)
        subtypes.append(sf.info(str(path)).subtype)
    assert len(set(subtypes)) == 1, f"les conteneurs n'ont pas la meme profondeur: {subtypes}"
    for other in arrays[1:]:
        assert np.array_equal(arrays[0], other)


def test_the_verdict_does_not_depend_on_the_container(containers):
    """Issue #7's property: same samples, same verdict, whatever the wrapper."""
    analyzer = FLACAnalyzer(deep=True)
    results = {fmt: analyzer.analyze_file(str(path)) for fmt, path in containers.items()}

    verdicts = {fmt: r.get("verdict") for fmt, r in results.items()}
    assert len(set(verdicts.values())) == 1, f"le verdict depend du conteneur: {verdicts}"

    scores = {fmt: r.get("score") for fmt, r in results.items()}
    assert len(set(scores.values())) == 1, f"le score depend du conteneur: {scores}"

    cutoffs = {fmt: r.get("cutoff_freq") for fmt, r in results.items()}
    assert len(set(cutoffs.values())) == 1, f"la coupure depend du conteneur: {cutoffs}"


def test_the_evidence_families_do_not_depend_on_the_container(containers):
    """A verdict can match while the reasoning behind it does not.

    Two containers agreeing on AUTHENTIC for different reasons would still be a
    container dependency, hidden one layer down, so the witnesses are compared
    too.
    """
    analyzer = FLACAnalyzer(deep=True)
    families = {
        fmt: tuple(sorted(analyzer.analyze_file(str(path)).get("evidence_families") or []))
        for fmt, path in containers.items()
    }
    assert len(set(families.values())) == 1, f"les temoins different: {families}"
