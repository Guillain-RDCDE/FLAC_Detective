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

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.analyzer import FLACAnalyzer  # noqa: E402

# Containers libsndfile can write, so the test needs no external tool. ALAC needs
# ffmpeg and is added when it is there — it belongs in this matrix, because it is
# the container that showed the reporter the pattern was compression and not
# libsndfile: ALAC sided with FLAC, and libsndfile cannot read ALAC at all.
CONTAINERS = (("FLAC", ".flac"), ("WAV", ".wav"), ("AIFF", ".aiff"))
SAMPLE_RATE = 44_100

_HAVE_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


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


def _reported_signal(seconds: float = 70.0) -> np.ndarray:
    """The shape that actually reproduces issue #7, rather than merely resembling it.

    ``_signal`` above is quiet, short and spectrally bare: every container takes
    the authentic fast path on it and agrees, so a test built on it alone passes
    green while the engine is broken. It agrees because nothing was consulted.

    This one is calibrated to land on the rules that carry the container
    dependency, which took measuring rather than guessing:

    * a wall at ~19.15 kHz -> a detected cutoff of 19,250 Hz, which sits in BOTH
      Rule 1's 256 kbps cell (18.5-19.5 kHz) and Rule 7's ambiguous zone
      (19-21.5 kHz), the only overlap where both can speak;
    * spectrally tilted, near-mono content, so the FLAC lands at ~819 kbps —
      inside Rule 1's 600-850 kbps window for that cell, where a WAV's 1411 kbps
      is not;
    * a residual floor around -47 dB (shallower than the -55 dB bar), so the
      "uninformative container" bypass does not hand the WAV back the evidence
      by another door;
    * three real silent gaps carrying dither, because Rule 7 returns NO_SILENCE
      and votes on nothing without them.

    Before the fix this file read WARNING 33/150 as FLAC and ALAC and AUTHENTIC
    3/150 as WAV and AIFF, from bit-identical samples.
    """
    rng = np.random.default_rng(20260904)
    n = int(SAMPLE_RATE * seconds)
    t = np.arange(n) / SAMPLE_RATE

    music = np.zeros((n, 2))
    for freq, amp in (
        (110, 0.30),
        (165, 0.22),
        (220, 0.20),
        (330, 0.14),
        (440, 0.11),
        (660, 0.08),
        (880, 0.06),
        (1320, 0.045),
        (2200, 0.03),
        (3300, 0.02),
        (5500, 0.012),
        (8800, 0.008),
        (13200, 0.005),
    ):
        env = 0.6 + 0.4 * np.sin(2 * np.pi * 0.37 * t + freq % 7)
        music += (amp * env * np.sin(2 * np.pi * freq * t))[:, None]

    spectrum = np.fft.rfft(music, axis=0)
    freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)

    # Tilted, almost-mono noise: the tilt is what brings a FLAC down to a
    # music-like bitrate (white noise costs ~1180 kbps and never enters Rule 1's
    # window at all), the shared component is what fine-tunes it into the cell.
    correlation = 0.9998
    common = rng.normal(0.0, 0.25, size=(n, 1))
    independent = rng.normal(0.0, 0.25, size=(n, 2))
    noise = correlation * common + np.sqrt(1.0 - correlation**2) * independent
    tilt = (200.0 / np.maximum(freqs, 200.0)) ** 0.6
    tilt = np.maximum(tilt, (200.0 / 3000.0) ** 0.6)  # plateau above 3 kHz
    spectrum += np.fft.rfft(noise, axis=0) * tilt[:, None]

    spectrum[freqs > 19_150.0] = 0.0
    audio = np.fft.irfft(spectrum, n=n, axis=0)
    audio *= 0.45 / np.max(np.abs(audio))

    for start, end in ((12.0, 13.2), (28.0, 29.4), (46.0, 47.6)):
        lo, hi = int(start * SAMPLE_RATE), int(end * SAMPLE_RATE)
        audio[lo:hi] = rng.normal(0.0, 0.0016, size=(hi - lo, 2))  # ~ -56 dBFS

    return np.clip(np.round(audio * 32767), -32768, 32767).astype(np.int16)


def _write_containers(folder: Path, samples: np.ndarray, stem: str) -> dict:
    """Write the same samples into every container this machine can produce."""
    paths = {}
    for fmt, suffix in CONTAINERS:
        path = folder / f"{stem}{suffix}"
        sf.write(str(path), samples, SAMPLE_RATE, subtype="PCM_16", format=fmt)
        paths[fmt] = path
    if _HAVE_FFMPEG:
        alac = folder / f"{stem}.m4a"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(paths["WAV"]),
                "-c:a",
                "alac",
                str(alac),
            ],
            check=True,
            timeout=300,
        )
        paths["ALAC"] = alac
    return paths


@pytest.fixture(scope="module")
def containers(tmp_path_factory):
    """The same 16-bit samples written into each container."""
    folder = tmp_path_factory.mktemp("containers")
    return _write_containers(folder, _signal(), "same")


@pytest.fixture(scope="module")
def reported_containers(tmp_path_factory):
    """The issue #7 shape, in every container."""
    folder = tmp_path_factory.mktemp("containers_issue7")
    return _write_containers(folder, _reported_signal(), "issue7")


@pytest.fixture(scope="module")
def results(containers):
    """Analysed once, on purpose.

    Module-scoped because this file asks several different questions of the same
    run, and re-analysing per test buys nothing but minutes.
    """
    return _analyse_all(containers)


@pytest.fixture(scope="module")
def reported_results(reported_containers):
    return _analyse_all(reported_containers)


@pytest.fixture(scope="module")
def reported_results_default(reported_containers):
    """The same matrix in the mode people actually run.

    ``--deep`` bypasses the authentic fast path by design, so it hides the half of
    this defect that lives in that path: under deep the four containers disagreed
    only about which witnesses they had heard, while under the default they
    disagreed about the verdict itself — WARNING 33/150 against AUTHENTIC 3/150.
    A container-independence test that only ever runs deep is testing the mode the
    bug does not live in.
    """
    return _analyse_all(reported_containers, deep=False)


def _samples_of(fmt: str, path: Path) -> np.ndarray:
    """Read a container's samples, going through ffmpeg for the one libsndfile can't."""
    if fmt != "ALAC":
        return sf.read(str(path), always_2d=True, dtype="int16")[0]
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-"],
        check=True,
        capture_output=True,
        timeout=300,
    ).stdout
    return np.frombuffer(raw, dtype="<i2").reshape(-1, 2)


def _check_same_samples(paths: dict) -> None:
    """The premise, checked rather than assumed — and checked as READ.

    An `-f s16le` hash would pass here even if one file were 24-bit. Comparing
    the arrays soundfile returns is what distinguishes a container difference
    from a bit-depth difference, and that distinction is the whole subject.
    """
    reference = None
    subtypes = []
    for fmt, path in paths.items():
        data = _samples_of(fmt, path)
        if fmt != "ALAC":
            info = sf.info(str(path))
            assert info.samplerate == SAMPLE_RATE, fmt
            subtypes.append(info.subtype)
        if reference is None:
            reference = data
        else:
            assert np.array_equal(reference, data), f"{fmt} ne porte pas les memes samples"
    assert len(set(subtypes)) == 1, f"les conteneurs n'ont pas la meme profondeur: {subtypes}"


def _analyse_all(paths: dict, deep: bool = True) -> dict:
    analyzer = FLACAnalyzer(deep=deep)
    return {fmt: analyzer.analyze_file(str(path)) for fmt, path in paths.items()}


def _check_agreement(results: dict) -> None:
    for label, key in (
        ("le verdict", "verdict"),
        ("le score", "score"),
        ("la coupure", "cutoff_freq"),
    ):
        seen = {fmt: r.get(key) for fmt, r in results.items()}
        assert len(set(seen.values())) == 1, f"{label} depend du conteneur: {seen}"

    families = {fmt: tuple(sorted(r.get("evidence_families") or [])) for fmt, r in results.items()}
    assert len(set(families.values())) == 1, f"les temoins different: {families}"


def test_the_fixtures_really_hold_the_same_samples(containers):
    _check_same_samples(containers)


def test_the_verdict_does_not_depend_on_the_container(results):
    """Issue #7's property: same samples, same verdict, whatever the wrapper.

    ``_check_agreement`` compares the evidence families too: a verdict can match
    while the reasoning behind it does not, and two containers agreeing on
    AUTHENTIC for different reasons would still be a container dependency, hidden
    one layer down.
    """
    _check_agreement(results)


def test_the_reported_fixtures_really_hold_the_same_samples(reported_containers):
    _check_same_samples(reported_containers)


def test_the_reported_case_does_not_depend_on_the_container(reported_results):
    """The same property, on audio the rules actually judge.

    This is the assertion that fails on the code as it stood when the issue was
    filed: WARNING 33/150 for FLAC and ALAC, AUTHENTIC 3/150 for WAV and AIFF.
    """
    _check_agreement(reported_results)


def test_the_reported_case_does_not_depend_on_the_container_by_default(
    reported_results_default,
):
    """And in default mode, which is where the fast path can still acquit."""
    _check_agreement(reported_results_default)


def test_the_default_mode_does_not_acquit_by_container(reported_results_default):
    """No container may leave by the fast path while another gets judged.

    This is the defect in its own words. The fast path returns AUTHENTIC without
    running rules 7, 10, 12, 13, 14 or 15; before the fix the two uncompressed
    containers took it and the two compressed ones did not, so a WAV was not
    cleared, it was never examined. Whatever the verdict, the four have to have
    been asked the same questions.
    """
    fast = {
        fmt: "Fast analysis" in (r.get("reason") or "")
        for fmt, r in reported_results_default.items()
    }
    assert len(set(fast.values())) == 1, f"le chemin rapide depend du conteneur: {fast}"


def test_the_reported_case_is_not_vacuous(reported_results):
    """Guard against the way this whole test file could pass while lying.

    Agreement is cheap if nothing was consulted: silence every container and the
    matrix goes green. So the fixture has to earn its place — it must reach a
    verdict other than AUTHENTIC, and it must get there through the expensive
    rules rather than the fast path, in EVERY container. If a future change makes
    the fast path swallow this file again, that is the regression, and this is the
    assertion that catches it — not the ones above.
    """
    for fmt, result in reported_results.items():
        assert result.get("verdict") != "AUTHENTIC", (
            f"{fmt}: la fixture ne declenche plus rien, le test ne prouve plus rien "
            f"({result.get('score')}/150, {result.get('reason')})"
        )
        assert "Fast analysis" not in (
            result.get("reason") or ""
        ), f"{fmt}: sorti par le chemin rapide, les regles couteuses n'ont pas tourne"


@pytest.mark.skipif(not _HAVE_FFMPEG, reason="ffmpeg absent: pas d'ALAC a comparer")
def test_alac_is_in_the_matrix(reported_containers):
    """ALAC is the container that told the reporter it was compression, not libsndfile.

    libsndfile cannot open ALAC at all, so it takes a different reader — and it
    still sided with FLAC against WAV and AIFF. That is what ruled the reader out
    and pointed at the compression ratio. A matrix without it can be read as a
    libsndfile quirk.
    """
    assert "ALAC" in reported_containers
