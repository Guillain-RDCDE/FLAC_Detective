#!/usr/bin/env python3
"""
Batch Processing Example

This example shows how to analyze multiple directories and generate
a comprehensive report with statistics.
"""

import json
from pathlib import Path
from collections import Counter
from flac_detective import FLACAnalyzer


def analyze_directory(analyzer, directory):
    """Analyze all FLAC files in a directory."""
    flac_files = list(directory.glob("**/*.flac"))

    if not flac_files:
        print(f"No FLAC files found in {directory}")
        return []

    print(f"Analyzing {len(flac_files)} files in {directory.name}...")

    results = []
    for i, flac_file in enumerate(flac_files, 1):
        print(f"  [{i}/{len(flac_files)}] {flac_file.name}", end="\r")
        result = analyzer.analyze_file(flac_file)
        results.append(result)

    print()  # New line after progress
    return results


def print_statistics(results, directory_name):
    """Print statistics for analyzed files."""
    total = len(results)
    verdicts = Counter(r['verdict'] for r in results)

    print(f"\n{'=' * 70}")
    print(f"Statistics for {directory_name}")
    print(f"{'=' * 70}")
    print(f"Total files analyzed: {total}")
    print(f"  ✅ Authentic:     {verdicts['AUTHENTIC']:4d} ({verdicts['AUTHENTIC']/total*100:5.1f}%)")
    print(f"  ⚡ Warning:       {verdicts['WARNING']:4d} ({verdicts['WARNING']/total*100:5.1f}%)")
    print(f"  ⚠️  Suspicious:   {verdicts['SUSPICIOUS']:4d} ({verdicts['SUSPICIOUS']/total*100:5.1f}%)")
    print(f"  ❌ Fake Certain:  {verdicts['FAKE_CERTAIN']:4d} ({verdicts['FAKE_CERTAIN']/total*100:5.1f}%)")

    # Show suspicious and fake files
    problematic = [r for r in results if r['verdict'] in ['SUSPICIOUS', 'FAKE_CERTAIN']]
    if problematic:
        print(f"\n⚠️  Problematic files ({len(problematic)}):")
        for result in problematic[:10]:  # Show first 10
            print(f"  - {Path(result['filepath']).name} [{result['verdict']}] Score: {result['score']}")
        if len(problematic) > 10:
            print(f"  ... and {len(problematic) - 10} more")


def main():
    # Create analyzer
    analyzer = FLACAnalyzer()

    # Define directories to analyze
    directories = [
        Path("path/to/music/artist1"),
        Path("path/to/music/artist2"),
        Path("path/to/music/artist3"),
    ]

    all_results = []

    for directory in directories:
        if not directory.exists():
            print(f"Directory not found: {directory}")
            continue

        results = analyze_directory(analyzer, directory)

        if results:
            print_statistics(results, directory.name)
            all_results.extend(results)

    # Overall statistics
    if all_results:
        print_statistics(all_results, "ALL DIRECTORIES")

        # Save results to JSON
        output_file = Path("batch_analysis_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 Detailed results saved to: {output_file}")
    else:
        print("\nNo files were analyzed. Please check your directory paths.")


if __name__ == "__main__":
    main()
