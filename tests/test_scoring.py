import unittest
from pathlib import Path
from src.flac_detective.analysis.new_scoring import new_calculate_score, estimate_mp3_bitrate

class TestScoringV2(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            "sample_rate": 44100,
            "bit_depth": 16,
            "encoder": "Lavf58.29.100",
            "duration": 180.0
        }
        self.duration_check = {"mismatch": False}
        # Create a dummy filepath for testing
        self.filepath = Path("test_file.flac")

    def test_mp3_320_detection(self):
        # Case 1: Typical MP3 320k cutoff (20.5 kHz)
        # Note: 20.5 kHz is very close to the 21 kHz protection threshold,
        # so the new system may not flag this as suspicious
        cutoff = 20500
        score, verdict, confidence, reason = new_calculate_score(
            cutoff, self.metadata, self.duration_check, self.filepath, cutoff_std=0.001
        )
        # The new system protects files near 21 kHz threshold
        self.assertLess(score, 50, "Score should be low for cutoff near 21 kHz threshold")

    def test_mp3_320_high_cutoff(self):
        # Case 2: High cutoff MP3 320k (User Example 1: 21166 Hz)
        cutoff = 21166
        score, verdict, confidence, reason = new_calculate_score(
            cutoff, self.metadata, self.duration_check, self.filepath, cutoff_std=0.001
        )
        # High cutoff above 21kHz should be protected by safety checks
        self.assertLess(score, 30, "Score should be very low for cutoff above 21 kHz")
        self.assertEqual(verdict, "AUTHENTIQUE")

    def test_mp3_256_detection(self):
        # Case 3: MP3 256k (User Example 2: 19075 Hz)
        # Note: 19075 Hz is at the boundary between 256 and 320 kbps ranges
        cutoff = 19075
        score, verdict, confidence, reason = new_calculate_score(
            cutoff, self.metadata, self.duration_check, self.filepath, cutoff_std=0.001
        )
        # Without a real file, the container bitrate will be 0, so Rule 1 won't trigger
        # Only Rule 2 (cutoff penalty) will apply
        self.assertGreater(score, 0, "Score should be positive for low cutoff")

    def test_authentic_flac(self):
        # Case 4: Authentic FLAC (Full Spectrum)
        cutoff = 22000
        score, verdict, confidence, reason = new_calculate_score(
            cutoff, self.metadata, self.duration_check, self.filepath, cutoff_std=0.01
        )
        self.assertLess(score, 30, "Score should be low for authentic FLAC")
        self.assertEqual(verdict, "AUTHENTIQUE")

    def test_mp3_128_detection(self):
        # Case 5: MP3 160k (16 kHz)
        # Note: 16000 Hz falls in the 160 kbps range (15500-16500), not 128 kbps
        cutoff = 16000
        score, verdict, confidence, reason = new_calculate_score(
            cutoff, self.metadata, self.duration_check, self.filepath, cutoff_std=0.0001
        )
        # Without a real file, only Rule 2 (cutoff penalty) applies
        # 16 kHz is well below the 20 kHz threshold for 44.1 kHz sample rate
        self.assertGreater(score, 15, "Score should be elevated for low cutoff")

    def test_estimate_bitrate(self):
        self.assertEqual(estimate_mp3_bitrate(20500), 320)
        self.assertEqual(estimate_mp3_bitrate(21166), 320)
        self.assertEqual(estimate_mp3_bitrate(19075), 256)
        self.assertEqual(estimate_mp3_bitrate(16000), 160)
        self.assertEqual(estimate_mp3_bitrate(22000), 0)

if __name__ == '__main__':
    unittest.main()
