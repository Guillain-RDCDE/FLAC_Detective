"""``detect_cutoff_detailed``: a sentinel that says "I found nothing", and a width.

Why these tests exist
---------------------
``detect_cutoff`` returns Nyquist in three unrelated situations — the spectrum
genuinely reaches the top, the energy is concentrated in the bass, and nothing was
found at all. A caller cannot tell a measurement from a shrug, and our own Musepack
arm published medians that silently included one file reading 22,050 Hz at every
profile, including one where a 15.8 kHz bandwidth cap certainly applies.

That is the mono-gate lesson from Rule 15, unapplied: the correct behaviour when an
instrument cannot decide is silence, not a number, because a number is still an
opinion.

These use synthetic signals with known answers rather than corpus files. A corpus
test would tell us what the statistic does on our music; this tells us the statistic
does what it says, which is the part that must not silently change.
"""

from __future__ import annotations

import numpy as np
import pytest

from flac_detective.analysis.spectrum import _welch_magnitude_db, detect_cutoff_detailed

RATE = 44100
SECONDS = 5


def _noise(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 0.1, RATE * SECONDS)


def _spectrum(signal: np.ndarray):
    freq, magnitude_db = _welch_magnitude_db(signal.astype(np.float64), RATE)
    assert freq is not None and magnitude_db is not None
    return freq, magnitude_db


def _brickwall(cut_hz: float, seed: int = 0) -> np.ndarray:
    """White noise with everything above ``cut_hz`` set to exactly zero."""
    signal = _noise(seed)
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1 / RATE)
    spectrum[freqs > cut_hz] = 0
    return np.fft.irfft(spectrum, n=len(signal))


def _rolloff(start_hz: float, decay_hz: float, seed: int = 0) -> np.ndarray:
    """White noise fading exponentially above ``start_hz`` — a slope, not a wall."""
    signal = _noise(seed)
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(len(signal), 1 / RATE)
    above = freqs > start_hz
    spectrum[above] *= 10 ** (-(freqs[above] - start_hz) / decay_hz)
    return np.fft.irfft(spectrum, n=len(signal))


def test_a_full_band_signal_reports_no_edge_found():
    """The sentinel. Broadband noise has no wall, and must not be given a width."""
    reading = detect_cutoff_detailed(*_spectrum(_noise()), RATE)
    assert np.isnan(reading.width_hz), (
        "a signal with no wall must not receive a transition width; a width here "
        f"would be measuring the music. got {reading}"
    )


def test_a_brickwall_is_found_and_measured_at_its_own_frequency():
    reading = detect_cutoff_detailed(*_spectrum(_brickwall(19000.0)), RATE)
    assert reading.found, f"a hard wall at 19 kHz must be found, got {reading}"
    assert (
        abs(reading.cutoff_hz - 19000.0) < 600.0
    ), f"edge reported at {reading.cutoff_hz:.0f} Hz for a wall at 19,000 Hz"
    assert np.isfinite(reading.width_hz)


def test_a_wall_reads_narrower_than_a_rolloff():
    """The whole point of the statistic, and the only property a rule could use.

    Absolute values are instrument-specific and deliberately not asserted — Provir's
    equivalent reads 390-519 Hz on their MP3 positives with different smoothing and a
    different reference band, and importing that number would be exactly the mistake
    both projects have now made once each. What must hold is the ORDER.
    """
    wall = detect_cutoff_detailed(*_spectrum(_brickwall(19000.0)), RATE)
    slope = detect_cutoff_detailed(*_spectrum(_rolloff(15000.0, 4000.0)), RATE)
    assert np.isfinite(wall.width_hz) and np.isfinite(slope.width_hz)
    assert wall.width_hz < slope.width_hz, (
        "a brickwall must read narrower than a gradual rolloff, otherwise the "
        f"statistic is not measuring steepness. wall={wall.width_hz:.0f} Hz "
        f"slope={slope.width_hz:.0f} Hz"
    )


@pytest.mark.parametrize("cut_hz", [17000.0, 19000.0, 20500.0])
def test_width_does_not_drift_with_where_the_wall_sits(cut_hz: float):
    """A wall is a wall. If width tracked frequency it would just be the edge again.

    This is what makes the statistic independent of the quantity Provir retracted:
    edge POSITION does not separate lawful masters from transcodes — both
    populations live on both sides of every line — so a width that moved with
    position would inherit exactly that failure.
    """
    reading = detect_cutoff_detailed(*_spectrum(_brickwall(cut_hz)), RATE)
    assert np.isfinite(reading.width_hz)
    # 50 Hz, not 1000. The first version of this test asserted < 1000 and passed
    # while the statistic was reading its own 269 Hz smoothing kernel rather than the
    # signal — a bound loose enough to hold under the defect it was supposed to
    # catch. An ideal step convolved with a 24 Hz kernel cannot exceed a few tens of
    # Hz, so that is what gets asserted.
    assert reading.width_hz < 50.0, (
        f"a hard wall at {cut_hz:.0f} Hz read a width of {reading.width_hz:.0f} Hz. "
        "A step function should measure at roughly the smoothing kernel's own span; "
        "anything wider means the width is following the spectrum, not the transition"
    )


def test_the_sentinel_and_the_cutoff_disagree_on_purpose():
    """``found=False`` still carries a cutoff, and callers must not read it as one.

    Kept as a test because the tuple invites exactly that mistake, and the Musepack
    arm made it: it averaged Nyquist-on-failure into a published median.
    """
    reading = detect_cutoff_detailed(*_spectrum(_noise()), RATE)
    if not reading.found:
        assert np.isnan(
            reading.width_hz
        ), "when no edge was found there is nothing to measure the width of"
