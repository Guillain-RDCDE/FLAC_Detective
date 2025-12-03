

class TestRule8NyquistException:
    """Test Rule 8: Nyquist Exception."""
    
    def test_strong_bonus_98_percent(self):
        """Test strong bonus for cutoff >= 98% of Nyquist."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # 44.1 kHz: Nyquist = 22050 Hz, 98% = 21609 Hz
        score, reasons = apply_rule_8_nyquist_exception(21800, 44100, None, None)
        
        assert score == -50
        assert "98" in reasons[0] or "Très proche limite" in reasons[0]
        assert len(reasons) == 1
        
    def test_moderate_bonus_95_percent(self):
        """Test moderate bonus for cutoff between 95-98% of Nyquist."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # 44.1 kHz: Nyquist = 22050 Hz, 95% = 20947 Hz, 98% = 21609 Hz
        score, reasons = apply_rule_8_nyquist_exception(21000, 44100, None, None)
        
        assert score == -30
        assert "95" in reasons[0]  # Check for 95% threshold
        assert "Probablement authentique" in reasons[0]
        
    def test_no_bonus_below_95_percent(self):
        """Test no bonus for cutoff < 95% of Nyquist."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # 44.1 kHz: Nyquist = 22050 Hz, 95% = 20947 Hz
        score, reasons = apply_rule_8_nyquist_exception(20000, 44100, None, None)
        
        assert score == 0
        assert not reasons
        
    def test_cancelled_by_mp3_signature_and_dither(self):
        """Test bonus CANCELLED when MP3 signature + dither suspect (ratio > 0.2)."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # High cutoff but MP3 detected and high silence ratio (dither)
        score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.3)
        
        assert score == 0
        assert len(reasons) == 1
        assert "annulé" in reasons[0]
        assert "dither suspect" in reasons[0]
        
    def test_applied_with_authentic_silence(self):
        """Test bonus APPLIED when MP3 signature but authentic silence (ratio <= 0.15)."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # MP3 detected but silence ratio indicates authentic
        score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.05)
        
        assert score == -50
        assert len(reasons) == 1
        assert "MP3 signature mais silence authentique" in reasons[0]
        
    def test_reduced_in_grey_zone(self):
        """Test bonus REDUCED when MP3 signature + grey zone (0.15 < ratio <= 0.2)."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # MP3 detected and silence ratio in grey zone
        score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.18)
        
        assert score == -15
        assert len(reasons) == 1
        assert "Bonus réduit" in reasons[0]
        assert "zone grise" in reasons[0]
        
    def test_different_sample_rates(self):
        """Test with different sample rates."""
        from flac_detective.analysis.new_scoring.rules import apply_rule_8_nyquist_exception
        
        # 48 kHz: Nyquist = 24000 Hz, 98% = 23520 Hz
        score, reasons = apply_rule_8_nyquist_exception(23600, 48000, None, None)
        assert score == -50
        
        # 96 kHz: Nyquist = 48000 Hz, 95% = 45600 Hz
        score, reasons = apply_rule_8_nyquist_exception(46000, 96000, None, None)
        assert score == -30
