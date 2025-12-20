## Performance Benchmarking Guide

This guide explains how FLAC Detective tracks performance over time and detects performance regressions.

## Table of Contents

- [Overview](#overview)
- [Benchmark Suite](#benchmark-suite)
- [Running Benchmarks](#running-benchmarks)
- [Automated Tracking](#automated-tracking)
- [Performance Regressions](#performance-regressions)
- [Interpreting Results](#interpreting-results)
- [Optimization Guidelines](#optimization-guidelines)

## Overview

FLAC Detective uses **pytest-benchmark** to:
- Track execution time of critical code paths
- Detect performance regressions automatically
- Compare performance across commits
- Visualize performance trends over time

**Benefits**:
- ✅ Early detection of performance issues
- ✅ Historical performance tracking
- ✅ Data-driven optimization decisions
- ✅ Prevent performance regressions in PRs

## Benchmark Suite

### Benchmark Categories

#### 1. Audio Loading (`tests/benchmarks/test_audio_loading.py`)
Measures file I/O and audio data loading performance:

- **test_load_flac_file**: Complete FLAC file loading (30s)
- **test_load_small_flac**: Small file loading (5s)
- **test_audio_cache_creation**: AudioCache initialization
- **test_audio_cache_reuse**: Cached audio access
- **test_partial_loading**: Partial loading fallback

**Expected Performance**:
- Load 30s file: < 100ms
- Load 5s file: < 50ms
- Cache creation: < 100ms
- Cache hit: < 1ms

#### 2. Spectral Analysis (`tests/benchmarks/test_spectral_analysis.py`)
Measures FFT and frequency analysis performance:

- **test_spectrum_analysis_full**: Complete spectrum analysis
- **test_cutoff_detection**: Cutoff frequency detection
- **test_varying_duration**: Performance scaling with duration
- **test_varying_sample_rate**: Performance scaling with sample rate

**Expected Performance**:
- Full spectrum (5s): < 200ms
- Cutoff detection: < 50ms

#### 3. Scoring (`tests/benchmarks/test_scoring_performance.py`)
Measures rule execution and scoring performance:

- **test_rule1_mp3_detection**: Rule 1 execution time
- **test_rule2_bitrate_clusters**: Rule 2 execution time
- **test_rule3-8**: Individual rule benchmarks
- **test_full_score_calculation**: Complete scoring (all rules)

**Expected Performance**:
- Single rule: < 100ms
- Full scoring: < 500ms

#### 4. End-to-End (`tests/benchmarks/test_end_to_end.py`)
Measures complete analysis workflows:

- **test_single_file_analysis**: Full file analysis
- **test_quick_analysis**: Quick scan (5s sample)
- **test_batch_processing**: Multiple file analysis

**Expected Performance**:
- Single file (30s sample): < 1s
- Quick analysis (5s sample): < 500ms

### Benchmark Test Structure

```python
def test_example_benchmark(benchmark):
    """Benchmark example function."""
    result = benchmark(function_to_test, arg1, arg2)
    assert result is not None
```

**Key Points**:
- Benchmarks run 5+ rounds for accuracy
- Warmup phase included
- Statistical analysis (mean, median, std dev)
- Operations per second calculated

## Running Benchmarks

### Local Execution

**Run all benchmarks**:
```bash
pytest tests/benchmarks/ --benchmark-only -v
```

**Run specific benchmark file**:
```bash
pytest tests/benchmarks/test_audio_loading.py --benchmark-only
```

**Save baseline**:
```bash
pytest tests/benchmarks/ --benchmark-save=baseline
```

**Compare with baseline**:
```bash
pytest tests/benchmarks/ --benchmark-compare=baseline
```

**Generate HTML report**:
```bash
pytest tests/benchmarks/ --benchmark-only --benchmark-histogram
```

### pytest-benchmark Options

```bash
# Minimum rounds
pytest tests/benchmarks/ --benchmark-min-rounds=10

# Warmup
pytest tests/benchmarks/ --benchmark-warmup=on

# Sort results
pytest tests/benchmarks/ --benchmark-sort=mean

# Only show results (skip tests)
pytest tests/benchmarks/ --benchmark-only

# Autosave results
pytest tests/benchmarks/ --benchmark-autosave
```

### Advanced Usage

**Compare two saved benchmarks**:
```bash
pytest-benchmark compare baseline current --group-by=name
```

**Export to JSON**:
```bash
pytest tests/benchmarks/ \
  --benchmark-json=output.json \
  --benchmark-only
```

**Generate custom report**:
```bash
python scripts/generate_benchmark_report.py output.json > report.md
```

## Automated Tracking

### GitHub Actions Workflow

The [benchmark workflow](.github/workflows/benchmark.yml) runs automatically:

**Triggers**:
- Push to main branch
- Pull requests
- Weekly schedule (Sunday 3 AM)
- Manual dispatch

**Process**:
1. **Run Benchmarks** - Execute full benchmark suite
2. **Generate Report** - Create markdown summary
3. **Store Results** - Save to gh-pages branch
4. **Compare** (PRs only) - Compare with main branch
5. **Check Regressions** - Detect performance issues
6. **Comment PR** - Post results to pull request

### Benchmark History

Results are tracked on GitHub Pages:
```
https://github.com/GuillainM/FLAC_Detective/blob/gh-pages/dev/bench/index.html
```

**Features**:
- Historical trend charts
- Commit-by-commit tracking
- Interactive graphs
- Downloadable data

### Pull Request Comments

For PRs, the workflow posts:

```markdown
## 📊 Performance Benchmark Results

### Overall Statistics
- Fastest Test: 120 μs
- Slowest Test: 850 ms
- Average Time: 150 ms

### test_audio_loading
| Test | Mean | Min | Max | Ops/s |
|------|------|-----|-----|-------|
| test_load_flac | 85 ms | 80 ms | 95 ms | 11.76 ops/s |

...
```

### Regression Alerts

If performance regression detected (>30% slower):

```markdown
## ⚠️ Performance Regression Detected

**Test**: test_single_file_analysis
**Baseline**: 750 ms
**Current**: 1050 ms
**Change**: +40% 🔴

@GuillainM please review this regression.
```

## Performance Regressions

### Detection Thresholds

**Alert Threshold**: 130% (30% slower)
- Triggers comment on commit
- Alerts configured users
- Does not fail workflow

**Severe Regression**: >50% slower
- Fails regression check job
- Blocks merge (optional)
- Requires manual review

### Regression Check Script

```bash
python scripts/check_performance_regression.py \
  output.json \
  --threshold 30 \
  --output regression-report.md
```

**Output**:
- Violations (>30% slower)
- Warnings (20-30% slower)
- Passing tests (<20% variation)
- Recommendations

### Handling Regressions

**If regression detected**:

1. **Review Changes**: Check what code changed
2. **Profile Code**: Use Python profiler to identify bottleneck
3. **Optimize**: Fix the performance issue
4. **Re-benchmark**: Verify improvement
5. **Document**: Note optimization in commit message

**Profiling Example**:
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run slow code
analyzer.analyze_file(filepath)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest
```

## Interpreting Results

### Understanding Output

**pytest-benchmark output**:
```
Name (time in ms)                     Min      Max     Mean    StdDev
test_load_flac_file                  80.2     95.3    85.1      4.2
test_spectrum_analysis              145.0    180.2   155.3     12.1
test_full_score_calculation         420.5    510.8   455.2     28.3
```

**Key Metrics**:
- **Min**: Fastest execution (best case)
- **Max**: Slowest execution (worst case)
- **Mean**: Average execution time
- **StdDev**: Consistency (lower is better)
- **Ops/s**: Throughput (operations per second)

### Performance Grades

- ⚡ **Very Fast**: < 1ms (microseconds)
- 🚀 **Fast**: 1-10ms
- ⏱️ **Moderate**: 10-100ms
- 🐌 **Slow**: 100ms-1s
- 🐢 **Very Slow**: > 1s

### What's Acceptable?

**For FLAC Detective**:
- Audio loading: 50-100ms (acceptable)
- Spectral analysis: 100-200ms (good)
- Complete scoring: 300-500ms (excellent)
- End-to-end analysis: < 1s (target)

**User Experience**:
- < 500ms: Feels instant
- 500ms-1s: Acceptable
- 1-2s: Noticeable delay
- > 2s: Needs optimization

## Optimization Guidelines

### Performance Best Practices

#### 1. Avoid Repeated I/O

**Bad**:
```python
def analyze():
    audio1 = sf.read(filepath)  # Read 1
    audio2 = sf.read(filepath)  # Read 2 (redundant!)
    audio3 = sf.read(filepath)  # Read 3 (redundant!)
```

**Good**:
```python
def analyze():
    cache = AudioCache(filepath)
    audio = cache.get_audio()  # Read once, reuse
```

#### 2. Use NumPy Efficiently

**Bad**:
```python
result = []
for i in range(len(array)):
    result.append(array[i] * 2)  # Python loop (slow)
```

**Good**:
```python
result = array * 2  # Vectorized (fast)
```

#### 3. Cache Expensive Computations

**Bad**:
```python
def get_spectrum():
    return np.fft.rfft(audio)  # Recompute every time

spectrum1 = get_spectrum()
spectrum2 = get_spectrum()  # Redundant FFT!
```

**Good**:
```python
spectrum = np.fft.rfft(audio)  # Compute once
use_spectrum(spectrum)  # Reuse
```

#### 4. Short-Circuit When Possible

**Bad**:
```python
score = 0
score += rule1()  # Always run
score += rule2()  # Always run
score += rule3()  # Always run
# ... all rules run regardless of score
```

**Good**:
```python
score = 0
score += rule1()
if score >= 86:  # Early termination
    return {"score": score, "verdict": "FAKE"}
# Skip expensive rules if already certain
```

### Profiling Checklist

Before optimizing:
1. ✅ Run benchmarks to establish baseline
2. ✅ Profile code to find bottleneck
3. ✅ Focus on hot paths (90/10 rule)
4. ✅ Optimize one thing at a time
5. ✅ Re-benchmark to verify improvement
6. ✅ Document optimization

### Common Bottlenecks

**In FLAC Detective**:

1. **File I/O** (30-40% of time)
   - Solution: AudioCache, minimize reads

2. **FFT Computation** (20-30% of time)
   - Solution: Reduce sample size, cache results

3. **NumPy Operations** (15-25% of time)
   - Solution: Vectorize, avoid loops

4. **Rule Execution** (10-20% of time)
   - Solution: Short-circuit, parallel execution

## Monitoring Performance

### Weekly Review

Check benchmark trends:
```bash
# View last week's benchmarks
git log --grep="benchmark" --since="1 week ago"

# Check gh-pages for trends
# Visit: https://github.com/GuillainM/FLAC_Detective/blob/gh-pages/dev/bench/
```

### Monthly Audit

1. Review slowest tests
2. Check for upward trends
3. Plan optimization sprints
4. Update performance expectations

### Performance Dashboard

Key metrics to track:
- Average end-to-end time
- P95/P99 latencies
- Regression frequency
- Optimization impact

## Troubleshooting

### Benchmark Failures

**Issue**: Benchmarks fail or timeout

**Solutions**:
1. Increase `--benchmark-min-rounds`
2. Check system load
3. Disable other processes
4. Use `--benchmark-warmup=on`

### Inconsistent Results

**Issue**: High standard deviation

**Solutions**:
1. Run more rounds: `--benchmark-min-rounds=10`
2. Check for background processes
3. Use dedicated benchmark machine
4. Increase warmup: `--benchmark-warmup-iterations=5`

### Comparison Errors

**Issue**: Cannot compare benchmarks

**Solutions**:
1. Ensure same pytest-benchmark version
2. Check JSON format compatibility
3. Verify test names match
4. Use `--benchmark-compare=0001` format

## Related Documentation

- [pytest-benchmark docs](https://pytest-benchmark.readthedocs.io/)
- [Python profiling guide](https://docs.python.org/3/library/profile.html)
- [NumPy performance tips](https://numpy.org/doc/stable/user/performance.html)

---

**Last Updated**: 2025-12-20
**Benchmark Version**: v1.0
