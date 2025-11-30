"""Text report demonstration script."""

from pathlib import Path

from flac_detective.reporting.text_reporter import TextReporter

# Test data
demo_results = [
    {
        "filepath": "/music/album1/track01.flac",
        "filename": "01 - Intro.flac",
        "score": 100,
        "reason": "Full spectrum, excellent HF energy",
        "cutoff_freq": 22050,
        "duration_mismatch": False,
    },
    {
        "filepath": "/music/album1/track02.flac",
        "filename": "02 - Main Theme.flac",
        "score": 95,
        "reason": "Authentic",
        "cutoff_freq": 22050,
        "duration_mismatch": False,
    },
    {
        "filepath": "/music/album2/track01.flac",
        "filename": "Cash (Remix).flac",
        "score": 20,
        "reason": "Cutoff 16kHz (MP3 128kbps transcode)",
        "cutoff_freq": 16000,
        "duration_mismatch": False,
    },
    {
        "filepath": "/music/album2/track02.flac",
        "filename": "Summer Vibes.flac",
        "score": 65,
        "reason": "Low HF energy, suspicious",
        "cutoff_freq": 18500,
        "duration_mismatch": True,
        "duration_diff": 250,
    },
    {
        "filepath": "/music/album3/track01.flac",
        "filename": "Classical Symphony No.5.flac",
        "score": 98,
        "reason": "Authentic",
        "cutoff_freq": 22050,
        "duration_mismatch": False,
    },
    {
        "filepath": "/music/downloads/unknown.flac",
        "filename": "Unknown Artist - Unknown Track.flac",
        "score": 35,
        "reason": "Cutoff 16kHz + suspicious metadata (LAME)",
        "cutoff_freq": 16000,
        "duration_mismatch": True,
        "duration_diff": 1500,
    },
]

# Report generation
reporter = TextReporter()
output_file = Path("EXAMPLE_REPORT.txt")
reporter.generate_report(demo_results, output_file)

print(f"✅ Demo report generated : {output_file}")
print("\nReport content :\n")
print("=" * 100)
print(output_file.read_text(encoding="utf-8"))
