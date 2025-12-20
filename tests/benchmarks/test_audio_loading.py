"""Benchmarks for audio loading performance.

Tests the performance of:
- FLAC file reading
- Audio cache operations
- Retry mechanism
- Partial loading fallback
"""

import pytest
from pathlib import Path

from flac_detective.analysis.audio_cache import AudioCache
from flac_detective.analysis.new_scoring.audio_loader import (
    load_audio_with_retry,
    sf_blocks_partial,
)


class TestAudioLoadingBenchmarks:
    """Benchmark audio loading operations."""

    def test_load_flac_file(self, benchmark, benchmark_audio_file):
        """Benchmark loading a complete FLAC file."""
        result = benchmark(load_audio_with_retry, benchmark_audio_file)
        assert result is not None
        assert len(result) > 0

    def test_load_small_flac(self, benchmark, benchmark_small_audio):
        """Benchmark loading a small FLAC file."""
        result = benchmark(load_audio_with_retry, benchmark_small_audio)
        assert result is not None

    def test_audio_cache_creation(self, benchmark, benchmark_audio_file):
        """Benchmark AudioCache initialization."""
        result = benchmark(
            AudioCache,
            benchmark_audio_file,
            30.0
        )
        assert result is not None

    def test_audio_cache_reuse(self, benchmark, benchmark_audio_file):
        """Benchmark repeated access to cached audio."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        def access_cache():
            return cache.get_audio()

        result = benchmark(access_cache)
        assert result is not None

    def test_partial_loading(self, benchmark, benchmark_audio_file):
        """Benchmark partial audio loading (fallback mode)."""
        result = benchmark(
            sf_blocks_partial,
            benchmark_audio_file,
            blocksize=4096
        )
        assert result is not None


class TestAudioLoadingScaling:
    """Benchmark audio loading with different file sizes."""

    def test_load_30s_file(self, benchmark, benchmark_audio_file):
        """Benchmark 30-second file loading."""
        benchmark(load_audio_with_retry, benchmark_audio_file)

    def test_load_5s_file(self, benchmark, benchmark_small_audio):
        """Benchmark 5-second file loading."""
        benchmark(load_audio_with_retry, benchmark_small_audio)


class TestCachePerformance:
    """Benchmark cache-related operations."""

    def test_cache_creation_overhead(self, benchmark, benchmark_audio_file):
        """Benchmark AudioCache creation overhead."""
        benchmark(AudioCache, benchmark_audio_file, 30.0)

    def test_cache_hit_performance(self, benchmark, benchmark_audio_file):
        """Benchmark cache hit (already loaded)."""
        cache = AudioCache(benchmark_audio_file, 30.0)
        _ = cache.get_audio()  # Warm up cache

        benchmark(cache.get_audio)

    def test_cache_miss_performance(self, benchmark):
        """Benchmark cache miss (new file each time)."""
        import tempfile
        import soundfile as sf
        import numpy as np

        def create_and_cache():
            # Create temp file
            audio = np.random.randn(44100, 2) * 0.5
            temp_file = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
            temp_path = Path(temp_file.name)
            sf.write(temp_path, audio, 44100)

            # Create cache
            cache = AudioCache(temp_path, 5.0)
            result = cache.get_audio()

            # Cleanup
            temp_path.unlink(missing_ok=True)

            return result

        benchmark(create_and_cache)
