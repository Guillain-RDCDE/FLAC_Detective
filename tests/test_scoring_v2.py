import unittest
from src.flac_detective.analysis.scoring import calculate_score, estimate_mp3_bitrate

class TestScoringV2(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            "sample_rate": 44100,
            "bit_depth": 16,
            "encoder": "Lavf58.29.100"
        }
        self.duration_check = {"mismatch": False}

    def test_mp3_320_detection(self):
        # Case 1: Typical MP3 320k cutoff (20.5 kHz)
        cutoff = 20500
        score, reason = calculate_score(cutoff, 0.001, self.metadata, self.duration_check)
        self.assertLess(score, 70, "Score should be low for MP3 320k")
        self.assertIn("matches MP3 320kbps", reason)

    def test_mp3_320_high_cutoff(self):
        # Case 2: High cutoff MP3 320k (User Example 1: 21166 Hz)
        cutoff = 21166
        score, reason = calculate_score(cutoff, 0.001, self.metadata, self.duration_check)
        self.assertLess(score, 70, "Score should be low for high cutoff MP3 320k")
        self.assertIn("matches MP3 320kbps", reason)

    def test_mp3_256_detection(self):
        # Case 3: MP3 256k (User Example 2: 19075 Hz)
        cutoff = 19075
        score, reason = calculate_score(cutoff, 0.001, self.metadata, self.duration_check)
        self.assertLess(score, 60, "Score should be low for MP3 256k")
        self.assertIn("matches MP3 256kbps", reason)

    def test_authentic_flac(self):
        # Case 4: Authentic FLAC (Full Spectrum)
        cutoff = 22000
        score, reason = calculate_score(cutoff, 0.01, self.metadata, self.duration_check)
        self.assertGreaterEqual(score, 90, "Score should be high for authentic FLAC")
        self.assertIn("Full spectrum", reason)

    def test_mp3_128_detection(self):
        # Case 5: MP3 128k (16 kHz)
        cutoff = 16000
        score, reason = calculate_score(cutoff, 0.0001, self.metadata, self.duration_check)
        self.assertLess(score, 30, "Score should be very low for MP3 128k")
        self.assertIn("matches MP3 160kbps", reason) # 16000 falls in 160k range (15.5-16.5)

    def test_estimate_bitrate(self):
        self.assertEqual(estimate_mp3_bitrate(20500), 320)
        self.assertEqual(estimate_mp3_bitrate(21166), 320)
        self.assertEqual(estimate_mp3_bitrate(19075), 256)
        self.assertEqual(estimate_mp3_bitrate(16000), 160)
        self.assertEqual(estimate_mp3_bitrate(22000), 0)

if __name__ == '__main__':
    unittest.main()
