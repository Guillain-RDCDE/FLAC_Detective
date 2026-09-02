"""Tests for the plain-language presentation layer (easy mode)."""

from __future__ import annotations

from flac_detective import presentation as pz


def test_verdict_plain_known_and_default():
    icon, label, action = pz.verdict_plain("FAKE_CERTAIN")
    assert label == "Fake"
    assert action  # non-empty recommended action
    # Unknown verdict degrades gracefully.
    icon2, label2, action2 = pz.verdict_plain("WHATEVER")
    assert label2 == "WHATEVER"


def test_plain_explanation_authentic():
    txt = pz.plain_explanation({"verdict": "AUTHENTIC"})
    assert "genuine" in txt.lower()
    assert _no_jargon(txt)


def test_plain_explanation_authentic_states_its_scope():
    """A pass must say how far it reaches.

    On set B this verdict came back for all 35 atrac3plus files: every rule ran,
    none covers that format, and an unqualified "genuine lossless audio" is a
    clean bill the engine had no standing to give. It cannot abstain instead —
    it cannot see that the file is ATRAC — so the pass has to carry its own
    limit.
    """
    txt = pz.plain_explanation({"verdict": "AUTHENTIC"})
    assert "not a guarantee" in txt.lower()
    assert "panel" in txt.lower()
    assert _no_jargon(txt)


def test_plain_explanation_fake_uses_cliff_and_bitrate():
    txt = pz.plain_explanation(
        {"verdict": "FAKE_CERTAIN", "cutoff_freq": 16000, "estimated_mp3_bitrate": 128}
    )
    assert "16 kHz" in txt
    assert "128 kbps" in txt
    assert _no_jargon(txt)


def test_plain_explanation_suspicious_without_bitrate():
    txt = pz.plain_explanation({"verdict": "SUSPICIOUS", "cutoff_freq": 17500})
    assert "kHz" in txt  # mentions the cutoff in kHz, in plain language
    assert _no_jargon(txt)


def test_plain_explanation_hires_note_appended():
    txt = pz.plain_explanation(
        {"verdict": "AUTHENTIC", "hires_verdict": "UPSAMPLED", "suspected_original_rate": 44100}
    )
    assert "upsampled" in txt.lower()
    assert _no_jargon(txt)


def test_plain_explanation_padded_depth():
    txt = pz.plain_explanation({"verdict": "AUTHENTIC", "hires_verdict": "PADDED_DEPTH"})
    assert "16-bit" in txt


def _no_jargon(txt: str) -> bool:
    """Easy-mode text must not leak rule codes, point contributions, dB or p-values."""
    lowered = txt.lower()
    banned = ["r1", "r9", "r12", "+pts", "pts)", " db", "p=", "softmax", "residual"]
    return not any(b in lowered for b in banned)
