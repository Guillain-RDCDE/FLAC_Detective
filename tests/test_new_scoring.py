"""Tests for the new 6-rule FLAC fake detection scoring system.

This test suite validates the scoring system against the 4 mandatory test cases
from the machine specifications.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from flac_detective.analysis.new_scoring import (
    new_calculate_score,
    get_cutoff_threshold,
    get_minimum_expected_bitrate,
    calculate_real_bitrate,
    calculate_apparent_bitrate,
    MP3_STANDARD_BITRATES,
    SCORE_FAKE_CERTAIN,
    SCORE_FAKE_PROBABLE,
    SCORE_DOUTEUX,
)


class TestCutoffThresholds:
    """Test cutoff frequency thresholds based on sample rate."""
    
    def test_44100_hz_threshold(self):
        assert get_cutoff_threshold(44100) == 20000
    
    def test_48000_hz_threshold(self):
        assert get_cutoff_threshold(48000) == 22000
    
    def test_88200_hz_threshold(self):
        assert get_cutoff_threshold(88200) == 40000
    
    def test_96000_hz_threshold(self):
        assert get_cutoff_threshold(96000) == 44000
    
    def test_unknown_sample_rate_uses_45_percent(self):
        # For unknown sample rates, should use 45% of sample rate
        threshold = get_cutoff_threshold(50000)
        assert threshold == 50000 * 0.45


class TestMinimumExpectedBitrate:
    """Test minimum expected bitrate calculations."""
    
    def test_44100_16bit(self):
        assert get_minimum_expected_bitrate(44100, 16) == 600
    
    def test_48000_16bit(self):
        assert get_minimum_expected_bitrate(48000, 16) == 650
    
    def test_44100_24bit(self):
        assert get_minimum_expected_bitrate(44100, 24) == 900
    
    def test_48000_24bit(self):
        assert get_minimum_expected_bitrate(48000, 24) == 1000
    
    def test_88200_24bit(self):
        assert get_minimum_expected_bitrate(88200, 24) == 1800
    
    def test_96000_24bit(self):
        assert get_minimum_expected_bitrate(96000, 24) == 2000


class TestBitrateCalculations:
    """Test bitrate calculation functions."""
    
    def test_calculate_apparent_bitrate(self):
        # 44100 Hz × 16 bits × 2 channels / 1000 = 1411.2 kbps
        assert calculate_apparent_bitrate(44100, 16, 2) == 1411
    
    def test_calculate_apparent_bitrate_24bit(self):
        # 48000 Hz × 24 bits × 2 channels / 1000 = 2304 kbps
        assert calculate_apparent_bitrate(48000, 24, 2) == 2304


class TestMandatoryTestCase1:
    """TEST 1: MP3 320 kbps with high frequency - MUST be detected as FAKE.
    
    File: 02 - Dalton - Soul brother.flac
    Parameters: sample_rate 44100, bits 16, cutoff 21166 Hz, 
                bitrate_real 320 kbps, bitrate_apparent 851 kbps
    
    Expected score calculation:
    - Règle 1: +50 points (bitrate = 320)
    - Règle 2: +0 points (cutoff > 20000)
    - Règle 3: +50 points (320 < 400 and 851 > 600)
    - Total: 100 points
    - Expected verdict: FAKE_CERTAIN
    """
    
    @patch('flac_detective.analysis.new_scoring.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculate_bitrate_variance')
    def test_mp3_320_high_cutoff(self, mock_variance, mock_real_bitrate):
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks
        mock_real_bitrate.return_value = 320  # Real bitrate = 320 kbps
        mock_variance.return_value = 50  # Low variance (constant bitrate)
        
        # Metadata
        metadata = {
            "sample_rate": 44100,
            "bit_depth": 16,
            "channels": 2,
            "duration": 180.0,  # 3 minutes
        }
        
        # Duration check (no mismatch)
        duration_check = {
            "mismatch": None,
            "diff_ms": 0,
        }
        
        # Cutoff frequency
        cutoff_freq = 21166  # High cutoff (above 20kHz threshold)
        
        # Calculate score
        score, verdict, confidence, reason = new_calculate_score(
            cutoff_freq, metadata, duration_check, mock_path
        )
        
        # Assertions
        assert score == 100, f"Expected score 100, got {score}"
        assert verdict == "FAKE_CERTAIN", f"Expected FAKE_CERTAIN, got {verdict}"
        assert "320" in reason, "Reason should mention 320 kbps"


class TestMandatoryTestCase2:
    """TEST 2: MP3 256 kbps in 24-bit - MUST be detected as FAKE.
    
    File: 01 - Ara Kekedjian - Mini, midi, maxi.flac
    Parameters: sample_rate 48000, bits 24, cutoff 19143 Hz,
                bitrate_real 256 kbps, bitrate_apparent 1663 kbps
    
    Expected score calculation:
    - Règle 1: +50 points (bitrate = 256)
    - Règle 2: +14 points ((22000-19143)/200)
    - Règle 3: +50 points (256 < 400 and 1663 > 1000)
    - Règle 4: +30 points (24-bit with bitrate < 500)
    - Total: 144 points
    - Expected verdict: FAKE_CERTAIN
    """
    
    @patch('flac_detective.analysis.new_scoring.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculate_bitrate_variance')
    def test_mp3_256_24bit(self, mock_variance, mock_real_bitrate):
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks
        mock_real_bitrate.return_value = 256  # Real bitrate = 256 kbps
        mock_variance.return_value = 30  # Low variance
        
        # Metadata
        metadata = {
            "sample_rate": 48000,
            "bit_depth": 24,
            "channels": 2,
            "duration": 200.0,
        }
        
        # Duration check (no mismatch)
        duration_check = {
            "mismatch": None,
            "diff_ms": 0,
        }
        
        # Cutoff frequency
        cutoff_freq = 19143  # Below 22kHz threshold
        
        # Calculate score
        score, verdict, confidence, reason = new_calculate_score(
            cutoff_freq, metadata, duration_check, mock_path
        )
        
        # Assertions
        # Score should be >= 100 (capped at max, but internally calculated as 144)
        assert score >= 100, f"Expected score >= 100, got {score}"
        assert verdict == "FAKE_CERTAIN", f"Expected FAKE_CERTAIN, got {verdict}"
        assert "256" in reason or "24-bit" in reason, "Reason should mention 256 kbps or 24-bit issue"


class TestMandatoryTestCase3:
    """TEST 3: Authentic FLAC of poor quality - MUST NOT be detected as FAKE.
    
    File: Old vinyl rip
    Parameters: sample_rate 44100, bits 16, cutoff 18000 Hz,
                bitrate_real 850 kbps, bitrate_apparent 850 kbps, variance 150 kbps
    
    Expected score calculation:
    - Règle 1: +0 points (850 is not a standard MP3 bitrate)
    - Règle 2: +10 points ((20000-18000)/200)
    - Règle 3: +0 points (850 > 400)
    - Règle 6: -30 points (coherent and > 800)
    - Total: -20 → 0 points (minimum)
    - Expected verdict: AUTHENTIQUE
    """
    
    @patch('flac_detective.analysis.new_scoring.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculate_bitrate_variance')
    def test_authentic_poor_quality(self, mock_variance, mock_real_bitrate):
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks
        mock_real_bitrate.return_value = 850  # Real bitrate = 850 kbps
        mock_variance.return_value = 150  # High variance (variable bitrate)
        
        # Metadata
        metadata = {
            "sample_rate": 44100,
            "bit_depth": 16,
            "channels": 2,
            "duration": 180.0,
        }
        
        # Duration check (no mismatch)
        duration_check = {
            "mismatch": None,
            "diff_ms": 0,
        }
        
        # Cutoff frequency
        cutoff_freq = 18000  # Low cutoff (poor quality recording)
        
        # Calculate score
        score, verdict, confidence, reason = new_calculate_score(
            cutoff_freq, metadata, duration_check, mock_path
        )
        
        # Assertions
        assert score < 30, f"Expected score < 30 (AUTHENTIQUE), got {score}"
        assert verdict == "AUTHENTIQUE", f"Expected AUTHENTIQUE, got {verdict}"


class TestMandatoryTestCase4:
    """TEST 4: Authentic high-quality FLAC - MUST NOT be detected as FAKE.
    
    File: 01 - Hamid El Shaeri - Tew'idni dom.flac
    Parameters: sample_rate 44100, bits 16, cutoff 21878 Hz,
                bitrate_real 1580 kbps, bitrate_apparent 1580 kbps, variance 200 kbps
    
    Expected score calculation:
    - Règle 1: +0 points
    - Règle 2: +0 points (cutoff > 20000)
    - Règle 3: +0 points
    - Règle 5: -40 points (bitrate > 1000 and variance > 100)
    - Total: -40 → 0 points (minimum)
    - Expected verdict: AUTHENTIQUE
    """
    
    @patch('flac_detective.analysis.new_scoring.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculate_bitrate_variance')
    def test_authentic_high_quality(self, mock_variance, mock_real_bitrate):
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks
        mock_real_bitrate.return_value = 1580  # Real bitrate = 1580 kbps
        mock_variance.return_value = 200  # High variance (variable bitrate)
        
        # Metadata
        metadata = {
            "sample_rate": 44100,
            "bit_depth": 16,
            "channels": 2,
            "duration": 180.0,
        }
        
        # Duration check (no mismatch)
        duration_check = {
            "mismatch": None,
            "diff_ms": 0,
        }
        
        # Cutoff frequency
        cutoff_freq = 21878  # High cutoff (excellent quality)
        
        # Calculate score
        score, verdict, confidence, reason = new_calculate_score(
            cutoff_freq, metadata, duration_check, mock_path
        )
        
        # Assertions
        assert score < 30, f"Expected score < 30 (AUTHENTIQUE), got {score}"
        assert verdict == "AUTHENTIQUE", f"Expected AUTHENTIQUE, got {verdict}"


class TestVerdictThresholds:
    """Test that verdict thresholds are correctly applied."""
    
    def test_fake_certain_threshold(self):
        """Score >= 80 should give FAKE_CERTAIN verdict."""
        assert SCORE_FAKE_CERTAIN == 80
    
    def test_fake_probable_threshold(self):
        """Score >= 50 should give FAKE_PROBABLE verdict."""
        assert SCORE_FAKE_PROBABLE == 50
    
    def test_douteux_threshold(self):
        """Score >= 30 should give DOUTEUX verdict."""
        assert SCORE_DOUTEUX == 30


class TestMP3BitrateConstants:
    """Test that MP3 bitrate constants are immutable and correct."""
    
    def test_mp3_standard_bitrates(self):
        """Verify MP3 standard bitrates list."""
        expected = [96, 128, 160, 192, 224, 256, 320]
        assert MP3_STANDARD_BITRATES == expected
