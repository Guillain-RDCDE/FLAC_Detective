#!/usr/bin/env python3
"""
Basic FLAC Detective Usage Example

This example demonstrates the simplest way to use FLAC Detective
to analyze a single FLAC file or directory.
"""

from pathlib import Path
from flac_detective import FLACAnalyzer


def main():
    # Create an analyzer instance
    analyzer = FLACAnalyzer()

    # Example 1: Analyze a single file
    print("=" * 70)
    print("Example 1: Analyzing a single file")
    print("=" * 70)

    # Replace with your FLAC file path
    file_path = Path("path/to/your/file.flac")

    if file_path.exists():
        result = analyzer.analyze_file(file_path)

        print(f"\nFile: {result['filepath']}")
        print(f"Verdict: {result['verdict']}")
        print(f"Score: {result['score']}/100")
        print(f"Reason: {result['reason']}")

        # Interpret the verdict
        if result['verdict'] == 'AUTHENTIC':
            print("\n✅ This file is genuine lossless audio!")
        elif result['verdict'] == 'WARNING':
            print("\n⚡ This file needs manual verification.")
        elif result['verdict'] == 'SUSPICIOUS':
            print("\n⚠️ This file is likely a transcode.")
        else:  # FAKE_CERTAIN
            print("\n❌ This file is definitely a transcode.")
    else:
        print(f"File not found: {file_path}")
        print("Please update the file_path variable with a valid FLAC file.")

    # Example 2: Analyze a directory
    print("\n" + "=" * 70)
    print("Example 2: Analyzing a directory")
    print("=" * 70)

    # Replace with your directory path
    directory_path = Path("path/to/your/music/folder")

    if directory_path.exists() and directory_path.is_dir():
        # Find all FLAC files
        flac_files = list(directory_path.glob("**/*.flac"))
        print(f"\nFound {len(flac_files)} FLAC files")

        # Analyze first 3 files as example
        for i, flac_file in enumerate(flac_files[:3], 1):
            result = analyzer.analyze_file(flac_file)
            print(f"\n{i}. {flac_file.name}")
            print(f"   Verdict: {result['verdict']} | Score: {result['score']}")

        if len(flac_files) > 3:
            print(f"\n... and {len(flac_files) - 3} more files")
    else:
        print(f"Directory not found: {directory_path}")
        print("Please update the directory_path variable with a valid directory.")


if __name__ == "__main__":
    main()
