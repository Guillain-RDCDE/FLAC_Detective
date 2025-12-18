#!/usr/bin/env python3
"""Compare scoring between two similar files to understand verdict differences."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flac_detective.analysis.analyzer import analyze_file

def compare_files(file1_path: str, file2_path: str):
    """Analyze two files and compare their scores."""
    
    file1 = Path(file1_path)
    file2 = Path(file2_path)
    
    if not file1.exists() or not file2.exists():
        print(f"Error: Files not found")
        print(f"  File 1: {file1}")
        print(f"  File 2: {file2}")
        return
    
    print("=" * 80)
    print("DETAILED COMPARISON: Two Similar Spectrograms, Different Verdicts")
    print("=" * 80)
    
    # Analyze file 1
    print(f"\n📁 FILE 1: {file1.name}")
    print("-" * 80)
    result1 = analyze_file(file1)
    print(f"  Cutoff: {result1.get('cutoff_freq', 'N/A')} Hz")
    print(f"  Bitrate: {result1.get('bitrate', 'N/A')} kbps")
    print(f"  Verdict: {result1.get('verdict', 'N/A')}")
    print(f"  Score: {result1.get('score', 'N/A')}")
    print(f"  Reason: {result1.get('reason', 'N/A')}")
    
    # Analyze file 2
    print(f"\n📁 FILE 2: {file2.name}")
    print("-" * 80)
    result2 = analyze_file(file2)
    print(f"  Cutoff: {result2.get('cutoff_freq', 'N/A')} Hz")
    print(f"  Bitrate: {result2.get('bitrate', 'N/A')} kbps")
    print(f"  Verdict: {result2.get('verdict', 'N/A')}")
    print(f"  Score: {result2.get('score', 'N/A')}")
    print(f"  Reason: {result2.get('reason', 'N/A')}")
    
    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)
    
    cutoff1 = result1.get('cutoff_freq', 0)
    cutoff2 = result2.get('cutoff_freq', 0)
    bitrate1 = result1.get('bitrate', 0)
    bitrate2 = result2.get('bitrate', 0)
    score1 = result1.get('score', 0)
    score2 = result2.get('score', 0)
    
    print(f"\n🔍 Cutoff Frequency Difference:")
    print(f"   File 1: {cutoff1} Hz")
    print(f"   File 2: {cutoff2} Hz")
    print(f"   Δ = {abs(cutoff1 - cutoff2)} Hz")
    
    print(f"\n💾 Bitrate Difference:")
    print(f"   File 1: {bitrate1} kbps")
    print(f"   File 2: {bitrate2} kbps")
    print(f"   Δ = {abs(bitrate1 - bitrate2)} kbps")
    
    print(f"\n📊 Score Difference:")
    print(f"   File 1: {score1} points → {result1.get('verdict')}")
    print(f"   File 2: {score2} points → {result2.get('verdict')}")
    print(f"   Δ = {abs(score1 - score2)} points")
    
    print(f"\n💡 Why different verdicts despite similar spectrograms?")
    print(f"   This is likely due to OTHER RULES (not just Rule 1)")
    print(f"   Check: metadata patterns, silence, artifacts, etc.")
    

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_two_files.py <file1> <file2>")
        print("\nExample:")
        print("  python compare_two_files.py 'D:\\FLAC\\...\\Soô.flac' 'D:\\FLAC\\...\\Need you.flac'")
        sys.exit(1)
    
    compare_files(sys.argv[1], sys.argv[2])
