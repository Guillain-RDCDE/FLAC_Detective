"""Tests pour le module d'encodage."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from flac_detective.repair.encoding import (
    _decode_to_wav,
    _encode_from_wav,
    check_flac_tool_available,
    reencode_flac,
)


class TestEncoding:
    """Tests des fonctions d'encodage FLAC."""

    @patch("subprocess.run")
    def test_check_flac_tool_available_success(self, mock_run):
        """Vérifie la détection de l'outil flac."""
        mock_run.return_value.returncode = 0
        assert check_flac_tool_available() is True

    @patch("subprocess.run")
    def test_check_flac_tool_available_fail(self, mock_run):
        """Vérifie l'absence de l'outil flac."""
        mock_run.side_effect = FileNotFoundError
        assert check_flac_tool_available() is False

    @patch("subprocess.run")
    def test_decode_to_wav_success(self, mock_run):
        """Vérifie le décodage réussi."""
        mock_run.return_value.returncode = 0
        assert _decode_to_wav(Path("input.flac"), Path("temp.wav")) is True
        
        args = mock_run.call_args[0][0]
        assert args[0] == "flac"
        assert "--decode" in args

    @patch("subprocess.run")
    def test_decode_to_wav_fail(self, mock_run):
        """Vérifie l'échec du décodage."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Error"
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.unlink") as mock_unlink:
            assert _decode_to_wav(Path("input.flac"), Path("temp.wav")) is False
            mock_unlink.assert_called_once()

    @patch("subprocess.run")
    def test_encode_from_wav_success(self, mock_run):
        """Vérifie l'encodage réussi."""
        mock_run.return_value.returncode = 0
        assert _encode_from_wav(Path("temp.wav"), Path("output.flac"), 5) is True
        
        args = mock_run.call_args[0][0]
        assert "-5" in args

    @patch("flac_detective.repair.encoding.check_flac_tool_available")
    @patch("flac_detective.repair.encoding._decode_to_wav")
    @patch("flac_detective.repair.encoding._encode_from_wav")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    def test_reencode_flac_full_flow(
        self, mock_unlink, mock_exists, mock_encode, mock_decode, mock_check
    ):
        """Test le flux complet de ré-encodage."""
        mock_check.return_value = True
        mock_decode.return_value = True
        mock_encode.return_value = True
        mock_exists.return_value = True  # temp wav exists

        assert reencode_flac(Path("in.flac"), Path("out.flac")) is True
        
        mock_check.assert_called_once()
        mock_decode.assert_called_once()
        mock_encode.assert_called_once()
        mock_unlink.assert_called_once()  # Cleanup temp wav

    @patch("flac_detective.repair.encoding.check_flac_tool_available")
    def test_reencode_flac_tool_missing(self, mock_check):
        """Test quand l'outil est manquant."""
        mock_check.return_value = False
        assert reencode_flac(Path("in.flac"), Path("out.flac")) is False

    @patch("flac_detective.repair.encoding.check_flac_tool_available")
    @patch("flac_detective.repair.encoding._decode_to_wav")
    def test_reencode_flac_decode_fail(self, mock_decode, mock_check):
        """Test quand le décodage échoue."""
        mock_check.return_value = True
        mock_decode.return_value = False
        
        assert reencode_flac(Path("in.flac"), Path("out.flac")) is False
