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
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

# RICH INTEGRATION
try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
    )
    from rich.logging import RichHandler
    from rich.theme import Theme
    
    # Custom theme for FLAC Detective
    custom_theme = Theme({
        "info": "dim cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "fake": "bold red",
        "suspicious": "bold yellow",
        "authentic": "bold green",
    })
    
    console = Console(theme=custom_theme)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

from .analysis import FLACAnalyzer
from .config import analysis_config
from .reporting import TextReporter
from .tracker import ProgressTracker
from .utils import LOGO, find_flac_files, find_non_flac_audio_files
from .colors import Colors, colorize

# Fix Windows console encoding for UTF-8 support (Standard approach)
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")

# Configure Logging
# If Rich is available, we use RichHandler for beautiful console logs
# But we ALWAYS keep a FileHandler for the persistent log file
def setup_logging(output_dir: Path) -> Path:
    """Setup logging: Rich for console (if avail), File for persistence.

    Args:
        output_dir: Directory where the log file will be saved.

    Returns:
        Path to the created log file.
    """
    log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = output_dir / f"flac_console_log_{log_timestamp}.txt"

    # Root logger
    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    root_log.handlers = []

    # File Handler (Always detailed)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    file_handler.setFormatter(file_formatter)
    root_log.addHandler(file_handler)

    # Console Handler
    if HAS_RICH:
        # Rich Handler for beautiful output
        rich_handler = RichHandler(
            console=console, 
            show_time=True, 
            omit_repeated_times=False,
            show_path=False,
            rich_tracebacks=True
        )
        rich_handler.setLevel(logging.INFO)
        root_log.addHandler(rich_handler)
    else:
        # Standard Console Handler (Legacy fallback)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(file_formatter)
        root_log.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    if not HAS_RICH:
        logger.info(f"Console log will be saved to: {log_file}")
    else:
        console.print(f"[dim]Log file: {log_file}[/dim]")
        
    return log_file

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
            print(f"  {colorize('[OK]', Colors.GREEN)} Added : {path.absolute()}")
        else:
            print(f"  {colorize('[!!]', Colors.YELLOW)} Ignored (does not exist) : {raw_path}")

    return valid_paths


def get_user_input_path() -> list[Path]:
    """Asks user to enter one or more paths via interactive interface.

    Returns:
        List of paths (folders or files) to analyze.
    """
    print(LOGO)
    print("\n" + colorize("═" * 75, Colors.CYAN))
    print(f"  {colorize('INTERACTIVE MODE', Colors.BRIGHT_WHITE)}")
    print(colorize("═" * 75, Colors.CYAN))
    print("  Drag and drop one or more folders/files below")
    print("  (You can separate multiple paths with commas or semicolons)")
    print("  (Or press Enter to analyze current folder)")
    print(colorize("═" * 75, Colors.CYAN))

    while True:
        try:
            user_input = input(f"\n  {colorize('Path(s)', Colors.BRIGHT_YELLOW)} : ").strip()

            # If empty, use current directory
            if not user_input:
                return [Path.cwd()]

            # Parse and validate paths
            raw_paths = _parse_multiple_paths(user_input)
            valid_paths = _validate_paths(raw_paths)

            if valid_paths:
                print(f"\n  Total : {len(valid_paths)} location(s) selected")
                return valid_paths
            else:
                print(f"  {colorize('[XX]', Colors.RED)} No valid path found. Please try again.")

        except KeyboardInterrupt:
            print(f"\n\n{colorize('Goodbye !', Colors.CYAN)}")
            sys.exit(0)


def setup_logging(output_dir: Path) -> Path:
    """Setup file logging to capture console output.

    Args:
        output_dir: Directory where the log file will be saved.

    Returns:
        Path to the created log file.
    """
    log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = output_dir / f"flac_console_log_{log_timestamp}.txt"

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)

    logger.info(f"Console log will be saved to: {log_file}")
    return log_file


def parse_arguments() -> list[Path]:
    """Determine paths to analyze from command line or interactive input.

    Returns:
        List of paths to analyze.
    """
    if len(sys.argv) > 1:
        # Command line mode: all arguments are paths
        paths = [Path(arg) for arg in sys.argv[1:]]
        invalid_paths = [p for p in paths if not p.exists()]
        if invalid_paths:
            logger.error(f"Invalid paths : {', '.join(str(p) for p in invalid_paths)}")
            sys.exit(1)
        print(LOGO)
        return paths
    else:
        # Interactive mode
        return get_user_input_path()


def scan_files(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Scan paths for FLAC and non-FLAC audio files.

    Args:
        paths: List of paths to scan.

    Returns:
        Tuple of (all_flac_files, all_non_flac_files).
    """
    all_flac_files = []
    all_non_flac_files = []

    for path in paths:
        if path.is_file() and path.suffix.lower() == ".flac":
            # It's a FLAC file directly
            all_flac_files.append(path)
            logger.info(f"File added : {path.name}")
        elif path.is_dir():
            # It's a folder, scan recursively for FLAC
            flac_files = find_flac_files(path)
            all_flac_files.extend(flac_files)

            # Also scan for non-FLAC audio files
            non_flac_files = find_non_flac_audio_files(path)
            all_non_flac_files.extend(non_flac_files)
        else:
            logger.warning(f"Ignored (not a FLAC file or folder) : {path}")

    return all_flac_files, all_non_flac_files


def _get_score_icon(score: int) -> str:
    """Get colored icon based on score.

    Args:
        score: Analysis score (0-100).

    Returns:
        Colored icon string.
    """
    if score >= 80:  # FAKE_CERTAIN
        return colorize("[FAKE]", Colors.RED)
    elif score >= 50:  # FAKE_PROBABLE
        return colorize("[SUSP]", Colors.YELLOW)
    elif score >= 30:  # DOUTEUX
        return colorize("[?]", Colors.YELLOW)
    else:  # AUTHENTIQUE
        return colorize("[OK]", Colors.GREEN)


def _log_formatted_result(result: dict, processed: int, total: int):
    """Log analysis result with Rich formatting.
    
    Args:
        result: Analysis result dictionary.
        processed: Number of files processed.
        total: Total number of files.
    """
    score = result.get("score", 0)
    verdict = result.get("verdict", "UNKNOWN")
    filename = result['filename']
    
    # Icons and Styles
    if score >= 80: 
        icon = "❌"
        style = "fake"
        verdict = "FAKE"
    elif score >= 50: 
        icon = "⚠️ "
        style = "suspicious"
        verdict = "SUSPICIOUS"
    elif score >= 30: 
        icon = "❓"
        style = "warning"
        verdict = "WARNING"
    else: 
        icon = "✅"
        style = "authentic"
        verdict = "AUTHENTIC"

    # Truncate filename gracefully
    if len(filename) > 50:
        filename = filename[:47] + "..."

    # Rich formatted message
    if HAS_RICH:
        # We rely on RichHandler for the timestamp and base formatting
        # Here we just construct the nice message content
        msg = f"[{style}]{icon} {verdict:<12} {score:>3}/100[/]  {filename}"
        logger.info(msg, extra={"markup": True})
    else:
        # Fallback for standard logging
        score_str = f"{score}/100"
        msg = f"[{processed:03d}/{total:03d}] {icon} {verdict:<12} {score_str:>7}  {filename}"
        logger.info(msg)



def _create_non_flac_result(non_flac_file: Path) -> dict:
    """Create a result dictionary for a non-FLAC audio file.

    Args:
        non_flac_file: Path to the non-FLAC file.

    Returns:
        Result dictionary.
    """
    extension = non_flac_file.suffix.upper()[1:]  # Remove the dot and uppercase
    return {
        "filepath": str(non_flac_file),
        "filename": non_flac_file.name,
        "score": 100,  # Maximum fake score for non-FLAC
        "verdict": "NON_FLAC",
        "confidence": "CERTAIN",
        "reason": f"NON-FLAC FILE ({extension}) - Must be replaced with authentic FLAC",
        "cutoff_freq": 0,
        "sample_rate": "N/A",
        "bit_depth": "N/A",
        "encoder": extension,
        "duration_mismatch": None,
        "duration_metadata": "N/A",
        "duration_real": "N/A",
        "duration_diff": "N/A",
        "has_clipping": False,
        "clipping_severity": "n/a",
        "clipping_percentage": 0.0,
        "has_dc_offset": False,
        "dc_offset_severity": "n/a",
        "dc_offset_value": 0.0,
        "is_corrupted": False,
        "corruption_error": None,
        "has_silence_issue": False,
        "silence_issue_type": "n/a",
        "is_fake_high_res": False,
        "estimated_bit_depth": 0,
        "is_upsampled": False,
        "suspected_original_rate": 0,
        "estimated_mp3_bitrate": 0,
    }


def _process_flac_files(
    files_to_process: list[Path],
    tracker: ProgressTracker,
    analyzer: FLACAnalyzer
):
    """Process FLAC files with multi-processing and rich progress.

    Args:
        files_to_process: List of FLAC files to analyze.
        tracker: Progress tracker instance.
        analyzer: FLAC analyzer instance.
    """
    total_files = len(files_to_process)
    
    # Define Progress Bar Columns
    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
    ]
    
    # Use Rich Progress if available
    if HAS_RICH:
        progress_ctx = Progress(*columns, console=console)
    else:
        # Dummy context manager for no-rich mode
        from contextlib import nullcontext
        progress_ctx = nullcontext()

    with ProcessPoolExecutor(max_workers=analysis_config.MAX_WORKERS) as executor:
        futures = {executor.submit(analyzer.analyze_file, f): f for f in files_to_process}
        
        processed_count = 0
        
        # Start Progress Block
        if HAS_RICH:
             with progress_ctx as progress:
                task_id = progress.add_task("[cyan]Analyzing audio files...", total=total_files)
                
                for future in as_completed(futures):
                    result = future.result()
                    tracker.add_result(result)
                    processed_count += 1
                    
                    # Update Progress
                    progress.update(task_id, advance=1)
                    
                    # Log result (will appear above progress bar thanks to RichHandler)
                    _log_formatted_result(result, processed_count, total_files)

                    # Periodic save
                    if processed_count % analysis_config.SAVE_INTERVAL == 0:
                        tracker.save()
        else:
            # Fallback for standard console
            for future in as_completed(futures):
                result = future.result()
                tracker.add_result(result)
                processed_count += 1
                
                _log_formatted_result(result, processed_count, total_files)

                if processed_count % analysis_config.SAVE_INTERVAL == 0:
                    tracker.save()


def _add_non_flac_results(all_non_flac_files: list[Path], tracker: ProgressTracker):
    """Add non-FLAC audio files to results.

    Args:
        all_non_flac_files: List of non-FLAC files.
        tracker: Progress tracker instance.
    """
    for non_flac_file in all_non_flac_files:
        result = _create_non_flac_result(non_flac_file)
        tracker.add_result(result)

    if all_non_flac_files:
        logger.info(f"\n{len(all_non_flac_files)} non-FLAC audio files added to report")


def run_analysis_loop(
    all_flac_files: list[Path],
    all_non_flac_files: list[Path],
    output_dir: Path
) -> list[dict]:
    """Run the main analysis loop on the provided files.

    Args:
        all_flac_files: List of FLAC files to analyze.
        all_non_flac_files: List of non-FLAC files to report.
        output_dir: Directory for saving progress and reports.

    Returns:
        List of result dictionaries.
    """
    # Initialization
    analyzer = FLACAnalyzer(sample_duration=analysis_config.SAMPLE_DURATION)
    tracker = ProgressTracker(progress_file=output_dir / "progress.json")

    # Filter already processed files
    files_to_process = [f for f in all_flac_files if not tracker.is_processed(str(f))]

    if not files_to_process:
        logger.info("All files have already been processed!")
        logger.info("Delete progress.json to restart analysis")
    else:
        tracker.set_total(len(all_flac_files))
        processed, total = tracker.get_progress()

        logger.info(f"Resuming: {processed}/{total} files already processed")
        logger.info(f"{len(files_to_process)} files remaining to analyze")
        logger.info(f"Multi-processing: {analysis_config.MAX_WORKERS} workers")
        print()

        # Multi-process analysis
        _process_flac_files(files_to_process, tracker, analyzer)

        # Final save
        tracker.save()

    # Add non-FLAC audio files to results
    _add_non_flac_results(all_non_flac_files, tracker)

    # Clean up progress file after successful completion
    tracker.cleanup()

    return tracker.get_results()


def generate_final_report(
    results: list[dict],
    output_dir: Path,
    all_flac_files: list[Path],
    all_non_flac_files: list[Path],
    log_file: Path,
    input_paths: list[Path]
):
    """Generate the final report and print summary.

    Args:
        results: List of analysis results.
        output_dir: Directory to save the report.
        all_flac_files: List of FLAC files analyzed.
        all_non_flac_files: List of non-FLAC files found.
        log_file: Path to the console log file.
        input_paths: List of user input paths (scan roots).
    """
    logger.info("\nGenerating report...")

    output_file = output_dir / f"flac_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    reporter = TextReporter()
    reporter.generate_report(results, output_file, scan_paths=input_paths)

    # Summary (NEW SCORING: score >= 50 = suspicious)
    suspicious_flac = [r for r in results if r.get("score", 0) >= 50 and r.get("verdict") not in ["NON_FLAC", "ERROR"]]
    fake_certain = [r for r in results if r.get("score", 0) >= 80 and r.get("verdict") not in ["NON_FLAC", "ERROR"]]
    non_flac_count = len(all_non_flac_files)

    print()
    print(colorize("=" * 70, Colors.CYAN))
    print(f"  {colorize('ANALYSIS COMPLETE', Colors.BRIGHT_GREEN)}")
    print(colorize("=" * 70, Colors.CYAN))
    print(f"  FLAC files analyzed: {len(all_flac_files)}")
    print(f"  {colorize('Fake/Suspicious FLAC files', Colors.RED)}: {len(suspicious_flac)} (including {len(fake_certain)} certain fakes)")
    if non_flac_count > 0:
        print(f"  {colorize('Non-FLAC files (need replacement)', Colors.RED)}: {non_flac_count}")
    print(f"  Text report: {output_file.name}")
    print(f"  Console log: {log_file.name}")
    print(colorize("=" * 70, Colors.CYAN))


def main():
    """Main function."""
    paths = parse_arguments()

    print()
    print(colorize("=" * 70, Colors.CYAN))
    print(f"  {colorize('FLAC AUTHENTICITY ANALYZER', Colors.BRIGHT_WHITE)}")
    print("  Detection of MP3s transcoded to FLAC")
    print("  Method: Advanced spectral analysis")
    print(colorize("=" * 70, Colors.CYAN))
    print()

    all_flac_files, all_non_flac_files = scan_files(paths)

    if not all_flac_files and not all_non_flac_files:
        logger.error("No audio files found!")
        return

    # Determine output directory (for progress.json and report)
    # Use the directory of the first path, or current directory if it's a file
    output_dir = paths[0] if paths[0].is_dir() else paths[0].parent

    log_file = setup_logging(output_dir)

    results = run_analysis_loop(all_flac_files, all_non_flac_files, output_dir)

    generate_final_report(results, output_dir, all_flac_files, all_non_flac_files, log_file, paths)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{colorize('Interrupted by user', Colors.YELLOW)}")
        print("Progress is saved in progress.json")
        print("Relaunch script to resume analysis")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
