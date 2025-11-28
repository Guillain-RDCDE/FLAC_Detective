"""Tests pour le module d'analyse de qualité audio."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from flac_detective.analysis.quality import (
    analyze_audio_quality,
    detect_clipping,
    detect_corruption,
    detect_dc_offset,
)


class TestQualityAnalysis:
    """Tests des fonctions d'analyse de qualité."""

    def test_detect_clipping_no_clipping(self):
        """Vérifie la détection sans clipping."""
        # Signal normal sans clipping
        data = np.random.rand(44100) * 0.5  # Amplitude max 0.5
        result = detect_clipping(data)

        assert result["has_clipping"] is False
        assert result["clipping_percentage"] == 0.0
        assert result["clipped_samples"] == 0
        assert result["severity"] == "none"

    def test_detect_clipping_with_clipping(self):
        """Vérifie la détection avec clipping."""
        # Signal avec clipping
        data = np.ones(44100)  # Tous les échantillons à 1.0
        result = detect_clipping(data)

        assert result["has_clipping"] is True
        assert result["clipping_percentage"] == 100.0
        assert result["clipped_samples"] == 44100
        assert result["severity"] == "severe"

    def test_detect_clipping_light(self):
        """Vérifie la détection de clipping léger."""
        data = np.random.rand(44100) * 0.5
        # Ajouter quelques pics
        data[100:105] = 0.995
        result = detect_clipping(data)

        assert result["has_clipping"] is False  # < 0.01%
        assert result["severity"] == "light"

    def test_detect_clipping_stereo(self):
        """Vérifie la détection sur signal stéréo."""
        # Signal stéréo avec clipping
        data = np.ones((44100, 2))
        result = detect_clipping(data)

        assert result["has_clipping"] is True
        assert result["clipped_samples"] == 88200  # 2 canaux

    def test_detect_dc_offset_no_offset(self):
        """Vérifie la détection sans DC offset."""
        # Signal centré sur zéro
        data = np.sin(np.linspace(0, 2 * np.pi, 44100))
        result = detect_dc_offset(data)

        assert result["has_dc_offset"] is False
        assert abs(result["dc_offset_value"]) < 0.001
        assert result["severity"] == "none"

    def test_detect_dc_offset_with_offset(self):
        """Vérifie la détection avec DC offset."""
        # Signal avec offset de 0.1
        data = np.sin(np.linspace(0, 2 * np.pi, 44100)) + 0.1
        result = detect_dc_offset(data)

        assert result["has_dc_offset"] is True
        assert abs(result["dc_offset_value"] - 0.1) < 0.01
        assert result["severity"] == "severe"

    def test_detect_dc_offset_stereo(self):
        """Vérifie la détection sur signal stéréo."""
        # Signal stéréo avec offset
        data = np.ones((44100, 2)) * 0.05
        result = detect_dc_offset(data)

        assert result["has_dc_offset"] is True
        assert result["severity"] == "severe"

    @patch("soundfile.read")
    def test_detect_corruption_valid_file(self, mock_read):
        """Vérifie la détection sur fichier valide."""
        mock_data = np.random.rand(44100).astype('float32')
        mock_read.return_value = (mock_data, 44100)

        result = detect_corruption(Path("test.flac"))

        assert result["is_corrupted"] is False
        assert result["readable"] is True
        assert result["error"] is None
        assert result["frames_read"] == 44100

    @patch("soundfile.read")
    def test_detect_corruption_read_error(self, mock_read):
        """Vérifie la détection d'erreur de lecture."""
        mock_read.side_effect = Exception("Read error")

        result = detect_corruption(Path("test.flac"))

        assert result["is_corrupted"] is True
        assert result["readable"] is False
        assert "Read error" in result["error"]
        assert result["frames_read"] == 0

    @patch("soundfile.read")
    def test_detect_corruption_empty_file(self, mock_read):
        """Vérifie la détection de fichier vide."""
        mock_read.return_value = (np.array([]), 44100)

        result = detect_corruption(Path("test.flac"))

        assert result["is_corrupted"] is True
        assert result["readable"] is False
        assert "No data" in result["error"]

    @patch("soundfile.read")
    def test_detect_corruption_nan_values(self, mock_read):
        """Vérifie la détection de valeurs NaN."""
        data = np.random.rand(44100).astype('float32')
        data[100] = np.nan
        mock_read.return_value = (data, 44100)

        result = detect_corruption(Path("test.flac"))

        assert result["is_corrupted"] is True
        assert result["readable"] is True
        assert "NaN" in result["error"]

    @patch("soundfile.read")
    def test_analyze_audio_quality_complete(self, mock_read):
        """Vérifie l'analyse complète de qualité."""
        # Signal avec léger clipping et DC offset
        data = np.random.rand(44100).astype('float32') * 0.9 + 0.05
        data[100:110] = 0.995
        mock_read.return_value = (data, 44100)

        result = analyze_audio_quality(Path("test.flac"))

        assert "corruption" in result
        assert "clipping" in result
        assert "dc_offset" in result
        assert result["corruption"]["is_corrupted"] is False

    @patch("flac_detective.analysis.quality.detect_corruption")
    def test_analyze_audio_quality_corrupted_file(self, mock_detect_corruption):
        """Vérifie l'analyse sur fichier corrompu."""
        mock_detect_corruption.return_value = {
            "is_corrupted": True,
            "readable": False,
            "error": "Corrupted",
            "frames_read": 0,
        }

        result = analyze_audio_quality(Path("test.flac"))

        # Si corrompu, les autres analyses ne sont pas effectuées
        assert result["corruption"]["is_corrupted"] is True
        assert result["clipping"]["severity"] == "unknown"
        assert result["dc_offset"]["severity"] == "unknown"
