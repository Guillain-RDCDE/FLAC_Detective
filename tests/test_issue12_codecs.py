"""Issue #12 — the readings Rule 13 could not take, Rule 17 (SBR) and Rule 18 (side step).

Pinned here:

* the new MDCT is the transform Rule 13 already uses (TDAC fold + DCT-IV against
  the basis of ``mdct.mdct_basis``), and the held local median is the running one
  when evaluated at every bin;
* real Vorbis and Opus round trips (libsndfile's own encoders) show their grid,
  untouched audio does not, and the CELT reading survives a 48 -> 44.1 kHz trip;
* a high band that is a frequency-shifted copy reads as replication, and music
  without one does not;
* a side channel that stops at a frequency reads as a step, an ordinary stereo
  image and a mono file do not;
* the two rules' contracts: Rule 17 scores in two tiers and is its own family,
  Rule 18 scores nothing and testifies for ``stereo``;
* the calculator: Rule 17 withdraws Rule 8's protection, and the fast path does
  not acquit a file Rule 17 reads.

Every test fails on the 2.0.0 tree, where none of these modules exist.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from scipy.ndimage import median_filter
from scipy.signal import butter, hilbert, resample_poly, sosfiltfilt

from flac_detective.analysis.new_scoring.codec_grids import (
    celt_ratio,
    local_median,
    mdct_magnitudes,
    vorbis_switch_ratio,
)
from flac_detective.analysis.new_scoring.constants import CONVICTION_MIN_SCORE
from flac_detective.analysis.new_scoring.evidence import (
    POINTLESS_WITNESS_RULES,
    RULE_FAMILY,
    evidence_families,
)
from flac_detective.analysis.new_scoring.joint_stereo import side_step
from flac_detective.analysis.new_scoring.mdct import mdct_basis
from flac_detective.analysis.new_scoring.rules.joint_stereo_step import (
    STEP_BAR_DB,
    apply_rule_18_side_step,
)
from flac_detective.analysis.new_scoring.rules.mdct_alignment import (
    CELT_HARD,
    VORBIS_SWITCH_HARD,
    VORBIS_SWITCH_REVIEW,
)
from flac_detective.analysis.new_scoring.rules.sbr_replication import (
    COHERENCE_HARD,
    COHERENCE_REVIEW,
    SCORE_HARD,
    apply_rule_17_sbr_replication,
)
from flac_detective.analysis.new_scoring.sbr import replication_coherence
from flac_detective.analysis.new_scoring.verdict import determine_verdict

SR = 44100
_OGG = "OGG" in sf.available_formats()


def _shape(n: int, rate: int) -> np.ndarray:
    f = np.fft.rfftfreq(n, 1 / rate)
    return 1 / np.sqrt(np.maximum(f, 50) / 50)


@lru_cache(maxsize=None)
def _music_like(rate: int = SR, seconds: float = 10.0, seed: int = 3) -> np.ndarray:
    """Pink-ish stereo noise, a slow envelope and decaying hits, so a coder has work to do."""
    rng = np.random.default_rng(seed)
    n = int(rate * seconds)
    shape = _shape(n, rate)
    x = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)
    x = x / np.abs(x).max() * 0.5
    x *= 0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 0.7 * np.arange(n) / rate))
    hits = np.zeros(n)
    hits[:: int(rate * 0.37)] = 1.0
    x += np.convolve(hits, np.exp(-np.arange(400) / 40) * rng.standard_normal(400) * 0.4, "same")
    other = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)
    y = 0.9 * np.roll(x, 37) + 0.15 * other / np.abs(other).max()
    out = np.stack([x, y], axis=1).astype(np.float32)
    out.setflags(write=False)
    return out


def _round_trip(tmp_path: Path, audio: np.ndarray, rate: int, subtype: str) -> np.ndarray:
    """Encode with libsndfile's own encoder and decode back.

    Written in blocks: libsndfile's Vorbis writer crashes the process on one long
    write under Windows.
    """
    path = tmp_path / f"x.{subtype.lower()}.ogg"
    with sf.SoundFile(
        str(path), "w", rate, audio.shape[1], format="OGG", subtype=subtype, compression_level=0.5
    ) as fh:
        for i in range(0, len(audio), 4096):
            fh.write(audio[i : i + 4096])
    decoded, _ = sf.read(str(path), dtype="float32", always_2d=True)
    return decoded


class TestTheTransform:
    def test_dct4_mdct_is_rule_13s_mdct(self):
        rng = np.random.default_rng(0)
        blocks = rng.standard_normal((8, 2048))
        basis = mdct_basis(SR, (2000.0, 16000.0))
        reference = np.abs(blocks @ basis.astype(np.float64))
        ours = mdct_magnitudes(blocks, SR, (2000.0, 16000.0))
        assert ours.shape == reference.shape
        assert np.allclose(ours, reference, rtol=1e-4, atol=1e-6 * reference.std())

    def test_held_median_at_every_bin_is_the_running_median(self):
        spec = np.abs(np.random.default_rng(1).standard_normal((4, 300)))
        expected = median_filter(spec, size=(1, 33), mode="nearest")
        assert np.allclose(local_median(spec, 33, 1), expected)


class TestTheGrids:
    def test_untouched_audio_reads_under_both_review_bars(self):
        audio = _music_like()
        assert vorbis_switch_ratio(audio, SR)[0] < VORBIS_SWITCH_REVIEW
        assert celt_ratio(audio.mean(axis=1), SR)[0] < 2.0

    @pytest.mark.skipif(not _OGG, reason="libsndfile built without OGG support")
    def test_a_vorbis_round_trip_shows_its_grid(self, tmp_path):
        decoded = _round_trip(tmp_path, _music_like(), SR, "VORBIS")
        ratio, residue = vorbis_switch_ratio(decoded, SR)
        assert ratio >= VORBIS_SWITCH_HARD
        assert 0 <= residue < 128

    @pytest.mark.skipif(not _OGG, reason="libsndfile built without OGG support")
    def test_an_opus_round_trip_shows_its_grid_at_48k_and_after_44k1(self, tmp_path):
        decoded = _round_trip(tmp_path, _music_like(48000), 48000, "OPUS")
        assert celt_ratio(decoded.mean(axis=1), 48000)[0] >= CELT_HARD
        at_44k1 = resample_poly(decoded, 147, 160, axis=0).astype(np.float32)
        assert celt_ratio(at_44k1.mean(axis=1), SR)[0] >= CELT_HARD

    def test_too_short_or_unsupported_rate_is_nan(self):
        assert math.isnan(vorbis_switch_ratio(np.zeros((1000, 2), np.float32), SR)[0])
        assert math.isnan(celt_ratio(np.zeros(SR * 5, np.float32), 32000)[0])


@lru_cache(maxsize=None)
def _replicated(seconds: float = 10.0, shift_bands: int = 22) -> np.ndarray:
    """Low band kept, high band rebuilt as a copy of it shifted up by whole subbands."""
    mono = _music_like(seconds=seconds)[:, 0].astype(np.float64)
    low = sosfiltfilt(butter(8, 9000, "lowpass", fs=SR, output="sos"), mono)
    source = sosfiltfilt(butter(8, [2500, 9000], "bandpass", fs=SR, output="sos"), mono)
    shift_hz = shift_bands * SR / 128
    t = np.arange(len(mono)) / SR
    copy = np.real(hilbert(source) * np.exp(2j * np.pi * shift_hz * t))
    envelope = 0.4 + 0.2 * np.sin(2 * np.pi * 1.3 * t)
    out = low + copy * envelope
    return np.stack([out, out], axis=1).astype(np.float32)


class TestReplication:
    def test_a_shifted_copy_reads_as_replication(self):
        coherence, shift = replication_coherence(_replicated().mean(axis=1), SR)
        assert coherence >= COHERENCE_HARD
        assert shift == 22

    def test_music_without_a_copy_does_not(self):
        coherence, _ = replication_coherence(_music_like().mean(axis=1), SR)
        assert coherence < COHERENCE_REVIEW

    def test_rule_17_scores_hard_and_is_its_own_family(self):
        score, reasons, details = apply_rule_17_sbr_replication("x", 20000.0, _replicated(), SR)
        assert score == SCORE_HARD
        assert "R17" in reasons[0]
        assert details["sbr_coherence"] >= COHERENCE_HARD
        assert RULE_FAMILY["Rule17SBRReplication"] == "sbr"

    def test_rule_17_without_audio_is_silent(self):
        assert apply_rule_17_sbr_replication("x", 20000.0, None, None)[0] == 0


@lru_cache(maxsize=None)
def _stepped(seconds: float = 10.0, split_hz: float = 6000.0) -> np.ndarray:
    """Independent channels below ``split_hz``, one common signal above it."""
    rng = np.random.default_rng(7)
    n = int(SR * seconds)
    shape = _shape(n, SR)
    lo = butter(8, split_hz, "lowpass", fs=SR, output="sos")
    hi = butter(8, split_hz, "highpass", fs=SR, output="sos")

    def noise() -> np.ndarray:
        return np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)

    common = sosfiltfilt(hi, noise())
    left = sosfiltfilt(lo, noise()) + common
    right = sosfiltfilt(lo, noise()) + common
    stereo = np.stack([left, right], axis=1)
    return (stereo / np.abs(stereo).max() * 0.5).astype(np.float32)


class TestSideStep:
    def test_a_side_channel_that_stops_reads_as_a_step(self):
        step, split, _ = side_step(_stepped(), SR, 22050.0)
        assert step >= STEP_BAR_DB
        # The split reads within the three-band span the statistic compares.
        assert 5000.0 <= split <= 9000.0

    def test_an_ordinary_stereo_image_does_not(self):
        assert side_step(_music_like(), SR, 22050.0)[0] < STEP_BAR_DB

    def test_mono_abstains(self):
        mono = _music_like()[:, :1].repeat(2, axis=1)
        assert math.isnan(side_step(mono, SR, 22050.0)[0])

    def test_only_bands_under_the_cutoff_are_read(self):
        # Cut the stepped file at 5 kHz: the step at 6 kHz is above it and must vanish.
        step, _, _ = side_step(_stepped(), SR, 5000.0)
        assert math.isnan(step) or step < STEP_BAR_DB

    def test_rule_18_scores_nothing_and_testifies_for_stereo(self):
        score, reasons, details = apply_rule_18_side_step("x", 22050.0, _stepped(), SR)
        assert score == 0
        assert details["step_witness"] is True
        assert "no points" in reasons[0]
        assert POINTLESS_WITNESS_RULES["Rule18SideStep"] == "stereo"

    def test_a_lone_witness_cannot_convict_but_completes_a_corroboration(self):
        assert determine_verdict(140, families={"stereo"})[0] != "FAKE_CERTAIN"
        families = evidence_families({"Rule17SBRReplication": SCORE_HARD}, witnesses={"stereo"})
        assert determine_verdict(CONVICTION_MIN_SCORE, families)[0] == "FAKE_CERTAIN"


class TestTheCalculator:
    def _ctx(self, audio: np.ndarray, rule_scores: dict, cutoff: float = 20000.0):
        from flac_detective.analysis.new_scoring.models import (
            AudioMetadata,
            BitrateMetrics,
            ScoringContext,
        )

        ctx = ScoringContext(
            filepath=Path("x.flac"),
            audio_meta=AudioMetadata(sample_rate=SR, bit_depth=16, channels=2, duration=20.0),
            bitrate_metrics=BitrateMetrics(
                real_bitrate=900.0, apparent_bitrate=1411, variance=None
            ),
            cutoff_freq=cutoff,
        )
        for rule, points in rule_scores.items():
            ctx.rule_scores[rule] = points
            ctx.current_score += points
        ctx.audio_data = audio
        ctx.loaded_sample_rate = SR
        return ctx

    def test_rule_17_withdraws_rule_8s_protection(self):
        from flac_detective.analysis.new_scoring import calculator

        ctx = self._ctx(_replicated(), {"Rule8NyquistException": -30})
        calculator._run_rule_17(ctx)
        assert ctx.rule_scores["Rule17SBRReplication"] == SCORE_HARD
        assert ctx.current_score == SCORE_HARD
        assert any("R8 protection withdrawn" in r for r in ctx.reasons)

    def test_the_fast_path_does_not_acquit_a_replicated_file(self, monkeypatch):
        from flac_detective.analysis.new_scoring import calculator

        # The witnesses and the CNN are not what is under test; keep them out.
        monkeypatch.setattr(calculator, "_run_rules_14_and_15", lambda ctx: None)
        monkeypatch.setattr(calculator.Rule12MLClassifier, "apply", lambda self, ctx: None)
        monkeypatch.setattr(calculator, "_run_rule_16_if_decisive", lambda ctx: None)
        ctx = self._ctx(_replicated(), {})
        score, reasons = calculator._silent_heuristics_path(ctx, deep=False)
        assert score >= SCORE_HARD
        assert not any("Fast analysis" in r for r in reasons)

    def test_the_fast_path_still_acquits_untouched_audio(self, monkeypatch):
        from flac_detective.analysis.new_scoring import calculator

        ctx = self._ctx(_music_like(), {})
        score, reasons = calculator._silent_heuristics_path(ctx, deep=False)
        assert score == 0
        assert any("Fast analysis: AUTHENTIC" in r for r in reasons)
