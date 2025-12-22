#!/usr/bin/env python3
"""
JSON Export and Parsing Example

This example demonstrates how to export results to JSON format
and parse them for custom reporting or integration with other tools.
"""

import json
from pathlib import Path
from datetime import datetime
from flac_detective import FLACAnalyzer


def analyze_and_export(directory, output_file):
    """Analyze directory and export results to JSON."""
    analyzer = FLACAnalyzer()

    # Find all FLAC files
    flac_files = list(directory.glob("**/*.flac"))

    if not flac_files:
        print(f"No FLAC files found in {directory}")
        return None

    print(f"Analyzing {len(flac_files)} files...")

    results = {
        'scan_info': {
            'timestamp': datetime.now().isoformat(),
            'directory': str(directory),
            'total_files': len(flac_files),
        },
        'files': []
    }

    for i, flac_file in enumerate(flac_files, 1):
        print(f"[{i}/{len(flac_files)}] {flac_file.name}", end="\r")
        result = analyzer.analyze_file(flac_file)
        results['files'].append(result)

    print()  # New line

    # Export to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results exported to {output_file}")
    return results


def parse_json_results(json_file):
    """Parse JSON results and generate custom report."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("\n" + "=" * 70)
    print("JSON Analysis Report")
    print("=" * 70)

    # Scan info
    info = data['scan_info']
    print(f"\nScan Date: {info['timestamp']}")
    print(f"Directory: {info['directory']}")
    print(f"Total Files: {info['total_files']}")

    # Group by verdict
    files_by_verdict = {
        'AUTHENTIC': [],
        'WARNING': [],
        'SUSPICIOUS': [],
        'FAKE_CERTAIN': []
    }

    for file_result in data['files']:
        verdict = file_result['verdict']
        files_by_verdict[verdict].append(file_result)

    # Print verdicts summary
    print("\n" + "-" * 70)
    print("Verdicts Summary:")
    print("-" * 70)
    for verdict, files in files_by_verdict.items():
        emoji = {'AUTHENTIC': '✅', 'WARNING': '⚡', 'SUSPICIOUS': '⚠️', 'FAKE_CERTAIN': '❌'}[verdict]
        print(f"{emoji} {verdict:13s}: {len(files):4d} files")

    # Show files to delete (FAKE_CERTAIN)
    if files_by_verdict['FAKE_CERTAIN']:
        print("\n" + "-" * 70)
        print("Files to DELETE (FAKE_CERTAIN):")
        print("-" * 70)
        for file_result in files_by_verdict['FAKE_CERTAIN']:
            path = Path(file_result['filepath'])
            print(f"  rm \"{path}\"  # Score: {file_result['score']}")

    # Show files to review (SUSPICIOUS + WARNING)
    review_files = files_by_verdict['SUSPICIOUS'] + files_by_verdict['WARNING']
    if review_files:
        print("\n" + "-" * 70)
        print("Files to REVIEW (SUSPICIOUS + WARNING):")
        print("-" * 70)
        for file_result in sorted(review_files, key=lambda x: x['score'], reverse=True)[:10]:
            path = Path(file_result['filepath'])
            print(f"  {file_result['verdict']:12s} | Score: {file_result['score']:3d} | {path.name}")
        if len(review_files) > 10:
            print(f"  ... and {len(review_files) - 10} more files")

    # Calculate average scores by verdict
    print("\n" + "-" * 70)
    print("Average Scores by Verdict:")
    print("-" * 70)
    for verdict, files in files_by_verdict.items():
        if files:
            avg_score = sum(f['score'] for f in files) / len(files)
            print(f"  {verdict:13s}: {avg_score:5.1f}")


def main():
    # Configuration
    directory = Path("path/to/your/music")
    output_file = Path("flac_analysis_results.json")

    if not directory.exists():
        print(f"Directory not found: {directory}")
        print("Please update the 'directory' variable with a valid path.")
        return

    # Step 1: Analyze and export
    print("Step 1: Analyzing and exporting to JSON...")
    results = analyze_and_export(directory, output_file)

    if results:
        # Step 2: Parse and generate custom report
        print("\nStep 2: Parsing JSON and generating report...")
        parse_json_results(output_file)

        # Bonus: Show how to filter files programmatically
        print("\n" + "=" * 70)
        print("Bonus: Programmatic Filtering")
        print("=" * 70)

        # Example: Find all files with score > 70
        high_score_files = [
            f for f in results['files']
            if f['score'] > 70
        ]
        print(f"\nFiles with score > 70: {len(high_score_files)}")

        # Example: Find all files with specific reason
        mp3_192_files = [
            f for f in results['files']
            if '192' in f.get('reason', '')
        ]
        print(f"Files with MP3 192 kbps signature: {len(mp3_192_files)}")


if __name__ == "__main__":
    main()
