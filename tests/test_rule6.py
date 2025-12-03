"""Tests for Rule 6: High Quality Protection (Reinforced)."""

from flac_detective.analysis.new_scoring.rules import apply_rule_6_variable_bitrate_protection


class TestRule6HighQualityProtection:
    """Test Rule 6: High Quality Protection (Reinforced)."""
    
    def test_all_conditions_met(self):
        """Test bonus when all conditions are met."""
        # No MP3, high bitrate, high cutoff, high variance
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=800,
            cutoff_freq=20000,
            bitrate_variance=100
        )
        
        assert score == -30
        assert "Haute qualité confirmée" in reasons[0]
        assert "800" in reasons[0]
        assert "20000" in reasons[0]
        assert "100" in reasons[0]
        
    def test_mp3_detected_blocks_bonus(self):
        """Test that MP3 signature blocks the bonus."""
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=320,
            bitrate_conteneur=800,
            cutoff_freq=20000,
            bitrate_variance=100
        )
        
        assert score == 0
        assert not reasons
        
    def test_low_bitrate_blocks_bonus(self):
        """Test that bitrate <= 700 kbps blocks the bonus."""
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=650,  # Below 700 threshold
            cutoff_freq=20000,
            bitrate_variance=100
        )
        
        assert score == 0
        assert not reasons
        
    def test_low_cutoff_blocks_bonus(self):
        """Test that cutoff < 19000 Hz blocks the bonus."""
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=800,
            cutoff_freq=18000,  # Below 19000 threshold
            bitrate_variance=100
        )
        
        assert score == 0
        assert not reasons
        
    def test_low_variance_blocks_bonus(self):
        """Test that variance <= 50 kbps blocks the bonus."""
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=800,
            cutoff_freq=20000,
            bitrate_variance=40  # Below 50 threshold
        )
        
        assert score == 0
        assert not reasons
        
    def test_edge_case_exact_thresholds(self):
        """Test edge cases at exact threshold values."""
        # Bitrate exactly at 700 - should NOT trigger
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=700,
            cutoff_freq=20000,
            bitrate_variance=100
        )
        assert score == 0
        
        # Cutoff exactly at 19000 - SHOULD trigger
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=701,
            cutoff_freq=19000,
            bitrate_variance=100
        )
        assert score == -30
        
        # Variance exactly at 50 - should NOT trigger
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=800,
            cutoff_freq=20000,
            bitrate_variance=50
        )
        assert score == 0
        
        # Variance at 51 - SHOULD trigger
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=701,
            cutoff_freq=19000,
            bitrate_variance=51
        )
        assert score == -30
        
    def test_high_quality_authentic_file(self):
        """Test typical high-quality authentic FLAC."""
        score, reasons = apply_rule_6_variable_bitrate_protection(
            mp3_bitrate_detected=None,
            bitrate_conteneur=1200,
            cutoff_freq=21500,
            bitrate_variance=150
        )
        
        assert score == -30
        assert "Authentique" in reasons[0]
