#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a markdown benchmark report from pytest-benchmark JSON output.

Usage:
    python scripts/generate_benchmark_report.py output.json
    python scripts/generate_benchmark_report.py output.json > report.md
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


def format_ops(ops_per_sec):
    """Format operations per second."""
    if ops_per_sec >= 1e6:
        return f"{ops_per_sec / 1e6:.2f}M ops/s"
    elif ops_per_sec >= 1e3:
        return f"{ops_per_sec / 1e3:.2f}K ops/s"
    else:
        return f"{ops_per_sec:.2f} ops/s"


def generate_report(benchmark_file):
    """Generate benchmark report from JSON file."""
    with open(benchmark_file, 'r') as f:
        data = json.load(f)

    benchmarks = data.get('benchmarks', [])

    if not benchmarks:
        print("⚠️ No benchmarks found in file")
        return

    # Group benchmarks by test file
    groups = {}
    for bench in benchmarks:
        group = bench.get('group', 'default')
        if group not in groups:
            groups[group] = []
        groups[group].append(bench)

    # Print summary
    print("## 📊 Performance Benchmark Report\n")
    print(f"**Total Benchmarks**: {len(benchmarks)}")
    print(f"**Test Groups**: {len(groups)}\n")

    # Print overall statistics
    all_means = [b['stats']['mean'] for b in benchmarks]
    all_medians = [b['stats']['median'] for b in benchmarks]

    print("### Overall Statistics\n")
    print(f"- **Fastest Test**: {format_time(min(all_means))}")
    print(f"- **Slowest Test**: {format_time(max(all_means))}")
    print(f"- **Average Time**: {format_time(sum(all_means) / len(all_means))}")
    print(f"- **Median Time**: {format_time(sorted(all_medians)[len(all_medians) // 2])}\n")

    # Print benchmarks by group
    for group_name, group_benchmarks in sorted(groups.items()):
        print(f"### {group_name}\n")
        print("| Test | Mean | Min | Max | Std Dev | Ops/s |")
        print("|------|------|-----|-----|---------|-------|")

        for bench in sorted(group_benchmarks, key=lambda x: x['stats']['mean']):
            name = bench['name']
            stats = bench['stats']

            # Truncate long names
            if len(name) > 50:
                name = name[:47] + "..."

            print(f"| {name} | "
                  f"{format_time(stats['mean'])} | "
                  f"{format_time(stats['min'])} | "
                  f"{format_time(stats['max'])} | "
                  f"{format_time(stats['stddev'])} | "
                  f"{format_ops(stats.get('ops', 0))} |")

        print()

    # Print slowest benchmarks
    print("### 🐢 Slowest 5 Benchmarks\n")
    slowest = sorted(benchmarks, key=lambda x: x['stats']['mean'], reverse=True)[:5]

    for i, bench in enumerate(slowest, 1):
        print(f"{i}. **{bench['name']}**: {format_time(bench['stats']['mean'])}")

    print()

    # Print fastest benchmarks
    print("### ⚡ Fastest 5 Benchmarks\n")
    fastest = sorted(benchmarks, key=lambda x: x['stats']['mean'])[:5]

    for i, bench in enumerate(fastest, 1):
        print(f"{i}. **{bench['name']}**: {format_time(bench['stats']['mean'])}")

    print()

    # Print performance grades
    print("### 📈 Performance Grades\n")

    # Categorize by speed
    very_fast = sum(1 for b in benchmarks if b['stats']['mean'] < 0.001)  # < 1ms
    fast = sum(1 for b in benchmarks if 0.001 <= b['stats']['mean'] < 0.01)  # 1-10ms
    moderate = sum(1 for b in benchmarks if 0.01 <= b['stats']['mean'] < 0.1)  # 10-100ms
    slow = sum(1 for b in benchmarks if 0.1 <= b['stats']['mean'] < 1.0)  # 100ms-1s
    very_slow = sum(1 for b in benchmarks if b['stats']['mean'] >= 1.0)  # > 1s

    print(f"- ⚡ Very Fast (< 1ms): {very_fast}")
    print(f"- 🚀 Fast (1-10ms): {fast}")
    print(f"- ⏱️ Moderate (10-100ms): {moderate}")
    print(f"- 🐌 Slow (100ms-1s): {slow}")
    print(f"- 🐢 Very Slow (> 1s): {very_slow}")

    print()

    # Machine info
    if 'machine_info' in data:
        info = data['machine_info']
        print("### 💻 Machine Info\n")
        print(f"- **Platform**: {info.get('system', 'Unknown')} {info.get('release', '')}")
        print(f"- **Processor**: {info.get('processor', 'Unknown')}")
        print(f"- **Python**: {info.get('python_version', 'Unknown')}")
        print(f"- **CPU Count**: {info.get('cpu', {}).get('count', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate benchmark report from pytest-benchmark JSON"
    )
    parser.add_argument(
        'benchmark_file',
        type=Path,
        help='Path to pytest-benchmark JSON output file'
    )

    args = parser.parse_args()

    if not args.benchmark_file.exists():
        print(f"❌ Error: File not found: {args.benchmark_file}", file=sys.stderr)
        sys.exit(1)

    try:
        generate_report(args.benchmark_file)
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
