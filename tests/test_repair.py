"""Tests pour le module de réparation."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from flac_detective.repair.fixer import FLACDurationFixer


class TestFLACDurationFixer(unittest.TestCase):
    def setUp(self):
        self.fixer = FLACDurationFixer(create_backup=True)
        self.filepath = Path("test_song.flac")

    @patch("flac_detective.repair.fixer.shutil.copy2")
    @patch("flac_detective.repair.fixer.reencode_flac")
    @patch("flac_detective.repair.fixer.extract_all_metadata")
    @patch("flac_detective.repair.fixer.restore_all_metadata")
    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.rename")
    @patch("pathlib.Path.exists")
    def test_fix_file_success(
        self,
        mock_exists,
        mock_rename,
        mock_unlink,
        mock_restore,
        mock_extract,
        mock_reencode,
        mock_copy,
    ):
        """Test une réparation complète réussie."""
        # Setup mocks
        mock_exists.return_value = True
        
        # 1. Check mismatch (mocking internal method)
        with patch.object(self.fixer, "check_duration_mismatch") as mock_check:
            # Premier appel (avant réparation) : Problème détecté
            # Deuxième appel (après réparation) : Problème résolu
            mock_check.side_effect = [
                {"has_mismatch": True, "diff_samples": 1000, "diff_ms": 22.5},
                {"has_mismatch": False, "diff_samples": 0, "diff_ms": 0},
            ]

            mock_extract.return_value = {"success": True, "tags": {}, "pictures": []}
            mock_reencode.return_value = True
            mock_restore.return_value = True

            # Execute
            try:
                result = self.fixer.fix_file(self.filepath, dry_run=False)
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise e

            # Verify
            self.assertTrue(result["success"])
            self.assertEqual(result["message"], "Réparé avec succès")
            
            # Vérifier les étapes
            mock_check.assert_called()
            mock_extract.assert_called_once()
            mock_copy.assert_called_once()  # Backup
            mock_reencode.assert_called_once()
            mock_restore.assert_called_once()
            mock_rename.assert_called_once() # Remplacement final
            # mock_exists n'est pas appelé dans le chemin du succès

    def test_fix_file_no_mismatch(self):
        """Test si le fichier n'a pas de problème."""
        with patch.object(self.fixer, "check_duration_mismatch") as mock_check:
            mock_check.return_value = {"has_mismatch": False}

            result = self.fixer.fix_file(self.filepath)

            self.assertFalse(result["success"])
            self.assertTrue(result["skipped"])
            self.assertEqual(self.fixer.skip_count, 1)

    def test_fix_file_dry_run(self):
        """Test le mode simulation."""
        with patch.object(self.fixer, "check_duration_mismatch") as mock_check:
            mock_check.return_value = {"has_mismatch": True, "diff_samples": 1000, "diff_ms": 22.5}

            result = self.fixer.fix_file(self.filepath, dry_run=True)

            self.assertTrue(result["success"])
            self.assertTrue(result["dry_run"])
            # Vérifier qu'aucune action destructive n'a été faite
            # (les mocks globaux ne sont pas patchés ici mais reencode/restore ne sont pas appelés)

    @patch("flac_detective.repair.fixer.reencode_flac")
    @patch("flac_detective.repair.fixer.extract_all_metadata")
    @patch("pathlib.Path.unlink")
    def test_fix_file_reencode_fail(self, mock_unlink, mock_extract, mock_reencode):
        """Test échec du ré-encodage."""
        self.fixer.create_backup = False  # Éviter shutil.copy2
        with patch.object(self.fixer, "check_duration_mismatch") as mock_check:
            mock_check.return_value = {"has_mismatch": True, "diff_samples": 1000, "diff_ms": 22.5}
            mock_extract.return_value = {"success": True, "tags": {}, "pictures": []}
            mock_reencode.return_value = False  # Échec

            result = self.fixer.fix_file(self.filepath)

            self.assertFalse(result["success"])
            self.assertEqual(result["message"], "Erreur ré-encodage")
            self.assertEqual(self.fixer.error_count, 1)


if __name__ == "__main__":
    unittest.main()
