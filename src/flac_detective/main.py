#!/usr/bin/env python3
"""FLAC Detective v0.1 - Advanced FLAC Authenticity Analyzer.

Hunting Down Fake FLACs Since 2025

Multi-criteria detection:
- Spectral frequency analysis (MP3 cutoff detection)
- High-frequency energy ratio (context-aware)
- Metadata consistency validation
- Duration integrity checking
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from .analysis import FLACAnalyzer
from .config import analysis_config
from .reporting import TextReporter
from .tracker import ProgressTracker
from .utils import LOGO, find_flac_files

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_multiple_paths(user_input: str) -> list[str]:
    """Parse user input potentially containing multiple paths.

    Args:
        user_input: String entered by the user.

    Returns:
        List of raw paths (uncleaned).
    """
    if ";" in user_input:
        return [p.strip() for p in user_input.split(";")]
    elif "," in user_input:
        return [p.strip() for p in user_input.split(",")]
    return [user_input]


def _clean_path_string(path_str: str) -> str:
    """Cleans quotes from a path string.

    Args:
        path_str: Path string potentially surrounded by quotes.

    Returns:
        Cleaned path.
    """
    if path_str.startswith('"') and path_str.endswith('"'):
        return path_str[1:-1]
    elif path_str.startswith("'") and path_str.endswith("'"):
        return path_str[1:-1]
    return path_str


def _validate_paths(raw_paths: list[str]) -> list[Path]:
    """Validates and converts a list of raw paths to Path objects.

    Args:
        raw_paths: List of path strings.

    Returns:
        List of valid (existing) Paths.
    """
    valid_paths = []
    for raw_path in raw_paths:
        if not raw_path:
            continue

        cleaned = _clean_path_string(raw_path)
        path = Path(cleaned)

        if path.exists():
            valid_paths.append(path)
            print(f"  ✅ Added : {path.absolute()}")
        else:
            print(f"  ⚠️  Ignored (does not exist) : {raw_path}")

    return valid_paths


def get_user_input_path() -> list[Path]:
    """Asks user to enter one or more paths via interactive interface.

    Returns:
        List of paths (folders or files) to analyze.
    """
    print(LOGO)
    print("\n" + "═" * 75)
    print("  📂 INTERACTIVE MODE")
    print("═" * 75)
    print("  Drag and drop one or more folders/files below")
    print("  (You can separate multiple paths with commas or semicolons)")
    print("  (Or press Enter to analyze current folder)")
    print("═" * 75)

    while True:
        try:
            user_input = input("\n  👉 Path(s) : ").strip()

            # If empty, use current directory
            if not user_input:
                return [Path.cwd()]

            # Parse and validate paths
            raw_paths = _parse_multiple_paths(user_input)
            valid_paths = _validate_paths(raw_paths)

            if valid_paths:
                print(f"\n  📊 Total : {len(valid_paths)} location(s) selected")
                return valid_paths
            else:
                print("  ❌ No valid path found. Please try again.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye !")
            sys.exit(0)


def main():
    """Main function."""
    # Determine paths to analyze
    if len(sys.argv) > 1:
        # Command line mode: all arguments are paths
        paths = [Path(arg) for arg in sys.argv[1:]]
        invalid_paths = [p for p in paths if not p.exists()]
        if invalid_paths:
            logger.error(f"❌ Invalid paths : {', '.join(str(p) for p in invalid_paths)}")
            sys.exit(1)
        print(LOGO)
    else:
        # Interactive mode
        paths = get_user_input_path()

    print()
    print("=" * 70)
    print("  🎵 FLAC AUTHENTICITY ANALYZER")
    print("  Detection of MP3s transcoded to FLAC")
    print("  Method: Spectral analysis (like Fakin' The Funk)")
    print("=" * 70)
    print()

    # Collect all FLAC files from all paths
    all_flac_files = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".flac":
            # It's a FLAC file directly
            all_flac_files.append(path)
            logger.info(f"📄 File added : {path.name}")
        elif path.is_dir():
            # It's a folder, scan recursively
            flac_files = find_flac_files(path)
            all_flac_files.extend(flac_files)
        else:
            logger.warning(f"⚠️  Ignored (not a FLAC file or folder) : {path}")

    if not all_flac_files:
        logger.error("❌ No FLAC files found!")
        return

    # Determine output directory (for progress.json and report)
    # Use the directory of the first path, or current directory if it's a file
    output_dir = paths[0] if paths[0].is_dir() else paths[0].parent

    # Initialization
    analyzer = FLACAnalyzer(sample_duration=analysis_config.SAMPLE_DURATION)
    tracker = ProgressTracker(progress_file=output_dir / "progress.json")

    # Filter already processed files
    files_to_process = [f for f in all_flac_files if not tracker.is_processed(str(f))]

    if not files_to_process:
        logger.info("✅ All files have already been processed!")
        logger.info("Delete progress.json to restart analysis")
    else:
        tracker.set_total(len(all_flac_files))
        processed, total = tracker.get_progress()

        logger.info(f"📊 Resuming: {processed}/{total} files already processed")
        logger.info(f"🔄 {len(files_to_process)} files remaining to analyze")
        logger.info(f"⚡ Multi-threading: {analysis_config.MAX_WORKERS} workers")
        print()

        # Multi-threaded analysis
        with ThreadPoolExecutor(max_workers=analysis_config.MAX_WORKERS) as executor:
            futures = {executor.submit(analyzer.analyze_file, f): f for f in files_to_process}

            for future in as_completed(futures):
                result = future.result()
                tracker.add_result(result)

                # Progress display
                processed, total = tracker.get_progress()
                score_icon = (
                    "✅" if result["score"] >= 90 else "⚠️" if result["score"] >= 70 else "🚨"
                )

                logger.info(
                    f"[{processed}/{total}] {score_icon} {result['filename'][:50]} "
                    f"- Score: {result['score']}%"
                )

                # Periodic save
                if processed % analysis_config.SAVE_INTERVAL == 0:
                    tracker.save()
                    logger.info(f"💾 Progress saved ({processed}/{total})")

        # Final save
        tracker.save()

    # Generate text report
    logger.info("\n📊 Generating report...")
    results = tracker.get_results()

    output_file = output_dir / f"flac_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    reporter = TextReporter()
    reporter.generate_report(results, output_file)

    # Summary
    suspicious = [r for r in results if r["score"] < 90]
    print()
    print("=" * 70)
    print("  ✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"  📁 Files analyzed: {len(results)}")
    print(f"  ⚠️  Suspicious files: {len(suspicious)}")
    print(f"  📄 Text report: {output_file.name}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print("💾 Progress is saved in progress.json")
        print("🔄 Relaunch script to resume analysis")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
