"""Tests pour le module principal main.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flac_detective.main import (
    _clean_path_string,
    _parse_multiple_paths,
    _validate_paths,
    get_user_input_path,
    main,
)


class TestMainHelpers:
    """Tests des fonctions helper de main.py."""

    def test_parse_multiple_paths(self):
        """Vérifie le parsing des chemins multiples."""
        # Cas simple
        assert _parse_multiple_paths("path1") == ["path1"]
        
        # Séparateur point-virgule
        assert _parse_multiple_paths("path1; path2") == ["path1", "path2"]
        
        # Séparateur virgule
        assert _parse_multiple_paths("path1, path2,path3") == ["path1", "path2", "path3"]

    def test_clean_path_string(self):
        """Vérifie le nettoyage des guillemets."""
        assert _clean_path_string('"path/to/file"') == "path/to/file"
        assert _clean_path_string("'path/to/file'") == "path/to/file"
        assert _clean_path_string("path/to/file") == "path/to/file"

    @patch("flac_detective.main.Path")
    def test_validate_paths(self, mock_path):
        """Vérifie la validation des chemins."""
        # Setup mock
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        
        # Cas 1: Chemin existant
        mock_path_instance.exists.return_value = True
        result = _validate_paths(["valid_path"])
        assert len(result) == 1
        assert result[0] == mock_path_instance
        
        # Cas 2: Chemin inexistant
        mock_path_instance.exists.return_value = False
        result = _validate_paths(["invalid_path"])
        assert len(result) == 0


class TestMainInteractive:
    """Tests du mode interactif."""

    @patch("builtins.input")
    @patch("flac_detective.main._validate_paths")
    def test_get_user_input_path_success(self, mock_validate, mock_input):
        """Vérifie la saisie utilisateur réussie."""
        mock_input.return_value = "path1"
        mock_validate.return_value = [Path("path1")]
        
        result = get_user_input_path()
        assert result == [Path("path1")]

    @patch("builtins.input")
    def test_get_user_input_path_empty(self, mock_input):
        """Vérifie le cas d'une entrée vide (dossier courant)."""
        mock_input.return_value = ""
        result = get_user_input_path()
        assert result == [Path.cwd()]

    @patch("builtins.input")
    @patch("sys.exit")
    def test_get_user_input_path_interrupt(self, mock_exit, mock_input):
        """Vérifie l'interruption clavier."""
        mock_input.side_effect = KeyboardInterrupt
        get_user_input_path()
        mock_exit.assert_called_with(0)


class TestMainFunction:
    """Tests de la fonction main()."""

    @patch("flac_detective.main.get_user_input_path")
    @patch("flac_detective.main.find_flac_files")
    @patch("flac_detective.main.FLACAnalyzer")
    @patch("flac_detective.main.ProgressTracker")
    @patch("flac_detective.main.TextReporter")
    @patch("flac_detective.main.ThreadPoolExecutor")
    @patch("flac_detective.main.as_completed")
    def test_main_interactive_success(
        self, mock_as_completed, mock_executor, mock_reporter, mock_tracker, mock_analyzer, mock_find, mock_input
    ):
        """Test complet du flux main en mode interactif."""
        # Setup mocks
        mock_path = MagicMock(spec=Path)
        mock_path.is_dir.return_value = True
        mock_path.is_file.return_value = False
        # Important: permettre l'accès à .parent et / operator
        mock_path.parent = mock_path
        mock_path.__truediv__.return_value = mock_path
        
        mock_input.return_value = [mock_path]
        mock_find.return_value = [Path("/music/song.flac")]
        
        # Mock tracker
        tracker_instance = mock_tracker.return_value
        tracker_instance.is_processed.return_value = False
        tracker_instance.get_progress.return_value = (0, 1)
        tracker_instance.get_results.return_value = [{"score": 100, "filename": "song.flac"}]
        
        # Mock executor & future
        executor_instance = mock_executor.return_value
        executor_instance.__enter__.return_value = executor_instance
        
        mock_future = MagicMock()
        mock_future.result.return_value = {"score": 100, "filename": "song.flac"}
        executor_instance.submit.return_value = mock_future
        
        # Mock as_completed to return our future
        mock_as_completed.return_value = [mock_future]
        
        # Run main
        with patch.object(sys, "argv", ["main.py"]):
            main()
            
        # Vérifications
        mock_find.assert_called()
        mock_analyzer.assert_called()
        mock_tracker.assert_called()
        executor_instance.submit.assert_called()
        mock_reporter.return_value.generate_report.assert_called()

    @patch("flac_detective.main.find_flac_files")
    def test_main_no_files(self, mock_find):
        """Test main quand aucun fichier n'est trouvé."""
        mock_find.return_value = []
        
        with patch.object(sys, "argv", ["main.py", "/empty"]), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.is_dir", return_value=True):
            
            # Devrait retourner sans erreur
            main()

    def test_main_invalid_args(self):
        """Test main avec arguments invalides."""
        with patch.object(sys, "argv", ["main.py", "/invalid"]), \
             patch("pathlib.Path.exists", return_value=False), \
             patch("sys.exit") as mock_exit:
            
            main()
            mock_exit.assert_called_with(1)
