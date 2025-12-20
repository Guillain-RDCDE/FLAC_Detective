"""Benchmarks for spectral analysis performance.

Tests the performance of:
- FFT computation
- Spectrum analysis
- Cutoff frequency detection
- Energy-based analysis
"""

import pytest
import numpy as np

from flac_detective.analysis.spectrum import (
    analyze_spectrum,
    find_cutoff_frequency,
)


class TestFFTPerformance:
    """Benchmark FFT and spectral analysis."""

    def test_spectrum_analysis_full(self, benchmark, sample_audio_data):
        """Benchmark complete spectrum analysis."""
        audio, sr = sample_audio_data

        result = benchmark(analyze_spectrum, audio, sr)
        assert 'cutoff_freq' in result

    def test_cutoff_detection(self, benchmark, sample_audio_data):
        """Benchmark cutoff frequency detection."""
        audio, sr = sample_audio_data

        # Pre-compute spectrum for isolated benchmark
        spectrum_result = analyze_spectrum(audio, sr)
        freqs = np.fft.rfftfreq(len(audio), 1/sr)
        spectrum = np.abs(np.fft.rfft(audio[:, 0]))

        result = benchmark(find_cutoff_frequency, freqs, spectrum, sr)
        assert result is not None


class TestSpectralScaling:
    """Benchmark spectral analysis with different data sizes."""

    @pytest.mark.parametrize("duration", [1.0, 5.0, 10.0, 30.0])
    def test_varying_duration(self, benchmark, duration):
        """Benchmark spectrum analysis with varying durations."""
        sr = 44100
        samples = int(sr * duration)
        audio = np.random.randn(samples, 2) * 0.5

        benchmark(analyze_spectrum, audio, sr)

    @pytest.mark.parametrize("sample_rate", [22050, 44100, 48000, 96000])
    def test_varying_sample_rate(self, benchmark, sample_rate):
        """Benchmark spectrum analysis with varying sample rates."""
        duration = 5.0
        samples = int(sample_rate * duration)
        audio = np.random.randn(samples, 2) * 0.5

        benchmark(analyze_spectrum, audio, sample_rate)


class TestEnergyAnalysis:
    """Benchmark energy-based analysis."""

    def test_energy_computation(self, benchmark):
        """Benchmark energy computation across frequencies."""
        sr = 44100
        duration = 5.0
        samples = int(sr * duration)

        audio = np.random.randn(samples) * 0.5
        spectrum = np.abs(np.fft.rfft(audio))

        def compute_cumulative_energy():
            return np.cumsum(spectrum**2)

        benchmark(compute_cumulative_energy)
