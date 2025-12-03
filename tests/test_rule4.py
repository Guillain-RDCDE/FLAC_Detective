"""Tests for Rule 4: 24-bit Suspicious Files with safeguards."""

import pytest
from flac_detective.analysis.new_scoring.rules import apply_rule_4_24bit_suspect


class TestRule4Safeguards:
    """Test Rule 4 with new safeguards against false positives."""

    def test_rule4_triggers_on_suspicious_24bit_upscaling(self):
        """Rule 4 should trigger on 24-bit file with low MP3 source and low cutoff."""
        # 24-bit file with MP3 192 kbps source and cutoff at 17 kHz (very low)
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=192,
            cutoff_freq=17000,
            silence_ratio=None
        )
        
        assert score == 30, "Should penalize 24-bit with low MP3 source and low cutoff"
        assert len(reasons) == 1
        assert "upscale suspect" in reasons[0].lower()

    def test_rule4_skips_when_cutoff_is_high(self):
        """Rule 4 should NOT trigger if cutoff is >= 19 kHz (acceptable for 24-bit)."""
        # 24-bit file with MP3 source but cutoff at 20 kHz (natural for vinyl)
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=192,
            cutoff_freq=20000,  # Above 19 kHz threshold
            silence_ratio=None
        )
        
        assert score == 0, "Should NOT penalize 24-bit with acceptable cutoff"
        assert len(reasons) == 0

    def test_rule4_protects_vinyl_rips(self):
        """Rule 4 should NOT trigger on vinyl rips (silence_ratio < 0.15)."""
        # 24-bit vinyl rip with low MP3-like cutoff but vinyl noise detected
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=192,
            cutoff_freq=17000,  # Low cutoff
            silence_ratio=0.10  # Vinyl noise detected (< 0.15)
        )
        
        assert score == 0, "Should protect authentic vinyl rips"
        assert len(reasons) == 0

    def test_rule4_triggers_when_vinyl_ratio_is_high(self):
        """Rule 4 should trigger if silence_ratio >= 0.15 (not a vinyl)."""
        # 24-bit file with low MP3 source, low cutoff, and high silence ratio
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=192,
            cutoff_freq=17000,
            silence_ratio=0.25  # Not a vinyl (>= 0.15)
        )
        
        assert score == 30, "Should penalize when not a vinyl rip"
        assert len(reasons) == 1

    def test_rule4_skips_on_16bit(self):
        """Rule 4 should NOT trigger on 16-bit files."""
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=16,
            mp3_bitrate_detected=192,
            cutoff_freq=17000,
            silence_ratio=None
        )
        
        assert score == 0, "Should skip 16-bit files"
        assert len(reasons) == 0

    def test_rule4_skips_when_no_mp3_detected(self):
        """Rule 4 should NOT trigger if no MP3 source detected."""
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=None,  # No MP3 detected
            cutoff_freq=17000,
            silence_ratio=None
        )
        
        assert score == 0, "Should skip when no MP3 source detected"
        assert len(reasons) == 0

    def test_rule4_skips_when_mp3_bitrate_is_high(self):
        """Rule 4 should NOT trigger if MP3 bitrate >= 500 kbps."""
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=600,  # High bitrate
            cutoff_freq=17000,
            silence_ratio=None
        )
        
        assert score == 0, "Should skip when MP3 bitrate is high"
        assert len(reasons) == 0

    def test_rule4_edge_case_cutoff_exactly_19khz(self):
        """Rule 4 should NOT trigger when cutoff is exactly 19 kHz."""
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=192,
            cutoff_freq=19000,  # Exactly at threshold
            silence_ratio=None
        )
        
        assert score == 0, "Should NOT trigger at exactly 19 kHz"
        assert len(reasons) == 0

    def test_rule4_edge_case_silence_ratio_exactly_015(self):
        """Rule 4 should trigger when silence_ratio is exactly 0.15."""
        score, reasons = apply_rule_4_24bit_suspect(
            bit_depth=24,
            mp3_bitrate_detected=192,
            cutoff_freq=17000,
            silence_ratio=0.15  # Exactly at threshold
        )
        
        assert score == 30, "Should trigger at exactly 0.15 (not < 0.15)"
        assert len(reasons) == 1
