"""Tests pour le module de reporting."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from openpyxl import Workbook

from flac_detective.reporting.reporter import ExcelReporter
from flac_detective.reporting.statistics import calculate_statistics, filter_suspicious


class TestStatistics(unittest.TestCase):
    def setUp(self):
        self.results = [
            {"score": 100, "duration_mismatch": False},
            {"score": 80, "duration_mismatch": False},
            {"score": 60, "duration_mismatch": True, "diff_samples": 1000},
            {"score": 40, "duration_mismatch": True, "diff_samples": 50000},
        ]

    def test_calculate_statistics(self):
        stats = calculate_statistics(self.results)
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["authentic"], 1)  # 100
        self.assertEqual(stats["probably_authentic"], 1)  # 80
        self.assertEqual(stats["suspect"], 1)  # 60
        self.assertEqual(stats["fake"], 1)  # 40
        self.assertEqual(stats["duration_issues"], 2)
        self.assertEqual(stats["duration_issues_critical"], 1)  # > 44100 samples

    def test_filter_suspicious(self):
        suspicious = filter_suspicious(self.results, threshold=90)
        self.assertEqual(len(suspicious), 3)  # 80, 60, 40
        self.assertNotIn({"score": 100, "duration_mismatch": False}, suspicious)


class TestExcelReporter(unittest.TestCase):
    def setUp(self):
        self.reporter = ExcelReporter()
        self.results = [
            {
                "filepath": "/path/to/fake.flac",
                "filename": "fake.flac",
                "score": 40,
                "reason": "Coupure 16kHz",
                "cutoff_freq": 16000,
                "sample_rate": 44100,
                "bit_depth": 16,
                "encoder": "Lavf",
                "duration_mismatch": False,
            }
        ]

    def test_generate_report(self):
        """Vérifie que le rapport est généré et sauvegardé."""
        with patch("openpyxl.workbook.Workbook.save") as mock_save:
            output_path = Path("report.xlsx")
            self.reporter.generate_report(self.results, output_path)

            # Vérifier que save a été appelé
            mock_save.assert_called_once_with(output_path)

            # Vérifier le contenu (sommaire)
            ws = self.reporter.wb["Fichiers Suspects"]
            self.assertEqual(ws["A2"].value, "/path/to/fake.flac")
            self.assertEqual(ws["C2"].value, 40)


if __name__ == "__main__":
    unittest.main()
