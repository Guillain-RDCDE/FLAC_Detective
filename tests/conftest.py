"""Pytest configuration and shared fixtures."""
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_flac_path():
    """Return path to sample FLAC file for testing."""
    # This should point to a real test file in your test data
    return Path(__file__).parent / "data" / "sample.flac"


@pytest.fixture
def mock_progress_file(temp_dir):
    """Create a temporary progress file."""
    return temp_dir / "progress.json"
