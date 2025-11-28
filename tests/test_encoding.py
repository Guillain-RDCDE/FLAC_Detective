"""Tests pour le module d'encodage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from flac_detective.repair.encoding import reencode_flac


class TestEncoding:
    """Tests des fonctions d'encodage FLAC."""

    @patch("soundfile.read")
    @patch("soundfile.write")
    def test_reencode_flac_success(self, mock_write, mock_read):
        """Vérifie le ré-encodage réussi."""
        # Simuler la lecture d'un fichier audio
        mock_data = np.random.rand(44100, 2).astype('float32')  # 1 seconde stéréo
        mock_read.return_value = (mock_data, 44100)
        
        input_path = Path("input.flac")
        output_path = Path("output.flac")
        
        assert reencode_flac(input_path, output_path, compression_level=5) is True
        
        # Vérifier que read a été appelé
        mock_read.assert_called_once_with(input_path, dtype='float32')
        
        # Vérifier que write a été appelé avec les bons paramètres
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        assert call_args[0][0] == output_path
        assert np.array_equal(call_args[0][1], mock_data)
        assert call_args[0][2] == 44100
        assert call_args[1]['format'] == 'FLAC'
        assert call_args[1]['subtype'] == 'PCM_16'

    @patch("soundfile.read")
    @patch("soundfile.write")
    def test_reencode_flac_different_compression_levels(self, mock_write, mock_read):
        """Vérifie les différents niveaux de compression."""
        mock_data = np.random.rand(44100).astype('float32')
        mock_read.return_value = (mock_data, 44100)
        
        # Test niveau 0
        reencode_flac(Path("in.flac"), Path("out.flac"), compression_level=0)
        assert mock_write.call_args[1]['subtype'] == 'PCM_16'
        
        # Test niveau 8
        reencode_flac(Path("in.flac"), Path("out.flac"), compression_level=8)
        assert mock_write.call_args[1]['subtype'] == 'PCM_24'

    @patch("soundfile.read")
    def test_reencode_flac_read_error(self, mock_read):
        """Vérifie la gestion des erreurs de lecture."""
        mock_read.side_effect = Exception("Read error")
        
        assert reencode_flac(Path("in.flac"), Path("out.flac")) is False

    @patch("soundfile.read")
    @patch("soundfile.write")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    def test_reencode_flac_write_error_cleanup(
        self, mock_unlink, mock_exists, mock_write, mock_read
    ):
        """Vérifie le nettoyage en cas d'erreur d'écriture."""
        mock_data = np.random.rand(44100).astype('float32')
        mock_read.return_value = (mock_data, 44100)
        mock_write.side_effect = Exception("Write error")
        mock_exists.return_value = True
        
        output_path = Path("out.flac")
        assert reencode_flac(Path("in.flac"), output_path) is False
        
        # Vérifier que le fichier de sortie est supprimé en cas d'erreur
        mock_unlink.assert_called_once()

    @patch("soundfile.read")
    @patch("soundfile.write")
    def test_reencode_flac_default_compression(self, mock_write, mock_read):
        """Vérifie l'utilisation du niveau de compression par défaut."""
        mock_data = np.random.rand(44100).astype('float32')
        mock_read.return_value = (mock_data, 44100)
        
        # Sans spécifier compression_level, devrait utiliser la config par défaut
        reencode_flac(Path("in.flac"), Path("out.flac"))
        
        mock_write.assert_called_once()
        # Le niveau par défaut dans config est 5, qui mappe à PCM_16
        assert mock_write.call_args[1]['subtype'] == 'PCM_16'

