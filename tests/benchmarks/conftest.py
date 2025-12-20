"""Pytest configuration and fixtures for benchmarks."""

import pytest
from pathlib import Path
import numpy as np
import soundfile as sf
import tempfile


@pytest.fixture(scope="session")
def benchmark_audio_file():
    """Create a temporary FLAC file for benchmarking.

    Creates a 30-second stereo FLAC file with synthetic audio data.
    """
    # Generate 30 seconds of stereo audio at 44.1kHz
    sample_rate = 44100
    duration = 30.0
    samples = int(sample_rate * duration)

    # Create synthetic audio (pink noise + sine waves)
    np.random.seed(42)  # Reproducible
    channels = 2

    # Generate base pink noise
    audio = np.random.randn(samples, channels) * 0.1

    # Add some harmonic content
    t = np.linspace(0, duration, samples)
    for freq in [440, 880, 1320]:  # A4, A5, E6
        audio[:, 0] += 0.05 * np.sin(2 * np.pi * freq * t)
        audio[:, 1] += 0.05 * np.sin(2 * np.pi * freq * t * 1.01)  # Slightly detuned

    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.8

    # Create temporary FLAC file
    temp_file = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
    temp_path = Path(temp_file.name)

    sf.write(temp_path, audio, sample_rate, subtype='PCM_16')

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def benchmark_small_audio():
    """Create a small (5 second) FLAC file for quick benchmarks."""
    sample_rate = 44100
    duration = 5.0
    samples = int(sample_rate * duration)

    np.random.seed(123)
    audio = np.random.randn(samples, 2) * 0.3

    temp_file = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
    temp_path = Path(temp_file.name)

    sf.write(temp_path, audio, sample_rate, subtype='PCM_16')

    yield temp_path

    temp_path.unlink(missing_ok=True)


@pytest.fixture
def sample_audio_data():
    """Generate sample audio data without file I/O."""
    sample_rate = 44100
    duration = 5.0
    samples = int(sample_rate * duration)

    np.random.seed(456)
    audio = np.random.randn(samples, 2) * 0.5

    return audio, sample_rate


@pytest.fixture
def benchmark_config():
    """Configuration for benchmarks."""
    return {
        'min_rounds': 5,
        'warmup': True,
        'sample_duration': 30.0,
    }
