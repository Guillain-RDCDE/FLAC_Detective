"""Tests pour l'analyseur principal."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from flac_detective.analysis.analyzer import FLACAnalyzer


class TestFLACAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = FLACAnalyzer()

    @patch("flac_detective.analysis.analyzer.calculate_score")
    @patch("flac_detective.analysis.analyzer.analyze_spectrum")
    @patch("flac_detective.analysis.analyzer.check_duration_consistency")
    @patch("flac_detective.analysis.analyzer.read_metadata")
    def test_analyze_file_mock(
        self, mock_read_meta, mock_check_duration, mock_analyze_spectrum, mock_calc_score
    ):
        # Configuration des mocks
        mock_read_meta.return_value = {
            "sample_rate": 44100,
            "bit_depth": 16,
            "encoder": "reference libFLAC",
        }
        mock_check_duration.return_value = {
            "mismatch": False,
            "metadata_duration": "100s",
            "real_duration": "100s",
            "diff_samples": 0,
        }
        mock_analyze_spectrum.return_value = (22000, 0.01)
        mock_calc_score.return_value = (100, "Spectre complet")

        # Exécution
        result = self.analyzer.analyze_file(Path("test.flac"))

        # Vérifications
        self.assertEqual(result["filename"], "test.flac")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["reason"], "Spectre complet")
        self.assertEqual(result["cutoff_freq"], 22000)

        # Vérifier que les fonctions ont été appelées
        mock_read_meta.assert_called_once()
        mock_check_duration.assert_called_once()
        mock_analyze_spectrum.assert_called_once()
        mock_calc_score.assert_called_once()


if __name__ == "__main__":
    unittest.main()
