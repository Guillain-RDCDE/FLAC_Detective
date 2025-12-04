"""Tests for the new 6-rule FLAC fake detection scoring system.

This test suite validates the scoring system against the 4 mandatory test cases
from the machine specifications.
"""

from pathlib import Path
from unittest.mock import Mock, patch
from flac_detective.analysis.new_scoring import (
    new_calculate_score,
    get_cutoff_threshold,
    calculate_apparent_bitrate,
    MP3_STANDARD_BITRATES,
    SCORE_FAKE_CERTAIN,
    SCORE_SUSPICIOUS,
    SCORE_WARNING,
)


class TestCutoffThresholds:
    """Test cutoff frequency thresholds based on sample rate."""
    
    def test_44100_hz_threshold(self):
        """Test threshold for 44.1kHz."""
        assert get_cutoff_threshold(44100) == 20000
    
    def test_48000_hz_threshold(self):
        """Test threshold for 48kHz."""
        assert get_cutoff_threshold(48000) == 22000
    
    def test_88200_hz_threshold(self):
        """Test threshold for 88.2kHz."""
        assert get_cutoff_threshold(88200) == 40000
    
    def test_96000_hz_threshold(self):
        """Test threshold for 96kHz."""
        assert get_cutoff_threshold(96000) == 44000
    
    def test_unknown_sample_rate_uses_45_percent(self):
        """Test threshold for unknown sample rate."""
        # For unknown sample rates, should use 45% of sample rate
        threshold = get_cutoff_threshold(50000)
        assert threshold == 50000 * 0.45


class TestBitrateCalculations:
    """Test bitrate calculation functions."""
    
    def test_calculate_apparent_bitrate(self):
        """Test apparent bitrate calculation for 16-bit."""
        # 44100 Hz × 16 bits × 2 channels / 1000 = 1411.2 kbps
        assert calculate_apparent_bitrate(44100, 16, 2) == 1411
    
    def test_calculate_apparent_bitrate_24bit(self):
        """Test apparent bitrate calculation for 24-bit."""
        # 48000 Hz × 24 bits × 2 channels / 1000 = 2304 kbps
        assert calculate_apparent_bitrate(48000, 24, 2) == 2304


class TestMandatoryTestCase1:
    """TEST 1: MP3 320 kbps with high frequency - MUST be detected as FAKE.
    
    File: 02 - Dalton - Soul brother.flac
    Parameters: sample_rate 44100, bits 16, cutoff ~20.5 kHz, 
                bitrate_container 851 kbps (FLAC container for MP3 320)
    
    Expected score calculation:
    - Règle 1: +50 points (cutoff ~20.5kHz = 320 kbps MP3, container 851 in range 700-950)
    - Règle 2: +0 points (cutoff > 20000)
    - Règle 3: +50 points (mp3_bitrate=320 detected and container 851 > 600)
    - Total: 100 points
    - Expected verdict: FAKE_CERTAIN
    """
    
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_bitrate_variance')
    @patch('flac_detective.analysis.new_scoring.strategies.apply_rule_7_silence_analysis')
    def test_mp3_320_high_cutoff(self, mock_rule7, mock_variance, mock_real_bitrate):
        """Test Case 1: MP3 320 kbps with high cutoff."""
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks - Use realistic FLAC container bitrate for MP3 320
        mock_real_bitrate.return_value = 851  # FLAC container bitrate (700-950 kbps range)
        mock_variance.return_value = 50  # Low variance (constant bitrate)
        
        # Mock Rule 7 to return neutral result (0 points)
        mock_rule7.return_value = (0, [], None)
        
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
        
        # Cutoff frequency - MP3 320 kbps typically has cutoff around 20.5 kHz
        cutoff_freq = 20500  # Below 21kHz threshold, in 320 kbps range (19.5-21.5 kHz)
        
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
                bitrate_container 725 kbps (FLAC container for MP3 256)
    
    Expected score calculation:
    - Règle 1: +50 points (cutoff 19143 Hz = 256 kbps MP3, container 725 in range 600-850)
    - Règle 2: +14 points ((22000-19143)/200)
    - Règle 3: +50 points (mp3_bitrate=256 detected and container 725 > 600)
    - Règle 4: +30 points (24-bit with mp3_bitrate 256 < 500)
    - Total: 144 points
    - Expected verdict: FAKE_CERTAIN
    """
    
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_bitrate_variance')
    @patch('flac_detective.analysis.new_scoring.strategies.apply_rule_7_silence_analysis')
    def test_mp3_256_24bit(self, mock_rule7, mock_variance, mock_real_bitrate):
        """Test Case 2: MP3 256 kbps in 24-bit container."""
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks - Use realistic FLAC container bitrate for MP3 256
        mock_real_bitrate.return_value = 725  # FLAC container bitrate (600-850 kbps range)
        mock_variance.return_value = 30  # Low variance
        
        # Mock Rule 7 to return neutral result
        mock_rule7.return_value = (0, [], None)
        
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
        
        # Cutoff frequency - MP3 256 kbps has cutoff around 18.5-19.5 kHz
        cutoff_freq = 19143  # In 256 kbps range
        
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
    
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_bitrate_variance')
    @patch('flac_detective.analysis.new_scoring.strategies.apply_rule_7_silence_analysis')
    def test_authentic_poor_quality(self, mock_rule7, mock_variance, mock_real_bitrate):
        """Test Case 3: Authentic FLAC with poor quality (e.g. vinyl rip)."""
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks
        mock_real_bitrate.return_value = 850  # Real bitrate = 850 kbps
        mock_variance.return_value = 150  # High variance (variable bitrate)
        
        # Mock Rule 7
        mock_rule7.return_value = (0, [], None)
        
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
        assert score < 31, f"Expected score < 31 (AUTHENTIC), got {score}"
        assert verdict == "AUTHENTIC", f"Expected AUTHENTIC, got {verdict}"


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
    
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_real_bitrate')
    @patch('flac_detective.analysis.new_scoring.calculator.calculate_bitrate_variance')
    @patch('flac_detective.analysis.new_scoring.strategies.apply_rule_7_silence_analysis')
    def test_authentic_high_quality(self, mock_rule7, mock_variance, mock_real_bitrate):
        """Test Case 4: Authentic high-quality FLAC."""
        # Mock file path
        mock_path = Mock(spec=Path)
        
        # Setup mocks
        mock_real_bitrate.return_value = 1580  # Real bitrate = 1580 kbps
        mock_variance.return_value = 200  # High variance (variable bitrate)
        
        # Mock Rule 7
        mock_rule7.return_value = (0, [], None)
        
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
        assert score < 31, f"Expected score < 31 (AUTHENTIC), got {score}"
        assert verdict == "AUTHENTIC", f"Expected AUTHENTIC, got {verdict}"


class TestVerdictThresholds:
    """Test that verdict thresholds are correctly applied."""
    
    def test_fake_certain_threshold(self):
        """Score >= 86 should give FAKE_CERTAIN verdict."""
        assert SCORE_FAKE_CERTAIN == 86
    
    def test_suspicious_threshold(self):
        """Score >= 61 should give SUSPICIOUS verdict."""
        assert SCORE_SUSPICIOUS == 61
    
    def test_warning_threshold(self):
        """Score >= 31 should give WARNING verdict."""
        assert SCORE_WARNING == 31


class TestMP3BitrateConstants:
    """Test that MP3 bitrate constants are immutable and correct."""
    
    def test_mp3_standard_bitrates(self):
        """Verify MP3 standard bitrates list."""
        expected = [96, 128, 160, 192, 224, 256, 320]
        assert MP3_STANDARD_BITRATES == expected


class TestRule7SilenceAnalysis:
    """Test Rule 7: Silence Analysis."""
    
    @patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio')
    def test_transcode_detection(self, mock_analyze):
        """Test detection of transcode (high HF energy in silence)."""
        # Setup mock
        mock_analyze.return_value = (0.4, "OK", 0.004, 0.01)  # Ratio 0.4 > 0.3
        
        # Call rule
        from flac_detective.analysis.new_scoring.rules import apply_rule_7_silence_analysis
        score, reasons, ratio = apply_rule_7_silence_analysis("dummy.flac", 20000, 44100)
        
        assert score == 50
        assert ratio == 0.4
        assert "Dither artificiel" in reasons[0]
        
    @patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio')
    def test_authentic_detection(self, mock_analyze):
        """Test detection of authentic file (low HF energy in silence)."""
        # Setup mock
        mock_analyze.return_value = (0.05, "OK", 0.0005, 0.01)  # Ratio 0.05 < 0.15
        
        # Call rule
        from flac_detective.analysis.new_scoring.rules import apply_rule_7_silence_analysis
        score, reasons, ratio = apply_rule_7_silence_analysis("dummy.flac", 20000, 44100)
        
        assert score == -50
        assert ratio == 0.05
        assert "Silence naturel" in reasons[0]
        
    @patch('flac_detective.analysis.new_scoring.rules.silence.detect_vinyl_noise')
    @patch('flac_detective.analysis.new_scoring.rules.silence.sf.read')
    @patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio')
    def test_uncertain_zone(self, mock_analyze, mock_sf_read, mock_vinyl):
        """Test uncertain zone (ratio between 0.15 and 0.3) proceeds to Phase 2."""
        # Setup mocks
        mock_analyze.return_value = (0.2, "OK", 0.002, 0.01)  # Ratio 0.2 (uncertain)
        mock_sf_read.return_value = (None, 44100)  # Dummy audio data
        # Mock vinyl detection - noise with pattern (uncertain)
        mock_vinyl.return_value = (False, {'energy_db': -60, 'autocorr': 0.4})
        
        # Call rule
        from flac_detective.analysis.new_scoring.rules import apply_rule_7_silence_analysis
        score, reasons, ratio = apply_rule_7_silence_analysis("dummy.flac", 20000, 44100)
        
        # In uncertain zone, proceeds to Phase 2
        # Phase 2 returns uncertain (noise with pattern) -> 0 points
        assert score == 0
        assert ratio == 0.2
        assert len(reasons) == 1
        assert "Bruit avec pattern" in reasons[0] or "Incertain" in reasons[0]
        
    @patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio')
    def test_skipped_outside_range_low(self, mock_analyze):
        """Test rule skipped if cutoff too low."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_7_silence_analysis
        score, reasons, ratio = apply_rule_7_silence_analysis("dummy.flac", 18000, 44100)
        
        assert score == 0
        assert not reasons
        assert ratio is None
        mock_analyze.assert_not_called()
        
    @patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio')
    def test_skipped_outside_range_high(self, mock_analyze):
        """Test rule skipped if cutoff too high."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_7_silence_analysis
        score, reasons, ratio = apply_rule_7_silence_analysis("dummy.flac", 22000, 44100)
        
        assert score == 0
        assert not reasons
        assert ratio is None
        mock_analyze.assert_not_called()
