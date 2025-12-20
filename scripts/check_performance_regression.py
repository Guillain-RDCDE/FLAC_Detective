#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check for performance regressions in benchmark results.

Usage:
    python scripts/check_performance_regression.py output.json
    python scripts/check_performance_regression.py output.json --threshold 50
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def format_time(seconds):
    """Format time in appropriate unit."""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.2f} ns"
    elif seconds < 1e-3:
        return f"{seconds * 1e6:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1e3:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def check_regressions(benchmark_file, threshold_pct, output_file):
    """Check for performance regressions.

    Args:
        benchmark_file: Path to benchmark JSON file
        threshold_pct: Percentage threshold for regression (default 30%)
        output_file: Output markdown file path
    """
    with open(benchmark_file, 'r') as f:
        data = json.load(f)

    benchmarks = data.get('benchmarks', [])

    if not benchmarks:
        print("⚠️ No benchmarks found")
        return

    # Define performance expectations (in seconds)
    # These are baseline expectations - tests slower than this are flagged
    expectations = {
        'test_load_flac_file': 0.1,  # 100ms max for loading
        'test_load_small_flac': 0.05,  # 50ms for small files
        'test_audio_cache_creation': 0.1,
        'test_audio_cache_reuse': 0.001,  # Should be very fast (cached)
        'test_spectrum_analysis_full': 0.2,  # 200ms for full analysis
        'test_full_score_calculation': 0.5,  # 500ms for complete scoring
        'test_single_file_analysis': 1.0,  # 1s for end-to-end
    }

    # Open output file
    with open(output_file, 'w') as out:
        out.write("# Performance Regression Report\n\n")

        # Check against expectations
        violations = []
        warnings = []
        good = []

        for bench in benchmarks:
            name = bench['name']
            mean = bench['stats']['mean']

            # Find matching expectation (partial match)
            expected_time = None
            for exp_name, exp_time in expectations.items():
                if exp_name in name:
                    expected_time = exp_time
                    break

            if expected_time:
                ratio = mean / expected_time

                if ratio > (1 + threshold_pct / 100):
                    # Severe regression
                    violations.append((name, mean, expected_time, ratio))
                elif ratio > 1.2:  # 20% over
                    # Warning
                    warnings.append((name, mean, expected_time, ratio))
                else:
                    # Good
                    good.append((name, mean, expected_time, ratio))

        # Write summary
        out.write("## Summary\n\n")
        out.write(f"- ✅ **Passing**: {len(good)} tests within expectations\n")
        out.write(f"- ⚠️ **Warnings**: {len(warnings)} tests slightly slow (20-{threshold_pct}%)\n")
        out.write(f"- 🔴 **Violations**: {len(violations)} tests severely slow (>{threshold_pct}%)\n\n")

        # Write violations
        if violations:
            out.write("## 🔴 SEVERE REGRESSION\n\n")
            out.write("| Test | Current | Expected | Ratio |\n")
            out.write("|------|---------|----------|-------|\n")

            for name, current, expected, ratio in sorted(violations, key=lambda x: x[3], reverse=True):
                out.write(f"| {name} | "
                          f"{format_time(current)} | "
                          f"{format_time(expected)} | "
                          f"**{ratio:.2f}x** |\n")

            out.write("\n⚠️ **Action Required**: These tests are significantly slower than expected.\n\n")

        # Write warnings
        if warnings:
            out.write("## ⚠️ Performance Warnings\n\n")
            out.write("| Test | Current | Expected | Ratio |\n")
            out.write("|------|---------|----------|-------|\n")

            for name, current, expected, ratio in sorted(warnings, key=lambda x: x[3], reverse=True):
                out.write(f"| {name} | "
                          f"{format_time(current)} | "
                          f"{format_time(expected)} | "
                          f"{ratio:.2f}x |\n")

            out.write("\n")

        # Write passing tests
        if good:
            out.write("## ✅ Passing Tests\n\n")
            out.write(f"{len(good)} tests within expected performance bounds.\n\n")

        # Write slowest tests overall
        out.write("## 🐢 Slowest 10 Tests\n\n")
        slowest = sorted(benchmarks, key=lambda x: x['stats']['mean'], reverse=True)[:10]

        for i, bench in enumerate(slowest, 1):
            out.write(f"{i}. **{bench['name']}**: {format_time(bench['stats']['mean'])}\n")

        out.write("\n")

        # Write recommendations
        out.write("## 💡 Recommendations\n\n")

        if violations:
            out.write("### Critical Actions\n\n")
            out.write("1. Profile the severely slow tests to identify bottlenecks\n")
            out.write("2. Consider algorithmic optimizations\n")
            out.write("3. Review for unnecessary I/O or computation\n")
            out.write("4. Check for memory leaks or inefficient caching\n\n")

        if warnings:
            out.write("### Suggested Improvements\n\n")
            out.write("1. Review warning tests for minor optimizations\n")
            out.write("2. Consider caching or memoization opportunities\n")
            out.write("3. Profile to identify low-hanging fruit\n\n")

        # Machine info
        if 'machine_info' in data:
            info = data['machine_info']
            out.write("## 💻 Test Environment\n\n")
            out.write(f"- **Platform**: {info.get('system', 'Unknown')} {info.get('release', '')}\n")
            out.write(f"- **Processor**: {info.get('processor', 'Unknown')}\n")
            out.write(f"- **Python**: {info.get('python_version', 'Unknown')}\n")
            out.write(f"- **CPU Count**: {info.get('cpu', {}).get('count', 'Unknown')}\n")

    # Print to stdout
    with open(output_file, 'r') as out:
        print(out.read())

    # Return exit code based on violations
    if violations:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Check for performance regressions"
    )
    parser.add_argument(
        'benchmark_file',
        type=Path,
        help='Benchmark JSON file to check'
    )
    parser.add_argument(
        '--threshold',
        type=int,
        default=30,
        help='Percentage threshold for severe regression (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('regression-report.md'),
        help='Output markdown file (default: regression-report.md)'
    )

    args = parser.parse_args()

    if not args.benchmark_file.exists():
        print(f"❌ Error: File not found: {args.benchmark_file}", file=sys.stderr)
        sys.exit(1)

    try:
        exit_code = check_regressions(args.benchmark_file, args.threshold, args.output)
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
