"""Benchmarks for scoring and rule execution performance.

Tests the performance of:
- Individual scoring rules
- Complete score calculation
- Rule optimization paths
- Early termination logic
"""

import pytest
import numpy as np
from pathlib import Path

from flac_detective.analysis.new_scoring import new_calculate_score
from flac_detective.analysis.new_scoring.rules import (
    rule1_mp3_bitrate_detection,
    rule2_bitrate_clusters,
    rule3_cutoff_stability,
    rule4_energy_ratio,
    rule5_dynamic_range,
    rule6_stereo_analysis,
    rule7_dither_vinyl_detection,
    rule8_nyquist_exception,
)
from flac_detective.analysis.audio_cache import AudioCache


class TestScoringRules:
    """Benchmark individual scoring rules."""

    def test_rule1_mp3_detection(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 1: MP3 bitrate detection."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule1_mp3_bitrate_detection, cache)
        assert 'points' in result

    def test_rule2_bitrate_clusters(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 2: Bitrate cluster analysis."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule2_bitrate_clusters, cache)
        assert 'points' in result

    def test_rule3_cutoff_stability(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 3: Cutoff stability analysis."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule3_cutoff_stability, cache)
        assert 'points' in result

    def test_rule4_energy_ratio(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 4: Energy ratio analysis."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule4_energy_ratio, cache)
        assert 'points' in result

    def test_rule5_dynamic_range(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 5: Dynamic range compression."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule5_dynamic_range, cache)
        assert 'points' in result

    def test_rule6_stereo_analysis(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 6: Stereo width analysis."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule6_stereo_analysis, cache)
        assert 'points' in result

    def test_rule7_vinyl_detection(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 7: Dither and vinyl detection."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule7_dither_vinyl_detection, cache)
        assert 'points' in result

    def test_rule8_nyquist_exception(self, benchmark, benchmark_audio_file):
        """Benchmark Rule 8: Nyquist exception."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(rule8_nyquist_exception, cache)
        assert 'points' in result


class TestCompleteScoring:
    """Benchmark complete score calculation."""

    def test_full_score_calculation(self, benchmark, benchmark_audio_file):
        """Benchmark complete score calculation (all rules)."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(new_calculate_score, cache)
        assert 'score' in result
        assert 'verdict' in result

    def test_score_with_early_termination(self, benchmark, benchmark_audio_file):
        """Benchmark score calculation with early termination."""
        # This tests the fast path optimization
        cache = AudioCache(benchmark_audio_file, 30.0)

        result = benchmark(new_calculate_score, cache)
        assert result is not None


class TestScoringOptimizations:
    """Benchmark scoring system optimizations."""

    def test_short_circuit_authentic(self, benchmark, benchmark_audio_file):
        """Benchmark short-circuit for authentic files."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        # Measure time to reach short-circuit decision
        result = benchmark(new_calculate_score, cache)
        assert result is not None

    def test_progressive_rule_execution(self, benchmark, benchmark_audio_file):
        """Benchmark progressive rule execution."""
        cache = AudioCache(benchmark_audio_file, 30.0)

        benchmark(new_calculate_score, cache)


class TestRuleScaling:
    """Benchmark rule execution with different workloads."""

    @pytest.mark.parametrize("duration", [5.0, 10.0, 30.0])
    def test_rule1_varying_duration(self, benchmark, duration):
        """Benchmark Rule 1 with varying audio durations."""
        import tempfile
        import soundfile as sf

        # Create temporary file
        sr = 44100
        samples = int(sr * duration)
        audio = np.random.randn(samples, 2) * 0.5

        temp_file = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
        temp_path = Path(temp_file.name)
        sf.write(temp_path, audio, sr)

        cache = AudioCache(temp_path, duration)

        result = benchmark(rule1_mp3_bitrate_detection, cache)

        # Cleanup
        temp_path.unlink(missing_ok=True)

        assert result is not None
