"""Tests pour le module utils."""

import unittest
from pathlib import Path
from unittest.mock import patch

from flac_detective.utils import find_flac_files


class TestUtils(unittest.TestCase):
    def test_find_flac_files(self):
        """Vérifie la recherche récursive de fichiers FLAC."""
        with patch("pathlib.Path.rglob") as mock_rglob:
            # Simuler des fichiers trouvés
            mock_rglob.return_value = [
                Path("/music/album1/track1.flac"),
                Path("/music/album2/track1.flac"),
            ]

            root = Path("/music")
            files = find_flac_files(root)

            self.assertEqual(len(files), 2)
            self.assertEqual(files[0].name, "track1.flac")
            mock_rglob.assert_called_once_with("*.flac")


if __name__ == "__main__":
    unittest.main()
