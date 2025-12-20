#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare two benchmark results and show differences.

Usage:
    python scripts/compare_benchmarks.py baseline.json current.json
    python scripts/compare_benchmarks.py baseline.json current.json > comparison.md
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


def format_change(baseline, current):
    """Format performance change percentage."""
    if baseline == 0:
        return "N/A"

    change = ((current - baseline) / baseline) * 100

    if abs(change) < 1:
        emoji = "➡️"  # Negligible
    elif change > 0:
        emoji = "🔴"  # Slower (regression)
    else:
        emoji = "🟢"  # Faster (improvement)

    return f"{emoji} {change:+.1f}%"


def load_benchmarks(file_path):
    """Load benchmarks from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Create lookup by test name
    benchmarks = {}
    for bench in data.get('benchmarks', []):
        name = bench['name']
        benchmarks[name] = bench['stats']

    return benchmarks


def compare_benchmarks(baseline_file, current_file):
    """Compare two benchmark files."""
    try:
        baseline = load_benchmarks(baseline_file)
    except Exception as e:
        print(f"⚠️ Could not load baseline: {e}")
        print("## No baseline available for comparison")
        return

    try:
        current = load_benchmarks(current_file)
    except Exception as e:
        print(f"❌ Error loading current benchmarks: {e}", file=sys.stderr)
        sys.exit(1)

    # Find common benchmarks
    common_tests = set(baseline.keys()) & set(current.keys())
    only_baseline = set(baseline.keys()) - set(current.keys())
    only_current = set(current.keys()) - set(baseline.keys())

    print("## 📊 Benchmark Comparison\n")

    if not common_tests:
        print("⚠️ **No common benchmarks found between baseline and current**\n")
        return

    print(f"**Common Tests**: {len(common_tests)}")
    print(f"**Only in Baseline**: {len(only_baseline)}")
    print(f"**New in Current**: {len(only_current)}\n")

    # Calculate improvements and regressions
    improvements = []
    regressions = []
    stable = []

    for test_name in common_tests:
        baseline_mean = baseline[test_name]['mean']
        current_mean = current[test_name]['mean']

        change_pct = ((current_mean - baseline_mean) / baseline_mean) * 100

        if change_pct < -5:  # 5% faster
            improvements.append((test_name, baseline_mean, current_mean, change_pct))
        elif change_pct > 5:  # 5% slower
            regressions.append((test_name, baseline_mean, current_mean, change_pct))
        else:
            stable.append((test_name, baseline_mean, current_mean, change_pct))

    # Print summary
    print("### Summary\n")
    print(f"- 🟢 **Improvements**: {len(improvements)} tests faster")
    print(f"- 🔴 **Regressions**: {len(regressions)} tests slower")
    print(f"- ➡️ **Stable**: {len(stable)} tests unchanged (±5%)\n")

    # Print regressions (most important)
    if regressions:
        print("### 🔴 Performance Regressions\n")
        print("| Test | Baseline | Current | Change |")
        print("|------|----------|---------|--------|")

        for test, baseline_mean, current_mean, change in sorted(regressions, key=lambda x: x[3], reverse=True):
            # Truncate long names
            display_name = test if len(test) <= 40 else test[:37] + "..."

            print(f"| {display_name} | "
                  f"{format_time(baseline_mean)} | "
                  f"{format_time(current_mean)} | "
                  f"{change:+.1f}% |")

        print()

        # Highlight severe regressions
        severe = [r for r in regressions if r[3] > 30]
        if severe:
            print("⚠️ **Severe Regressions (>30% slower)**:\n")
            for test, _, _, change in severe:
                print(f"- {test}: {change:+.1f}%")
            print()

    # Print improvements
    if improvements:
        print("### 🟢 Performance Improvements\n")
        print("| Test | Baseline | Current | Change |")
        print("|------|----------|---------|--------|")

        for test, baseline_mean, current_mean, change in sorted(improvements, key=lambda x: x[3]):
            display_name = test if len(test) <= 40 else test[:37] + "..."

            print(f"| {display_name} | "
                  f"{format_time(baseline_mean)} | "
                  f"{format_time(current_mean)} | "
                  f"{change:+.1f}% |")

        print()

    # Print new tests
    if only_current:
        print("### ✨ New Benchmarks\n")
        for test in sorted(only_current)[:10]:  # Show first 10
            mean = current[test]['mean']
            print(f"- {test}: {format_time(mean)}")

        if len(only_current) > 10:
            print(f"- ... and {len(only_current) - 10} more")

        print()

    # Print removed tests
    if only_baseline:
        print("### 🗑️ Removed Benchmarks\n")
        for test in sorted(only_baseline)[:10]:
            print(f"- {test}")

        if len(only_baseline) > 10:
            print(f"- ... and {len(only_baseline) - 10} more")

        print()

    # Overall verdict
    print("### 📊 Overall Verdict\n")

    if len(regressions) > len(improvements):
        print("⚠️ **More regressions than improvements detected**")
    elif len(improvements) > len(regressions):
        print("✅ **More improvements than regressions - good work!**")
    else:
        print("➡️ **Balanced changes - performance stable**")


def main():
    parser = argparse.ArgumentParser(
        description="Compare two benchmark results"
    )
    parser.add_argument(
        'baseline',
        type=Path,
        help='Baseline benchmark JSON file'
    )
    parser.add_argument(
        'current',
        type=Path,
        help='Current benchmark JSON file'
    )

    args = parser.parse_args()

    compare_benchmarks(args.baseline, args.current)


if __name__ == "__main__":
    main()
