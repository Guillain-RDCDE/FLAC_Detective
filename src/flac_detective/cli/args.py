"""Command-line arguments, and the interactive prompt shown when there are none."""

import argparse
import logging
import sys
from pathlib import Path

from ..__version__ import __version__
from ..colors import Colors, colorize
from ..config import analysis_config
from ..utils import LOGO
from .console import print_banner

logger = logging.getLogger(__name__)


def parse_multiple_paths(user_input: str) -> list[str]:
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


def clean_path_string(path_str: str) -> str:
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


def validate_paths(raw_paths: list[str]) -> list[Path]:
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

        cleaned = clean_path_string(raw_path)
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
            raw_paths = parse_multiple_paths(user_input)
            valid_paths = validate_paths(raw_paths)

            if valid_paths:
                print(f"\n  Total : {len(valid_paths)} location(s) selected")
                return valid_paths
            else:
                print(f"  {colorize('[XX]', Colors.RED)} No valid path found. Please try again.")

        except KeyboardInterrupt:
            print(f"\n\n{colorize('Goodbye !', Colors.CYAN)}")
            sys.exit(0)


def build_parser() -> argparse.ArgumentParser:
    """The CLI's argument parser, with every option and its help text."""
    parser = argparse.ArgumentParser(
        prog="flac-detective",
        description="Advanced FLAC authenticity analyzer — detects MP3-to-FLAC transcodes.",
        epilog="If no paths are given, an interactive prompt is shown.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="One or more FLAC files or directories to analyze.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"flac-detective {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output: log level DEBUG, show per-rule scoring details.",
    )
    parser.add_argument(
        "--sample-duration",
        type=float,
        default=None,
        metavar="SECS",
        help=(
            "Seconds of audio read per window, three windows per file (default: 30, "
            "range 5-120). Every published accuracy figure was measured at 30. A "
            "longer sample reads different audio, not the same audio better; a "
            "verdict that changes with this number is sitting on a reading boundary "
            "(see ml/exchange/SAMPLE_DURATION_MEASUREMENT_2026-09-07.md)."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="N",
        help=(
            f"Number of parallel worker processes (default: CPU count, capped at "
            f"{analysis_config.WORKER_CAP}). Use 1 to analyse in this process, with no "
            "workers to spawn at all — the answer if the run dies with 'WinError 1450' "
            "or a BrokenProcessPool, which is a start-up failure and not a problem with "
            "your files."
        ),
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help=(
            "Deep mode: run the ML rule (12) on every file, even ones the fast "
            "heuristics clear instantly. Slower (decode + CNN per file), but catches "
            "high-bitrate MP3 and Apple AAC transcodes that leave no heuristic "
            "trace (ffmpeg-family AAC, Vorbis, Opus and HE-AAC v2 are already read in a "
            "normal scan). Surfaces them as WARNING for review. "
            "Not an on/off switch: with the [ml] extra installed, the ML rule runs on "
            "files the fast heuristics leave in doubt whether or not this flag is given."
        ),
    )
    parser.add_argument(
        "--repair-in-place",
        action="store_true",
        help=(
            "When a FLAC cannot be decoded at all and the lossless repair (Xiph's flac "
            "tool, same samples, tags kept) succeeds, replace the file in your library "
            "with the repaired one, keeping a .corrupted.bak beside it. Off by default: "
            "a scan reads your library and writes nothing in it. Without this flag the "
            "repaired copy is analysed from the temp directory and discarded."
        ),
    )
    parser.add_argument(
        "--advanced",
        action="store_true",
        help=(
            "Advanced output: show the plumbing — numeric scores, detected cutoff and "
            "MP3 bitrate, and the per-rule reasoning. Default ('easy') mode hides all "
            "that and prints a plain-language verdict and recommended action per file."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path of the report file to write (default: auto-named in the work directory).",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "Directory for progress.json (resume state), the auto-named report and the "
            "console log. Default: the scan directory; if that is read-only (external "
            "drive, container ':ro' mount) the current directory is used instead. "
            "Created if missing."
        ),
    )
    parser.add_argument(
        "--progress-events",
        type=str,
        default=None,
        metavar="DEST",
        help=(
            "Report progress WITHIN each file, as one JSON object per line, for an "
            "application driving this as a subprocess. '-' writes to stderr (stdout "
            "stays reserved for the report); anything else is a file path, truncated "
            "at start. Off by default. Each line carries event, file, stage, index and "
            "total, where stage is prepare/metadata/spectrum/quality/scoring/done. "
            "There is no percentage: which rules run depends on what the earlier ones "
            "found, so the time left inside a file is not knowable when it is opened."
        ),
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv", "html"],
        default="text",
        help=(
            "Report format: 'text' (human-readable, default), 'json' (machine-readable), "
            "'csv' (one row per file, ranked most-suspicious first — for triaging a "
            "whole library in a spreadsheet), or 'html' (a single self-contained page "
            "with a sortable triage table and a spectrum plot for each flagged file)."
        ),
    )
    return parser


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments and (if none provided) prompt the user interactively.

    Returns:
        argparse.Namespace with `.paths` (list[Path]) and the rest of the
        options. `.paths` is always non-empty on return — either provided on
        the command line or collected interactively.
    """
    parser = build_parser()
    args = parser.parse_args()

    # Bounds check sample-duration (argparse `choices` only does discrete values)
    if args.sample_duration is not None and not (5.0 <= args.sample_duration <= 120.0):
        parser.error(
            f"--sample-duration must be between 5 and 120 seconds (got {args.sample_duration})"
        )

    # A worker count is a resource decision, so it is applied to the config here
    # and read from there everywhere — the CLI, the GUI worker and the pool all
    # take the same number rather than each having an opinion.
    if args.workers is not None:
        if args.workers < 1:
            parser.error(f"--workers must be 1 or more (got {args.workers})")
        analysis_config.MAX_WORKERS = args.workers

    if not args.paths:
        args.paths = get_user_input_path()
        return args

    invalid_paths = [p for p in args.paths if not p.exists()]
    if invalid_paths:
        logger.error(f"Invalid paths : {', '.join(str(p) for p in invalid_paths)}")
        sys.exit(1)
    # The banner goes to stderr whenever stdout carries data rather than a
    # report for a human. `--format json | jq .` failed on the first byte
    # because the ANSI-coloured logo was in front of the JSON (Provir,
    # 2026-08-31). stderr is what decoration is for; the data stream stays clean.
    print_banner(machine_readable=args.format != "text")
    return args
