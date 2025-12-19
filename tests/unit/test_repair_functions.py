"""Unit tests for FLAC repair functions.

Tests the metadata extraction, restoration, and repair functionality
introduced in v0.8.0.

NOTE: These tests require Python 3.8-3.12 due to scipy/numpy compatibility.
      Python 3.14+ may have compatibility issues with scipy.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from flac_detective.analysis.new_scoring.audio_loader import (
    _extract_metadata,
    _restore_metadata,
    repair_flac_file,
)


class TestExtractMetadata:
    """Tests for _extract_metadata() function."""

    def test_extract_metadata_success(self, tmp_path):
        """Test successful metadata extraction from a FLAC file."""
        # Create a mock FLAC file
        test_file = tmp_path / "test.flac"
        test_file.touch()

        # Mock the FLAC class
        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            # Setup mock
            mock_audio = MagicMock()
            mock_audio.tags = [
                ('TITLE', ['Test Song']),
                ('ARTIST', ['Test Artist']),
                ('ALBUM', ['Test Album']),
            ]
            mock_audio.pictures = [MagicMock()]  # One picture
            mock_flac.return_value = mock_audio

            # Call function
            result = _extract_metadata(str(test_file))

            # Assertions
            assert result is not None
            assert 'tags' in result
            assert 'pictures' in result
            assert len(result['tags']) == 3
            assert result['tags']['TITLE'] == ['Test Song']
            assert result['tags']['ARTIST'] == ['Test Artist']
            assert result['tags']['ALBUM'] == ['Test Album']
            assert len(result['pictures']) == 1

    def test_extract_metadata_no_tags(self, tmp_path):
        """Test extraction from FLAC file without tags."""
        test_file = tmp_path / "no_tags.flac"
        test_file.touch()

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_audio = MagicMock()
            mock_audio.tags = None
            mock_audio.pictures = []
            mock_flac.return_value = mock_audio

            result = _extract_metadata(str(test_file))

            assert result is not None
            assert result['tags'] == {}
            assert result['pictures'] == []

    def test_extract_metadata_multi_value_tags(self, tmp_path):
        """Test extraction of multi-value tags."""
        test_file = tmp_path / "multi.flac"
        test_file.touch()

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_audio = MagicMock()
            # Simulate multi-value tags
            mock_audio.tags = [
                ('ARTIST', ['Artist 1', 'Artist 2']),
                ('GENRE', ['Rock', 'Alternative']),
            ]
            mock_audio.pictures = []
            mock_flac.return_value = mock_audio

            result = _extract_metadata(str(test_file))

            assert 'ARTIST' in result['tags']
            assert len(result['tags']['ARTIST']) == 2
            assert 'Artist 1' in result['tags']['ARTIST']
            assert 'Artist 2' in result['tags']['ARTIST']

    def test_extract_metadata_mutagen_not_available(self, tmp_path):
        """Test behavior when Mutagen is not available."""
        test_file = tmp_path / "test.flac"
        test_file.touch()

        with patch('flac_detective.analysis.new_scoring.audio_loader.MUTAGEN_AVAILABLE', False):
            result = _extract_metadata(str(test_file))

            assert result is None

    def test_extract_metadata_exception_handling(self, tmp_path):
        """Test exception handling during metadata extraction."""
        test_file = tmp_path / "corrupt.flac"
        test_file.touch()

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_flac.side_effect = Exception("Cannot read file")

            result = _extract_metadata(str(test_file))

            assert result is None

    def test_extract_metadata_with_multiple_pictures(self, tmp_path):
        """Test extraction of multiple album art pictures."""
        test_file = tmp_path / "multi_pics.flac"
        test_file.touch()

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_audio = MagicMock()
            mock_audio.tags = []
            # Multiple pictures (front cover, back cover, etc.)
            mock_audio.pictures = [MagicMock(), MagicMock(), MagicMock()]
            mock_flac.return_value = mock_audio

            result = _extract_metadata(str(test_file))

            assert len(result['pictures']) == 3


class TestRestoreMetadata:
    """Tests for _restore_metadata() function."""

    def test_restore_metadata_success(self, tmp_path):
        """Test successful metadata restoration to a FLAC file."""
        test_file = tmp_path / "target.flac"
        test_file.touch()

        metadata = {
            'tags': {
                'TITLE': ['Restored Song'],
                'ARTIST': ['Restored Artist'],
                'ALBUM': ['Restored Album'],
            },
            'pictures': []
        }

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio

            result = _restore_metadata(str(test_file), metadata)

            assert result is True
            mock_audio.clear.assert_called_once()
            mock_audio.save.assert_called_once()
            # Verify tags were set
            assert mock_audio.__setitem__.call_count == 3

    def test_restore_metadata_with_pictures(self, tmp_path):
        """Test restoration including album art pictures."""
        test_file = tmp_path / "with_art.flac"
        test_file.touch()

        mock_picture = MagicMock()
        metadata = {
            'tags': {'TITLE': ['Test']},
            'pictures': [mock_picture]
        }

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio

            result = _restore_metadata(str(test_file), metadata)

            assert result is True
            mock_audio.add_picture.assert_called_once_with(mock_picture)

    def test_restore_metadata_empty_metadata(self, tmp_path):
        """Test restoration with empty metadata."""
        test_file = tmp_path / "empty.flac"
        test_file.touch()

        metadata = {
            'tags': {},
            'pictures': []
        }

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio

            result = _restore_metadata(str(test_file), metadata)

            assert result is True
            mock_audio.clear.assert_called_once()
            mock_audio.save.assert_called_once()

    def test_restore_metadata_mutagen_not_available(self, tmp_path):
        """Test behavior when Mutagen is not available."""
        test_file = tmp_path / "test.flac"
        test_file.touch()

        metadata = {'tags': {}, 'pictures': []}

        with patch('flac_detective.analysis.new_scoring.audio_loader.MUTAGEN_AVAILABLE', False):
            result = _restore_metadata(str(test_file), metadata)

            assert result is False

    def test_restore_metadata_no_metadata(self, tmp_path):
        """Test restoration with None metadata."""
        test_file = tmp_path / "test.flac"
        test_file.touch()

        result = _restore_metadata(str(test_file), None)

        assert result is False

    def test_restore_metadata_exception_handling(self, tmp_path):
        """Test exception handling during metadata restoration."""
        test_file = tmp_path / "error.flac"
        test_file.touch()

        metadata = {'tags': {'TITLE': ['Test']}, 'pictures': []}

        with patch('flac_detective.analysis.new_scoring.audio_loader.FLAC') as mock_flac:
            mock_flac.side_effect = Exception("Cannot write file")

            result = _restore_metadata(str(test_file), metadata)

            assert result is False


class TestRepairFlacFile:
    """Tests for repair_flac_file() function."""

    @pytest.fixture
    def mock_subprocess_success(self):
        """Mock successful subprocess calls."""
        with patch('flac_detective.analysis.new_scoring.audio_loader.subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            yield mock_run

    @pytest.fixture
    def mock_metadata_functions(self):
        """Mock metadata extraction and restoration."""
        with patch('flac_detective.analysis.new_scoring.audio_loader._extract_metadata') as mock_extract, \
             patch('flac_detective.analysis.new_scoring.audio_loader._restore_metadata') as mock_restore:

            mock_extract.return_value = {
                'tags': {'TITLE': ['Test']},
                'pictures': []
            }
            mock_restore.return_value = True

            yield mock_extract, mock_restore

    def test_repair_flac_file_success(self, tmp_path, mock_subprocess_success, mock_metadata_functions):
        """Test successful FLAC file repair."""
        # Create test files
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=True), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.getsize', return_value=1000000):

            result = repair_flac_file(str(corrupted_file))

            assert result is not None
            assert "repaired_" in result
            # Verify subprocess was called 3 times (decode, encode, verify)
            assert mock_subprocess_success.call_count == 3

    def test_repair_flac_file_decode_fails(self, tmp_path, mock_metadata_functions):
        """Test repair when decode step fails."""
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.subprocess.run') as mock_run, \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=False):

            result = repair_flac_file(str(corrupted_file))

            assert result is None

    def test_repair_flac_file_encode_fails(self, tmp_path, mock_metadata_functions):
        """Test repair when encode step fails."""
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.subprocess.run') as mock_run, \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=True), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.getsize', return_value=1000000):

            # First call (decode) succeeds, second call (encode) fails
            mock_result_decode = MagicMock()
            mock_result_decode.returncode = 0
            mock_result_encode = MagicMock()
            mock_result_encode.returncode = 1
            mock_run.side_effect = [mock_result_decode, mock_result_encode]

            result = repair_flac_file(str(corrupted_file))

            assert result is None

    def test_repair_flac_file_verify_fails(self, tmp_path, mock_metadata_functions):
        """Test repair when verify step fails."""
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.subprocess.run') as mock_run, \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=True), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.getsize', return_value=1000000):

            # Decode and encode succeed, verify fails
            mock_success = MagicMock()
            mock_success.returncode = 0
            mock_fail = MagicMock()
            mock_fail.returncode = 1
            mock_run.side_effect = [mock_success, mock_success, mock_fail]

            result = repair_flac_file(str(corrupted_file))

            assert result is None

    def test_repair_flac_file_with_source_replacement(self, tmp_path, mock_subprocess_success, mock_metadata_functions):
        """Test repair with source file replacement."""
        corrupted_file = tmp_path / "corrupted.flac"
        source_file = tmp_path / "source.flac"
        corrupted_file.write_bytes(b"fake flac data")
        source_file.write_bytes(b"original flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=True), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.getsize', return_value=1000000), \
             patch('flac_detective.analysis.new_scoring.audio_loader.shutil.copy2') as mock_copy, \
             patch('flac_detective.analysis.new_scoring.audio_loader.get_tracker') as mock_tracker:

            result = repair_flac_file(
                str(corrupted_file),
                source_path=str(source_file),
                replace_source=True
            )

            assert result is not None
            # Verify backup and replacement were attempted
            assert mock_copy.call_count >= 2  # Backup + replacement

    def test_repair_flac_file_timeout(self, tmp_path, mock_metadata_functions):
        """Test repair timeout handling."""
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Timeout")

            result = repair_flac_file(str(corrupted_file))

            assert result is None

    def test_repair_flac_file_cleanup_wav(self, tmp_path, mock_subprocess_success, mock_metadata_functions):
        """Test that intermediate WAV file is cleaned up."""
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=True), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.getsize', return_value=1000000), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.remove') as mock_remove:

            result = repair_flac_file(str(corrupted_file))

            # Verify cleanup was attempted
            mock_remove.assert_called()

    def test_repair_flac_file_no_metadata_extraction(self, tmp_path, mock_subprocess_success):
        """Test repair when metadata extraction fails."""
        corrupted_file = tmp_path / "corrupted.flac"
        corrupted_file.write_bytes(b"fake flac data")

        with patch('flac_detective.analysis.new_scoring.audio_loader._extract_metadata', return_value=None), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.exists', return_value=True), \
             patch('flac_detective.analysis.new_scoring.audio_loader.os.path.getsize', return_value=1000000):

            result = repair_flac_file(str(corrupted_file))

            # Should still succeed even without metadata
            assert result is not None


# Integration test marker
@pytest.mark.integration
class TestRepairIntegration:
    """Integration tests for repair functionality (requires actual FLAC tools)."""

    def test_repair_requires_flac_tool(self):
        """Test that repair requires flac command-line tool."""
        # This test documents the requirement
        # Actual integration tests in tests/integration/
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=flac_detective.analysis.new_scoring.audio_loader", "--cov-report=term-missing"])
