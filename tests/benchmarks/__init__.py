"""Performance benchmarks for FLAC Detective.

This package contains performance benchmarks to track execution time
of critical code paths and detect performance regressions.

Benchmark Categories:
- Audio Loading: File I/O and audio data loading
- Spectral Analysis: FFT and frequency analysis
- Scoring: Rule execution and score calculation
- Full Analysis: End-to-end file analysis

Run benchmarks:
    pytest tests/benchmarks/ --benchmark-only

Compare with baseline:
    pytest tests/benchmarks/ --benchmark-compare=baseline

Save baseline:
    pytest tests/benchmarks/ --benchmark-save=baseline
"""

__all__ = []
