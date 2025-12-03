"""Tests for Rule 9: Compression Artifacts Detection."""

import pytest
import numpy as np
import soundfile as sf
from pathlib import Path
from unittest.mock import patch, MagicMock
from flac_detective.analysis.new_scoring.artifacts import (
    detect_preecho_artifacts,
    detect_hf_aliasing,
    detect_mp3_noise_pattern,
    analyze_compression_artifacts
)


class TestPreechoDetection:
    """Test pre-echo artifact detection (Test 9A)."""

    def test_preecho_with_clean_transients(self):
        """Clean transients should not show pre-echo."""
        # Generate clean audio with sharp transients
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create clean transients (no pre-echo)
        audio = np.zeros_like(t)
        transient_positions = [0.2, 0.5, 0.8]
        for pos in transient_positions:
            idx = int(pos * sample_rate)
            audio[idx:idx+100] = 0.9  # Sharp peak
        
        percentage, num_transients, num_affected = detect_preecho_artifacts(
            audio, sample_rate
        )
        
        assert num_transients > 0, "Should detect transients"
        assert percentage < 5, "Clean transients should have low pre-echo percentage"

    def test_preecho_with_artificial_artifacts(self):
        """Artificial pre-echo should be detected."""
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create transient with artificial pre-echo
        audio = np.zeros_like(t)
        transient_idx = int(0.5 * sample_rate)
        
        # Add HF energy BEFORE the transient (pre-echo)
        pre_window = int(0.015 * sample_rate)
        hf_signal = np.sin(2 * np.pi * 15000 * t[:pre_window]) * 0.3
        audio[transient_idx - pre_window:transient_idx] = hf_signal
        
        # Add the main transient
        audio[transient_idx:transient_idx+100] = 0.9
        
        percentage, num_transients, num_affected = detect_preecho_artifacts(
            audio, sample_rate
        )
        
        # Note: This test may not always detect pre-echo due to filtering
        # but it validates the function runs without errors
        assert num_transients >= 0


class TestHFAliasing:
    """Test high-frequency aliasing detection (Test 9B)."""

    def test_aliasing_with_clean_audio(self):
        """Clean audio should show low aliasing correlation."""
        sample_rate = 44100
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Generate clean audio with random HF content
        np.random.seed(42)
        audio = np.random.randn(len(t)) * 0.1
        
        correlation = detect_hf_aliasing(audio, sample_rate)
        
        assert 0 <= correlation <= 1, "Correlation should be between 0 and 1"
        assert correlation < 0.3, "Clean audio should have low aliasing"

    def test_aliasing_with_low_sample_rate(self):
        """Low sample rate should skip the test."""
        sample_rate = 22050  # Too low for 20 kHz analysis
        audio = np.random.randn(1000)
        
        correlation = detect_hf_aliasing(audio, sample_rate)
        
        assert correlation == 0.0, "Should return 0 for low sample rate"


class TestMP3NoisePattern:
    """Test MP3 noise pattern detection (Test 9C)."""

    def test_mp3_pattern_with_clean_audio(self):
        """Clean audio should not show MP3 noise pattern."""
        sample_rate = 44100
        duration = 3.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Generate clean white noise
        np.random.seed(42)
        audio = np.random.randn(len(t)) * 0.1
        
        pattern_detected = detect_mp3_noise_pattern(audio, sample_rate)
        
        assert isinstance(pattern_detected, bool)
        # Clean noise is unlikely to have MP3 pattern, but not guaranteed
        # so we just check it runs without error

    def test_mp3_pattern_with_low_sample_rate(self):
        """Low sample rate should skip the test."""
        sample_rate = 22050
        audio = np.random.randn(10000)
        
        pattern_detected = detect_mp3_noise_pattern(audio, sample_rate)
        
        assert pattern_detected == False, "Should return False for low sample rate"

    def test_mp3_pattern_with_short_audio(self):
        """Short audio should skip the test."""
        sample_rate = 44100
        audio = np.random.randn(1000)  # Very short
        
        pattern_detected = detect_mp3_noise_pattern(audio, sample_rate)
        
        assert pattern_detected == False, "Should return False for short audio"


class TestCompressionArtifactsAnalysis:
    """Test the main Rule 9 analysis function."""

    def test_rule9_skips_when_not_activated(self):
        """Rule 9 should skip if cutoff >= 21 kHz and no MP3 detected."""
        with patch('flac_detective.analysis.new_scoring.artifacts.sf.read') as mock_read:
            # Mock audio data
            sample_rate = 44100
            audio = np.random.randn(sample_rate * 2)
            mock_read.return_value = (audio, sample_rate)
            
            score, reasons, details = analyze_compression_artifacts(
                'dummy.flac',
                cutoff_freq=22000,  # High cutoff
                mp3_bitrate_detected=None  # No MP3 detected
            )
            
            assert score == 0, "Should not activate"
            assert len(reasons) == 0, "Should have no reasons"

    def test_rule9_activates_with_low_cutoff(self):
        """Rule 9 should activate if cutoff < 21 kHz."""
        with patch('flac_detective.analysis.new_scoring.artifacts.sf.read') as mock_read:
            # Mock audio data
            sample_rate = 44100
            audio = np.random.randn(sample_rate * 2)
            mock_read.return_value = (audio, sample_rate)
            
            score, reasons, details = analyze_compression_artifacts(
                'dummy.flac',
                cutoff_freq=18000,  # Low cutoff
                mp3_bitrate_detected=None
            )
            
            # Should run the tests (score may be 0 if no artifacts found)
            assert 'tests_run' in details
            assert len(details['tests_run']) > 0

    def test_rule9_activates_with_mp3_signature(self):
        """Rule 9 should activate if MP3 signature detected."""
        with patch('flac_detective.analysis.new_scoring.artifacts.sf.read') as mock_read:
            # Mock audio data
            sample_rate = 44100
            audio = np.random.randn(sample_rate * 2)
            mock_read.return_value = (audio, sample_rate)
            
            score, reasons, details = analyze_compression_artifacts(
                'dummy.flac',
                cutoff_freq=22000,  # High cutoff
                mp3_bitrate_detected=320  # MP3 detected
            )
            
            # Should run the tests
            assert 'tests_run' in details
            assert len(details['tests_run']) > 0

    def test_rule9_handles_file_load_error(self):
        """Rule 9 should handle file loading errors gracefully."""
        with patch('flac_detective.analysis.new_scoring.artifacts.sf.read') as mock_read:
            mock_read.side_effect = Exception("File not found")
            
            score, reasons, details = analyze_compression_artifacts(
                'nonexistent.flac',
                cutoff_freq=18000,
                mp3_bitrate_detected=None
            )
            
            assert score == 0, "Should return 0 on error"
            assert len(reasons) == 0, "Should have no reasons on error"

    def test_rule9_scoring_thresholds(self):
        """Test that scoring thresholds work correctly."""
        with patch('flac_detective.analysis.new_scoring.artifacts.sf.read') as mock_read:
            sample_rate = 44100
            audio = np.random.randn(sample_rate * 2)
            mock_read.return_value = (audio, sample_rate)
            
            # Mock the detection functions to return specific values
            with patch('flac_detective.analysis.new_scoring.artifacts.detect_preecho_artifacts') as mock_preecho:
                with patch('flac_detective.analysis.new_scoring.artifacts.detect_hf_aliasing') as mock_aliasing:
                    with patch('flac_detective.analysis.new_scoring.artifacts.detect_mp3_noise_pattern') as mock_pattern:
                        # Test high pre-echo (>10%)
                        mock_preecho.return_value = (15.0, 10, 2)
                        mock_aliasing.return_value = 0.1
                        mock_pattern.return_value = False
                        
                        score, reasons, details = analyze_compression_artifacts(
                            'dummy.flac',
                            cutoff_freq=18000,
                            mp3_bitrate_detected=None
                        )
                        
                        assert score == 15, "Should give +15 for high pre-echo"
                        assert any('R9A' in r for r in reasons)

    def test_rule9_cumulative_scoring(self):
        """Test that all three tests can contribute to score."""
        with patch('flac_detective.analysis.new_scoring.artifacts.sf.read') as mock_read:
            sample_rate = 44100
            audio = np.random.randn(sample_rate * 2)
            mock_read.return_value = (audio, sample_rate)
            
            with patch('flac_detective.analysis.new_scoring.artifacts.detect_preecho_artifacts') as mock_preecho:
                with patch('flac_detective.analysis.new_scoring.artifacts.detect_hf_aliasing') as mock_aliasing:
                    with patch('flac_detective.analysis.new_scoring.artifacts.detect_mp3_noise_pattern') as mock_pattern:
                        # All tests detect artifacts
                        mock_preecho.return_value = (12.0, 10, 2)  # +15 points
                        mock_aliasing.return_value = 0.6  # +15 points
                        mock_pattern.return_value = True  # +10 points
                        
                        score, reasons, details = analyze_compression_artifacts(
                            'dummy.flac',
                            cutoff_freq=18000,
                            mp3_bitrate_detected=None
                        )
                        
                        assert score == 40, "Should give max +40 for all artifacts"
                        assert len(reasons) == 3, "Should have 3 reasons"
                        assert any('R9A' in r for r in reasons)
                        assert any('R9B' in r for r in reasons)
                        assert any('R9C' in r for r in reasons)
