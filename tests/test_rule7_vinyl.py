"""Tests for Rule 7: Silence Analysis and Vinyl Detection (3 Phases)."""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from flac_detective.analysis.new_scoring.rules import apply_rule_7_silence_analysis
from flac_detective.analysis.new_scoring.silence import (
    detect_vinyl_noise,
    detect_clicks_and_pops
)

class TestRule7VinylLogic:
    """Test the 3-phase logic of Rule 7."""

    def test_rule7_phase1_transcode(self):
        """Phase 1: High ratio (>0.3) should return +50 points (Transcode)."""
        with patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio') as mock_ratio:
            mock_ratio.return_value = (0.45, "OK", 0.0, 0.0)
            
            score, reasons, ratio = apply_rule_7_silence_analysis(
                'dummy.flac', cutoff_freq=20000, sample_rate=44100
            )
            
            assert score == 50
            assert "Dither artificiel" in reasons[0]
            assert ratio == 0.45

    def test_rule7_phase1_authentic(self):
        """Phase 1: Low ratio (<0.15) should return -50 points (Authentic)."""
        with patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio') as mock_ratio:
            mock_ratio.return_value = (0.05, "OK", 0.0, 0.0)
            
            score, reasons, ratio = apply_rule_7_silence_analysis(
                'dummy.flac', cutoff_freq=20000, sample_rate=44100
            )
            
            assert score == -50
            assert "Silence naturel" in reasons[0]
            assert ratio == 0.05

    def test_rule7_phase2_vinyl_detected(self):
        """Phase 2: Vinyl noise detected should return -40 points."""
        with patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio') as mock_ratio:
            # Ratio in uncertain zone (0.15-0.3)
            mock_ratio.return_value = (0.20, "OK", 0.0, 0.0)
            
            with patch('flac_detective.analysis.new_scoring.rules.silence.sf') as mock_sf:
                mock_sf.read.return_value = (np.zeros(100), 44100)
                
                with patch('flac_detective.analysis.new_scoring.rules.silence.detect_vinyl_noise') as mock_vinyl:
                    # Simulate vinyl detected
                    mock_vinyl.return_value = (True, {'energy_db': -60, 'autocorr': 0.1, 'temporal_variance': 2.0})
                    
                    with patch('flac_detective.analysis.new_scoring.rules.silence.detect_clicks_and_pops') as mock_clicks:
                        # No clicks confirmation
                        mock_clicks.return_value = (0, 0.0)
                        
                        score, reasons, ratio = apply_rule_7_silence_analysis(
                            'dummy.flac', cutoff_freq=20000, sample_rate=44100
                        )
                        
                        assert score == -40
                        assert "Bruit vinyle détecté" in reasons[0]

    def test_rule7_phase3_vinyl_confirmed_with_clicks(self):
        """Phase 3: Vinyl noise + Clicks should return -50 points (-40 + -10)."""
        with patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio') as mock_ratio:
            mock_ratio.return_value = (0.20, "OK", 0.0, 0.0)
            
            with patch('flac_detective.analysis.new_scoring.rules.silence.sf') as mock_sf:
                mock_sf.read.return_value = (np.zeros(100), 44100)
                
                with patch('flac_detective.analysis.new_scoring.rules.silence.detect_vinyl_noise') as mock_vinyl:
                    mock_vinyl.return_value = (True, {'energy_db': -60, 'autocorr': 0.1, 'temporal_variance': 2.0})
                    
                    with patch('flac_detective.analysis.new_scoring.rules.silence.detect_clicks_and_pops') as mock_clicks:
                        # Clicks confirm vinyl (20 clicks/min)
                        mock_clicks.return_value = (10, 20.0)
                        
                        score, reasons, ratio = apply_rule_7_silence_analysis(
                            'dummy.flac', cutoff_freq=20000, sample_rate=44100
                        )
                        
                        assert score == -50  # -40 (vinyl) + -10 (clicks)
                        assert any("Clicks vinyle détectés" in r for r in reasons)

    def test_rule7_phase2_digital_upsample(self):
        """Phase 2: No noise detected should return +20 points (Digital Upsample)."""
        with patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio') as mock_ratio:
            mock_ratio.return_value = (0.20, "OK", 0.0, 0.0)
            
            with patch('flac_detective.analysis.new_scoring.rules.silence.sf') as mock_sf:
                mock_sf.read.return_value = (np.zeros(100), 44100)
                
                with patch('flac_detective.analysis.new_scoring.rules.silence.detect_vinyl_noise') as mock_vinyl:
                    # No vinyl, very low energy
                    mock_vinyl.return_value = (False, {'energy_db': -80, 'autocorr': 0.0, 'temporal_variance': 0.0})
                    
                    score, reasons, ratio = apply_rule_7_silence_analysis(
                        'dummy.flac', cutoff_freq=20000, sample_rate=44100
                    )
                    
                    assert score == 20
                    assert "Pas de bruit" in reasons[0]

    def test_rule7_phase2_uncertain(self):
        """Phase 2: Noise with pattern should return 0 points (Uncertain)."""
        with patch('flac_detective.analysis.new_scoring.rules.silence.analyze_silence_ratio') as mock_ratio:
            mock_ratio.return_value = (0.20, "OK", 0.0, 0.0)
            
            with patch('flac_detective.analysis.new_scoring.rules.silence.sf') as mock_sf:
                mock_sf.read.return_value = (np.zeros(100), 44100)
                
                with patch('flac_detective.analysis.new_scoring.rules.silence.detect_vinyl_noise') as mock_vinyl:
                    # No vinyl, but high energy (noise present)
                    mock_vinyl.return_value = (False, {'energy_db': -60, 'autocorr': 0.5, 'temporal_variance': 0.0})
                    
                    score, reasons, ratio = apply_rule_7_silence_analysis(
                        'dummy.flac', cutoff_freq=20000, sample_rate=44100
                    )
                    
                    assert score == 0
                    assert "Bruit avec pattern" in reasons[0]

    def test_rule7_skipped_outside_range(self):
        """Rule 7 should be skipped if cutoff is outside 19-21.5 kHz."""
        score, reasons, ratio = apply_rule_7_silence_analysis(
            'dummy.flac', cutoff_freq=18000, sample_rate=44100
        )
        assert score == 0
        assert len(reasons) == 0


class TestSilenceModuleFunctions:
    """Test the helper functions in silence.py."""

    def test_detect_vinyl_noise_synthetic(self):
        """Test vinyl noise detection with synthetic signals."""
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # 1. Synthetic Vinyl Noise (White noise, low amplitude)
        np.random.seed(42)
        vinyl_noise = np.random.randn(len(t)) * 0.001  # ~ -60dB
        
        is_vinyl, details = detect_vinyl_noise(vinyl_noise, sample_rate, cutoff_freq=10000)
        
        # Note: Filter might affect energy, but white noise has energy everywhere
        # We expect energy > -70dB, low autocorr, low variance
        assert details['energy_db'] > -70
        assert details['autocorr'] < 0.3
        assert details['temporal_variance'] < 5.0
        assert is_vinyl == True

    def test_detect_vinyl_noise_digital_silence(self):
        """Test vinyl noise detection with digital silence."""
        sample_rate = 44100
        silence = np.zeros(44100)
        
        is_vinyl, details = detect_vinyl_noise(silence, sample_rate, cutoff_freq=10000)
        
        assert details['energy_db'] < -70
        assert is_vinyl == False

    def test_detect_clicks_synthetic(self):
        """Test click detection with synthetic clicks."""
        sample_rate = 44100
        duration = 60.0  # 1 minute to make clicks/min calculation easy
        audio = np.zeros(int(sample_rate * duration))
        
        # Add 10 clicks
        for i in range(10):
            idx = int((i + 1) * 5 * sample_rate)  # Every 5 seconds
            audio[idx] = 1.0  # Click
            
        num_clicks, cpm = detect_clicks_and_pops(audio, sample_rate)
        
        # Filter might reduce amplitude, but ideal click is broadband
        # We expect around 10 clicks
        assert num_clicks >= 5  # Allow some loss due to filtering/thresholding
        assert 5 <= cpm <= 15
