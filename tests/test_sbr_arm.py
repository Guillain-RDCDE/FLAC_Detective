"""Gates for the SBR arm — an arm that quietly becomes a different arm.

``ml/sbr_arm.py`` exists to find out what this engine does with spectral band
replication, where energy above the cutoff is synthesised rather than recorded.
Its whole value depends on two claims about its own material: that the HE-AAC
encodes really are HE-AAC, and that they really do fill higher than a non-SBR
control. MediaFoundation picks the profile from the bitrate, so the first claim
can fail silently and turn the experiment into a second AAC-LC arm reporting a
comforting number about nothing.

So both guards are tested here for their ability to REFUSE, not merely to run.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

ML = Path(__file__).resolve().parent.parent / "ml"
sys.path.insert(0, str(ML))

import sbr_arm  # noqa: E402

RATE = 44100


def row(arm, verdict="AUTHENTIC", ceiling=20000, cutoff=20000, source="s.flac"):
    return {
        "source": source,
        "arm": arm,
        "profile": "",
        "ceiling_hz": ceiling,
        "verdict": verdict,
        "score": 0,
        "cutoff_hz": cutoff,
        "families": "",
    }


# --------------------------------------------------------------------------
# The ceiling reader must find a band limit that is actually there
# --------------------------------------------------------------------------


def test_ceiling_finds_a_known_band_limit(tmp_path):
    """A band-limited signal must read as band-limited.

    A synthetic signal with nothing high in the band must not read at Nyquist. A
    ceiling reader that always returned Nyquist would make every arm look
    identical and every guard pass.
    """
    seconds = 4
    t = np.arange(seconds * RATE) / RATE
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(t.size)
    # crude but sufficient band limit: cumulative moving average low-pass
    kernel = np.ones(11) / 11
    band_limited = np.convolve(noise, kernel, mode="same")
    for _ in range(6):
        band_limited = np.convolve(band_limited, kernel, mode="same")
    band_limited /= np.abs(band_limited).max()
    path = tmp_path / "limited.flac"
    sf.write(str(path), band_limited, RATE, subtype="PCM_16", format="FLAC")

    ceiling = sbr_arm.spectral_ceiling(path)
    assert 0 < ceiling < 12000, ceiling


def test_full_band_noise_reads_near_nyquist(tmp_path):
    """Full-band material must read near Nyquist.

    The same reader must not report a low ceiling here, or the previous test
    would pass by always answering "low".
    """
    rng = np.random.default_rng(1)
    data = rng.standard_normal(4 * RATE) * 0.2
    path = tmp_path / "full.flac"
    sf.write(str(path), data, RATE, subtype="PCM_16", format="FLAC")
    assert sbr_arm.spectral_ceiling(path) > 18000


def test_a_file_shorter_than_one_block_returns_zero(tmp_path):
    """Not a crash, and not a plausible-looking frequency either."""
    path = tmp_path / "tiny.flac"
    sf.write(str(path), np.zeros(1000), RATE, subtype="PCM_16", format="FLAC")
    assert sbr_arm.spectral_ceiling(path) == 0.0


# --------------------------------------------------------------------------
# Guard 1 - the profile check must be able to refuse
# --------------------------------------------------------------------------


def test_profile_failures_suppress_the_conclusion(capsys):
    rows = [row("he_aac_64k"), row("lc_aac_64k", ceiling=12645)]
    sbr_arm.report(rows, ["s.flac / he_aac_64k: profil 'LC' au lieu de 'HE-AAC'"])
    out = capsys.readouterr().out
    assert "Ne rien en conclure" in out
    assert "tous les encodages HE-AAC declarent" not in out


def test_clean_profiles_do_conclude(capsys):
    """Otherwise the previous test could pass by never affirming anything."""
    sbr_arm.report([row("he_aac_64k"), row("lc_aac_64k", ceiling=12645)], [])
    out = capsys.readouterr().out
    assert "tous les encodages HE-AAC declarent" in out
    assert "Ne rien en conclure" not in out


# --------------------------------------------------------------------------
# Guard 2 - an SBR arm that did not fill high must be called out
# --------------------------------------------------------------------------


def test_an_sbr_arm_that_does_not_fill_high_is_refused(capsys):
    rows = [row("he_aac_64k", ceiling=12000), row("lc_aac_64k", ceiling=12645)]
    sbr_arm.report(rows, [])
    out = capsys.readouterr().out
    assert "n'a pas fait ce qu'il pretend" in out


def test_an_sbr_arm_that_does_fill_high_passes(capsys):
    rows = [row("he_aac_64k", ceiling=20448), row("lc_aac_64k", ceiling=12645)]
    sbr_arm.report(rows, [])
    out = capsys.readouterr().out
    lines = [
        line
        for line in out.splitlines()
        if line.strip().startswith("he_aac_64k") and "contre" in line
    ]
    assert lines and "OK" in lines[0]
    assert "n'a pas fait ce qu'il pretend" not in lines[0]


# --------------------------------------------------------------------------
# The headline number
# --------------------------------------------------------------------------


def test_missed_counts_only_authentic_reads():
    rows = [
        row("he_aac_64k", verdict="AUTHENTIC"),
        row("he_aac_64k", verdict="WARNING"),
        row("he_aac_64k", verdict="FAKE_CERTAIN"),
    ]
    assert sbr_arm.missed(rows, "he_aac_64k") == (1, 3)


def test_missed_does_not_count_failures_as_catches():
    """A failed analysis is not a detection.

    Counting ECHEC rows as "not missed" would make a broken arm look like a
    working one.
    """
    rows = [row("he_aac_64k", verdict="ECHEC:RuntimeError")]
    hole, total = sbr_arm.missed(rows, "he_aac_64k")
    assert (hole, total) == (0, 1)


def test_missed_on_an_absent_arm_is_zero_over_zero():
    assert sbr_arm.missed([row("he_aac_64k")], "does_not_exist") == (0, 0)


def test_the_blind_spot_marker_only_fires_on_sbr_arms(capsys):
    rows = [
        row("he_aac_64k", verdict="AUTHENTIC", ceiling=20448),
        row("lc_aac_64k", verdict="AUTHENTIC", ceiling=12645),
        row("lc_aac_128k", verdict="AUTHENTIC", ceiling=17288),
    ]
    sbr_arm.report(rows, [])
    out = capsys.readouterr().out
    sbr_line = [
        line
        for line in out.splitlines()
        if line.strip().startswith("he_aac_64k") and "AUTHENTIC" in line
    ]
    lc_line = [
        line
        for line in out.splitlines()
        if line.strip().startswith("lc_aac_64k") and "AUTHENTIC" in line
    ]
    assert sbr_line and "ANGLE MORT" in sbr_line[0]
    assert lc_line and "ANGLE MORT" not in lc_line[0]


# --------------------------------------------------------------------------
# The arm table itself
# --------------------------------------------------------------------------


def test_every_sbr_arm_is_declared_in_the_arm_table():
    declared = {arm for arm, _, _, _ in sbr_arm.ARMS}
    assert set(sbr_arm.SBR_ARMS) <= declared
    assert set(sbr_arm.CEILING_CONTROLS.values()) <= declared


def test_sbr_arms_expect_the_he_aac_profile():
    for arm, _, _, expected in sbr_arm.ARMS:
        if arm in sbr_arm.SBR_ARMS:
            assert expected == "HE-AAC", arm


def test_there_is_at_least_one_non_sbr_control_at_a_comparable_rate():
    """Without a control, a poor SBR result could just mean 'low bitrate is hard'."""
    non_sbr = [a for a, _, _, _ in sbr_arm.ARMS if a not in sbr_arm.SBR_ARMS]
    assert any("64k" in a for a in non_sbr)


@pytest.mark.parametrize("arm", sbr_arm.SBR_ARMS)
def test_sbr_arms_use_the_mediafoundation_encoder(arm):
    """Each SBR arm must still be driven by MediaFoundation.

    The ffmpeg native aac encoder cannot produce SBR at all, so an arm that lost
    its ``aac_mf`` would silently become an AAC-LC arm.
    """
    args = next(a for name, a, _, _ in sbr_arm.ARMS if name == arm)
    assert "aac_mf" in args


def test_every_sbr_arm_has_a_rate_matched_control():
    """A control at another bitrate answers a different question.

    The first run of this arm compared 32 kbps SBR with 128 kbps AAC-LC and the
    guard refused it, correctly: the claim is that at a GIVEN rate SBR fills
    higher than not-SBR, not that it beats four times the rate.
    """
    for arm in sbr_arm.SBR_ARMS:
        control = sbr_arm.CEILING_CONTROLS[arm]
        assert arm.rsplit("_", 1)[-1] == control.rsplit("_", 1)[-1], (arm, control)


def test_an_empty_control_arm_is_undecidable_not_a_pass(capsys):
    """With no control rows at all the guard must refuse to answer.

    A comparison against an absent control would otherwise read as OK, which is
    the empty-denominator failure this project keeps rediscovering.
    """
    sbr_arm.report([row("he_aac_64k", ceiling=20448)], [])
    out = capsys.readouterr().out
    line = [ln for ln in out.splitlines() if ln.strip().startswith("he_aac_64k") and "contre" in ln]
    assert line and "INDECIDABLE" in line[0]
