"""End-to-end performance benchmarks.

Tests the performance of:
- Complete file analysis
- Batch file processing
- Real-world scenarios
"""

from pathlib import Path

import pytest

from flac_detective.analysis.analyzer import FLACAnalyzer


class TestEndToEndPerformance:
    """Benchmark complete analysis workflows."""

    def test_single_file_analysis(self, benchmark, benchmark_audio_file):
        """Benchmark complete analysis of a single file."""
        analyzer = FLACAnalyzer(sample_duration=30.0)

        result = benchmark(analyzer.analyze_file, benchmark_audio_file)
        assert "score" in result
        assert "verdict" in result

    def test_quick_analysis(self, benchmark, benchmark_small_audio):
        """Benchmark quick analysis (5 seconds)."""
        analyzer = FLACAnalyzer(sample_duration=5.0)

        result = benchmark(analyzer.analyze_file, benchmark_small_audio)
        assert result is not None

    def test_full_analysis(self, benchmark, benchmark_audio_file):
        """Benchmark full analysis (30 seconds)."""
        analyzer = FLACAnalyzer(sample_duration=30.0)

        result = benchmark(analyzer.analyze_file, benchmark_audio_file)
        assert result is not None


class TestBatchProcessing:
    """Benchmark batch file processing."""

    def test_analyze_multiple_files(self, benchmark, benchmark_audio_file):
        """Benchmark analyzing multiple files sequentially."""
        analyzer = FLACAnalyzer(sample_duration=5.0)

        def analyze_batch():
            results = []
            for _ in range(3):  # Analyze 3 times
                result = analyzer.analyze_file(benchmark_audio_file)
                results.append(result)
            return results

        results = benchmark(analyze_batch)
        assert len(results) == 3

    def test_analyzer_reuse(self, benchmark, benchmark_small_audio):
        """Benchmark analyzer reuse (same instance)."""
        analyzer = FLACAnalyzer(sample_duration=5.0)

        # Pre-warm
        _ = analyzer.analyze_file(benchmark_small_audio)

        # Benchmark subsequent analyses
        result = benchmark(analyzer.analyze_file, benchmark_small_audio)
        assert result is not None


class TestRealWorldScenarios:
    """Benchmark realistic usage patterns."""

    def test_typical_user_workflow(self, benchmark, benchmark_audio_file):
        """Benchmark typical user workflow: create analyzer + analyze file."""

        def user_workflow():
            analyzer = FLACAnalyzer(sample_duration=30.0)
            return analyzer.analyze_file(benchmark_audio_file)

        result = benchmark(user_workflow)
        assert result is not None

    def test_quick_scan_workflow(self, benchmark, benchmark_small_audio):
        """Benchmark quick scan workflow (low sample duration)."""

        def quick_scan():
            analyzer = FLACAnalyzer(sample_duration=5.0)
            return analyzer.analyze_file(benchmark_small_audio)

        result = benchmark(quick_scan)
        assert result is not None


class TestMemoryEfficiency:
    """Benchmark memory-efficient operations."""

    def test_minimal_memory_footprint(self, benchmark, benchmark_small_audio):
        """Benchmark analysis with minimal memory usage."""
        # Small sample duration to reduce memory
        analyzer = FLACAnalyzer(sample_duration=1.0)

        result = benchmark(analyzer.analyze_file, benchmark_small_audio)
        assert result is not None

    def test_cache_cleanup(self, benchmark, benchmark_small_audio):
        """Benchmark with cache cleanup between runs."""

        def analyze_with_cleanup():
            analyzer = FLACAnalyzer(sample_duration=5.0)
            result = analyzer.analyze_file(benchmark_small_audio)
            # Force cleanup by deleting analyzer
            del analyzer
            return result

        result = benchmark(analyze_with_cleanup)
        assert result is not None
