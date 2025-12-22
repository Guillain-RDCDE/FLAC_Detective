#!/usr/bin/env python3
"""
API Integration Example

This example shows advanced usage of the FLAC Detective Python API,
including custom configuration, error handling, and integration patterns.
"""

from pathlib import Path
from flac_detective import FLACAnalyzer
from flac_detective.config import Config


def example_custom_configuration():
    """Example 1: Using custom analyzer configuration."""
    print("=" * 70)
    print("Example 1: Custom Configuration")
    print("=" * 70)

    # Create analyzer with custom sample duration (faster analysis)
    analyzer = FLACAnalyzer(sample_duration=15.0)

    print("Analyzing with 15-second sample (faster, less accurate)...")
    file_path = Path("path/to/your/file.flac")

    if file_path.exists():
        result = analyzer.analyze_file(file_path)
        print(f"Result: {result['verdict']} (Score: {result['score']})")
    else:
        print(f"File not found: {file_path}")

    # Create analyzer with longer sample (more accurate)
    analyzer_precise = FLACAnalyzer(sample_duration=60.0)

    print("\nAnalyzing with 60-second sample (slower, more accurate)...")
    if file_path.exists():
        result = analyzer_precise.analyze_file(file_path)
        print(f"Result: {result['verdict']} (Score: {result['score']})")


def example_error_handling():
    """Example 2: Proper error handling."""
    print("\n" + "=" * 70)
    print("Example 2: Error Handling")
    print("=" * 70)

    analyzer = FLACAnalyzer()

    test_files = [
        Path("valid_file.flac"),
        Path("corrupted_file.flac"),
        Path("nonexistent_file.flac"),
    ]

    for file_path in test_files:
        try:
            if not file_path.exists():
                print(f"\n❌ File not found: {file_path}")
                continue

            print(f"\nAnalyzing: {file_path.name}")
            result = analyzer.analyze_file(file_path)

            if result.get('error'):
                print(f"  ⚠️  Error: {result['error']}")
            else:
                print(f"  ✅ Success: {result['verdict']} (Score: {result['score']})")

        except Exception as e:
            print(f"  ❌ Exception: {e}")


def example_filtering_and_sorting():
    """Example 3: Filtering and sorting results."""
    print("\n" + "=" * 70)
    print("Example 3: Filtering and Sorting")
    print("=" * 70)

    analyzer = FLACAnalyzer()
    directory = Path("path/to/your/music")

    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    # Analyze all files
    flac_files = list(directory.glob("**/*.flac"))
    results = []

    print(f"Analyzing {len(flac_files)} files...")
    for flac_file in flac_files:
        result = analyzer.analyze_file(flac_file)
        results.append(result)

    # Filter: Only show problematic files
    print("\n--- Problematic Files (score >= 60) ---")
    problematic = [r for r in results if r['score'] >= 60]

    # Sort by score (descending)
    problematic.sort(key=lambda x: x['score'], reverse=True)

    for i, result in enumerate(problematic[:5], 1):
        path = Path(result['filepath'])
        print(f"{i}. {path.name}")
        print(f"   Score: {result['score']} | Verdict: {result['verdict']}")
        print(f"   Reason: {result['reason']}")

    # Filter: Only authentic files
    authentic = [r for r in results if r['verdict'] == 'AUTHENTIC']
    print(f"\n--- Authentic Files: {len(authentic)}/{len(results)} ---")

    # Calculate statistics
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0
    print(f"Average score: {avg_score:.1f}")


def example_integration_webhook():
    """Example 4: Integration with external systems (webhook simulation)."""
    print("\n" + "=" * 70)
    print("Example 4: External Integration (Webhook Simulation)")
    print("=" * 70)

    analyzer = FLACAnalyzer()
    directory = Path("path/to/your/music")

    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    def send_notification(title, message):
        """Simulate sending notification to external system."""
        print(f"\n📧 Notification: {title}")
        print(f"   {message}")

    flac_files = list(directory.glob("**/*.flac"))
    fake_count = 0

    for flac_file in flac_files:
        result = analyzer.analyze_file(flac_file)

        # Alert on fake files
        if result['verdict'] == 'FAKE_CERTAIN':
            fake_count += 1
            send_notification(
                title="Fake FLAC Detected!",
                message=f"File: {Path(result['filepath']).name} | Score: {result['score']}"
            )

    # Summary notification
    if fake_count > 0:
        send_notification(
            title="Scan Complete",
            message=f"Found {fake_count} fake files out of {len(flac_files)} analyzed."
        )
    else:
        send_notification(
            title="Scan Complete",
            message=f"All {len(flac_files)} files are authentic! 🎉"
        )


def example_parallel_processing():
    """Example 5: Parallel processing hint."""
    print("\n" + "=" * 70)
    print("Example 5: Parallel Processing (Concept)")
    print("=" * 70)

    print("""
For processing large collections, you can use Python's multiprocessing:

```python
from multiprocessing import Pool
from flac_detective import FLACAnalyzer

def analyze_file_worker(file_path):
    analyzer = FLACAnalyzer()
    return analyzer.analyze_file(file_path)

if __name__ == '__main__':
    flac_files = list(Path("music").glob("**/*.flac"))

    with Pool(processes=4) as pool:
        results = pool.map(analyze_file_worker, flac_files)

    print(f"Analyzed {len(results)} files in parallel")
```

Note: Each worker creates its own analyzer instance.
""")


def main():
    """Run all examples."""
    example_custom_configuration()
    example_error_handling()
    example_filtering_and_sorting()
    example_integration_webhook()
    example_parallel_processing()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nFor more information, see the documentation:")
    print("  - API Reference: docs/api-reference.md")
    print("  - User Guide: docs/user-guide.md")
    print("  - Technical Details: docs/technical-details.md")


if __name__ == "__main__":
    main()
