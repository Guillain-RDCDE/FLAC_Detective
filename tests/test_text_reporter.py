"""Tests pour le module de reporting texte."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from flac_detective.reporting.text_reporter import TextReporter


class TestTextReporter(unittest.TestCase):
    def setUp(self):
        self.reporter = TextReporter()
        self.results = [
            {
                "filepath": "/music/authentic.flac",
                "filename": "authentic.flac",
                "score": 100,
                "reason": "Parfait",
                "cutoff_freq": 22050,
                "duration_mismatch": False,
            },
            {
                "filepath": "/music/fake.flac",
                "filename": "fake.flac",
                "score": 30,
                "reason": "Coupure 16kHz",
                "cutoff_freq": 16000,
                "duration_mismatch": True,
                "duration_diff": 1500,
            },
            {
                "filepath": "/music/suspect.flac",
                "filename": "suspect.flac",
                "score": 60,
                "reason": "Énergie faible",
                "cutoff_freq": 18000,
                "duration_mismatch": False,
            },
        ]

    def test_generate_report(self):
        """Vérifie que le rapport texte est généré correctement."""
        with TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test_report.txt"
            self.reporter.generate_report(self.results, output_file)

            # Vérifier que le fichier existe
            self.assertTrue(output_file.exists())

            # Lire et vérifier le contenu
            content = output_file.read_text(encoding="utf-8")

            # Vérifier la présence d'éléments clés
            self.assertIn("FLAC DETECTIVE", content)
            self.assertIn("STATISTIQUES GLOBALES", content)
            self.assertIn("FICHIERS SUSPECTS", content)
            self.assertIn("RECOMMANDATIONS", content)

            # Vérifier les fichiers suspects
            self.assertIn("fake.flac", content)
            self.assertIn("suspect.flac", content)
            self.assertNotIn("authentic.flac", content)  # Score >= 90, pas dans suspects

            # Vérifier les scores
            self.assertIn("30%", content)
            self.assertIn("60%", content)

    def test_score_icons(self):
        """Vérifie les icônes de score."""
        self.assertEqual(self.reporter._score_icon(100), "✓✓✓")
        self.assertEqual(self.reporter._score_icon(80), "✓✓ ")
        self.assertEqual(self.reporter._score_icon(60), "✓  ")
        self.assertEqual(self.reporter._score_icon(30), "✗✗✗")

    def test_score_labels(self):
        """Vérifie les labels de score."""
        self.assertEqual(self.reporter._score_label(95), "AUTHENTIQUE")
        self.assertEqual(self.reporter._score_label(75), "PROB. AUTH.")
        self.assertEqual(self.reporter._score_label(55), "SUSPECT")
        self.assertEqual(self.reporter._score_label(25), "FAKE")


if __name__ == "__main__":
    unittest.main()
