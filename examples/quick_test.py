#!/usr/bin/env python3
"""
Quick Test Script - Try FLAC Detective Without Setup

This script demonstrates FLAC Detective using synthetic test data.
No FLAC files needed - perfect for a quick demo!
"""

import tempfile
import wave
import struct
import subprocess
from pathlib import Path

try:
    from flac_detective import FLACAnalyzer
    FLAC_DETECTIVE_INSTALLED = True
except ImportError:
    FLAC_DETECTIVE_INSTALLED = False


def create_test_wav(filepath, duration=1, sample_rate=44100, cutoff_freq=None):
    """Create a synthetic WAV file for testing."""
    import math

    num_samples = duration * sample_rate

    with wave.open(str(filepath), 'w') as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        for i in range(num_samples):
            # Generate sine wave
            t = i / sample_rate

            # Mix multiple frequencies
            value = 0
            for freq in [440, 880, 1320]:  # A4, A5, E6
                if cutoff_freq is None or freq < cutoff_freq:
                    value += math.sin(2 * math.pi * freq * t)

            # Apply cutoff to simulate MP3 transcode
            if cutoff_freq and i % 10 == 0:
                value *= 0.5  # Simulate compression

            # Convert to 16-bit integer
            sample = int(value * 10000)

            # Write stereo (same value for both channels)
            data = struct.pack('<hh', sample, sample)
            wav_file.writeframes(data)


def convert_wav_to_flac(wav_path, flac_path):
    """Convert WAV to FLAC using ffmpeg or flac command."""
    try:
        # Try with flac command first
        result = subprocess.run(
            ['flac', '--silent', '-f', str(wav_path), '-o', str(flac_path)],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        # Try with ffmpeg
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', str(wav_path), '-c:a', 'flac', str(flac_path)],
            capture_output=True,
            timeout=10,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False


def demo_without_flac_detective():
    """Show what FLAC Detective does (conceptual demo)."""
    print("=" * 70)
    print("FLAC Detective Demo (Conceptual)")
    print("=" * 70)
    print()
    print("FLAC Detective analyzes audio files to detect transcodes.")
    print()
    print("📊 Example Analysis Results:")
    print()
    print("File: authentic_rip.flac")
    print("  Verdict: ✅ AUTHENTIC (Score: 12/100)")
    print("  Reason: Full spectrum preserved, no artifacts")
    print("  → This is genuine lossless audio!")
    print()
    print("File: fake_320kbps.flac")
    print("  Verdict: ⚠️ SUSPICIOUS (Score: 72/100)")
    print("  Reason: MP3 192 kbps signature detected")
    print("  → This is likely a transcode from MP3")
    print()
    print("File: fake_128kbps.flac")
    print("  Verdict: ❌ FAKE_CERTAIN (Score: 103/100)")
    print("  Reason: MP3 128 kbps signature + cutoff at 16kHz")
    print("  → This is definitely a transcode!")
    print()
    print("-" * 70)
    print("To try the real tool:")
    print("  pip install flac-detective")
    print("  flac-detective /path/to/your/music")
    print("=" * 70)


def demo_with_flac_detective(temp_dir):
    """Run actual FLAC Detective demo with test files."""
    print("=" * 70)
    print("FLAC Detective Live Demo")
    print("=" * 70)
    print()
    print("Creating test files...")

    # Create authentic-like file
    authentic_wav = temp_dir / "authentic.wav"
    authentic_flac = temp_dir / "authentic.flac"
    create_test_wav(authentic_wav, duration=1, cutoff_freq=None)

    if not convert_wav_to_flac(authentic_wav, authentic_flac):
        print("⚠️  Could not convert WAV to FLAC (ffmpeg/flac not found)")
        print("Install ffmpeg or flac command-line tool to run this demo")
        demo_without_flac_detective()
        return

    # Create fake-like file (simulated transcode)
    fake_wav = temp_dir / "fake.wav"
    fake_flac = temp_dir / "fake.flac"
    create_test_wav(fake_wav, duration=1, cutoff_freq=16000)  # MP3 128kbps cutoff
    convert_wav_to_flac(fake_wav, fake_flac)

    print("✅ Test files created")
    print()

    # Analyze files
    analyzer = FLACAnalyzer(sample_duration=1.0)  # Quick analysis

    print("-" * 70)
    print("Analyzing: authentic.flac")
    print("-" * 70)
    result1 = analyzer.analyze_file(authentic_flac)
    print(f"Verdict: {result1['verdict']}")
    print(f"Score: {result1['score']}/100")
    print(f"Reason: {result1.get('reason', 'N/A')}")
    print()

    print("-" * 70)
    print("Analyzing: fake.flac (simulated transcode)")
    print("-" * 70)
    result2 = analyzer.analyze_file(fake_flac)
    print(f"Verdict: {result2['verdict']}")
    print(f"Score: {result2['score']}/100")
    print(f"Reason: {result2.get('reason', 'N/A')}")
    print()

    print("=" * 70)
    print("✨ Demo complete!")
    print()
    print("Note: These are synthetic test files for demonstration.")
    print("Real analysis works with actual FLAC music files.")
    print()
    print("Try it on your music collection:")
    print("  flac-detective /path/to/your/music")
    print("=" * 70)


def main():
    """Run the quick test demo."""
    print()
    print("🎵 FLAC Detective - Quick Test")
    print()

    if not FLAC_DETECTIVE_INSTALLED:
        print("⚠️  FLAC Detective is not installed.")
        print()
        print("To install and run the real tool:")
        print("  pip install flac-detective")
        print("  python quick_test.py")
        print()
        demo_without_flac_detective()
        return

    # Run live demo with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        demo_with_flac_detective(Path(temp_dir))


if __name__ == "__main__":
    main()
