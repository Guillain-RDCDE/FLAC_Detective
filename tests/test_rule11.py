"""Unit tests for Rule 11: Cassette Detection."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from flac_detective.analysis.new_scoring.rules.cassette import apply_rule_11_cassette_detection

# Mock soundfile read to return synthetic audio
@pytest.fixture
def mock_sf_read():
    with patch("soundfile.read") as mock:
        yield mock

def test_rule11_skipped_high_cutoff():
    """Rule 11 should be skipped if cutoff >= 19 kHz."""
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac",
        cutoff_freq=20000,
        cutoff_std=100,
        mp3_pattern_detected=False,
        sample_rate=44100
    )
    assert score == 0
    assert len(reasons) == 0

def test_rule11_full_cassette_profile(mock_sf_read):
    """Test a file matching all cassette criteria."""
    sr = 44100
    duration = 5.0
    t = np.linspace(0, duration, int(sr * duration))
    
    # Generate synthetic "cassette" audio
    # 1. Base audio (music) - low pass at 15k
    music = np.sin(2 * np.pi * 440 * t) 
    
    # 2. Tape hiss (White noise)
    # We want it > -60dB in the 16k-18k range
    # -40 dB full-band noise should leave enough energy in the 2kHz band
    noise = np.random.normal(0, 10**(-40/20), len(t))
    
    audio = music + noise
    
    mock_sf_read.return_value = (audio, sr)

    # Cutoff at 15k (Music)
    # Cutoff std 150 (Natural variation)
    # No MP3 pattern
    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac",
        cutoff_freq=15000,
        cutoff_std=150,
        mp3_pattern_detected=False,
        sample_rate=sr
    )

    # Expected:
    # 11A (Tape hiss): +30
    # 11B (Roll-off): Hard to simulate perfectly with simple noise, but let's see.
    #      White noise is flat, so roll-off is 0. 
    #      We need to filter the noise to have a slope? 
    #      Actually white noise has 0 slope. 
    #      Rule 11B expects slope between -6 and -3.
    #      So 11B probably won't trigger with pure white noise.
    # 11C (No MP3): +20
    # 11D (Variance 150): +15
    # Total expected: 30 + 20 + 15 = 65 (assuming 11B fails or yields 0)
    
    # Let's check reasons to be sure
    print("\nReasons:", reasons)
    
    assert score >= 65  # At least A, C, D
    assert any("R11A" in r for r in reasons)
    assert any("R11C" in r for r in reasons)
    assert any("R11D" in r for r in reasons)

def test_rule11_digital_cut(mock_sf_read):
    """Test a digital file (low variation, no noise)."""
    sr = 44100
    t = np.linspace(0, 1, int(sr))
    audio = np.zeros_like(t) # Silence
    
    mock_sf_read.return_value = (audio, sr)

    score, reasons = apply_rule_11_cassette_detection(
        "dummy.flac",
        cutoff_freq=15000,
        cutoff_std=10, # Very stable (suspicious)
        mp3_pattern_detected=True, # MP3 pattern detected
        sample_rate=sr
    )

    # Expected:
    # 11A (No noise): 0
    # 11B (Silence): slope probably crazy or 0, or skipped. 0 or -20 if distinct cut.
    #      With silence, response will be -100dB everywhere. Slope 0.
    # 11C (MP3 detected): 0
    # 11D (Variance 10 < 50): -20
    # Total: -20 (max(0, -20) -> 0 because function returns max(0, score))
    
    # Wait, the rule implementation returns max(0, cassette_score).
    # Correct.
    
    assert score == 0
    # But checking internal logic via reasons
    assert any("R11D" in r for r in reasons) 
    # Note: R11B might trigger "Sharp digital cut" if we had signal dropping sharp.
    # But here we have 0 score cap.
