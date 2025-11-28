"""Tests pour le module tracker."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flac_detective.tracker import ProgressTracker


class TestProgressTracker(unittest.TestCase):
    def setUp(self):
        # Créer un fichier temporaire pour chaque test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name) / "test_progress.json"
        self.tracker = ProgressTracker(progress_file=self.temp_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_state(self):
        """Vérifie l'état initial d'un nouveau tracker."""
        self.assertEqual(self.tracker.data["total_files"], 0)
        self.assertEqual(self.tracker.data["current_index"], 0)
        self.assertEqual(self.tracker.data["processed_files"], [])
        self.assertEqual(self.tracker.data["results"], [])

    def test_save_and_load(self):
        """Vérifie la persistance des données."""
        # Modifier les données
        self.tracker.set_total(100)
        self.tracker.add_result({"filepath": "test.flac", "score": 90})
        self.tracker.save()

        # Recharger dans une nouvelle instance
        new_tracker = ProgressTracker(progress_file=self.temp_path)
        self.assertEqual(new_tracker.data["total_files"], 100)
        self.assertEqual(len(new_tracker.data["results"]), 1)
        self.assertEqual(new_tracker.data["results"][0]["filepath"], "test.flac")

    def test_is_processed(self):
        """Vérifie la détection de fichiers déjà traités."""
        self.tracker.add_result({"filepath": "/path/to/file.flac", "score": 100})
        self.assertTrue(self.tracker.is_processed("/path/to/file.flac"))
        self.assertFalse(self.tracker.is_processed("/path/to/other.flac"))

    def test_corrupted_file(self):
        """Vérifie que le tracker gère un fichier JSON corrompu."""
        # Créer un fichier corrompu
        with open(self.temp_path, "w") as f:
            f.write("{invalid_json")

        # Le tracker doit démarrer à zéro sans crasher
        tracker = ProgressTracker(progress_file=self.temp_path)
        self.assertEqual(tracker.data["total_files"], 0)


if __name__ == "__main__":
    unittest.main()
