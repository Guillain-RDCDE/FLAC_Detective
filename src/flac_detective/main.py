#!/usr/bin/env python3
"""FLAC Detective - Advanced FLAC Authenticity Analyzer.

Hunting Down Fake FLACs Since 2025

The command-line entry point. The work is done by the ``flac_detective.cli``
package, one concern per module; this module wires them together in ``main``
and keeps every name it has historically exported (scripts and tests import
them from here).
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .__version__ import __version__
from .analysis.diagnostic_tracker import reset_tracker
from .cli import args as _args
from .cli import console as _console
from .cli import discovery as _discovery
from .cli import logsetup as _logsetup
from .cli import output as _output
from .cli import pool as _pool
from .cli import workdir as _workdir
from .cli.args import get_user_input_path, parse_arguments
from .cli.console import HAS_RICH, VERDICT_DISPLAY, console
from .cli.discovery import REJECTABLE_SUFFIXES, scan_files
from .cli.logsetup import ResilientFileHandler, setup_logging
from .cli.output import REAL_STDOUT, generate_final_report
from .cli.pool import run_analysis_loop
from .cli.update_flow import offer_update, print_install_report, run_update_command
from .cli.workdir import resolve_work_dir
from .colors import Colors, colorize
from .config import analysis_config
from .update_check import UpdateCheck
from .updater import consume_install_report
from .utils import LOGO

logger = logging.getLogger(__name__)

# Historical names, kept so that `from flac_detective.main import ...` keeps
# working for scripts and tests written against the single-module CLI.
_ResilientFileHandler = ResilientFileHandler
_writable_log_file = _logsetup.writable_log_file
_cleanup_console_log_if_empty = _logsetup.cleanup_console_log_if_empty
_is_writable_dir = _workdir.is_writable_dir
_parse_multiple_paths = _args.parse_multiple_paths
_clean_path_string = _args.clean_path_string
_validate_paths = _args.validate_paths
_print_banner = _console.print_banner
_make_streams_utf8_safe = _console.make_streams_utf8_safe
_log_formatted_result = _console.log_formatted_result
_VERDICT_DISPLAY = VERDICT_DISPLAY
_LOSSY_SUFFIXES = REJECTABLE_SUFFIXES
_create_non_flac_result = _discovery.create_non_flac_result
_add_non_flac_results = _discovery.add_non_flac_results
_progress_event_writer = _pool.progress_event_writer
_worker_event_channel = _pool.worker_event_channel
_analyze_batch = _pool.analyze_batch
_process_flac_files = _pool.process_flac_files
_write_report = _output.write_report
_REAL_STDOUT = REAL_STDOUT

__all__ = [
    "__version__",
    "main",
    "parse_arguments",
    "get_user_input_path",
    "scan_files",
    "resolve_work_dir",
    "setup_logging",
    "run_analysis_loop",
    "generate_final_report",
    "HAS_RICH",
    "console",
    "analysis_config",
    "Colors",
    "colorize",
    "LOGO",
]

# Work directory chosen by main() — read by the KeyboardInterrupt handler so the
# "progress saved in …" message names the real location (see resolve_work_dir).
_WORK_DIR: Optional[Path] = None


def _run() -> None:
    """The scan, start to finish: arguments, discovery, analysis, report."""
    global _WORK_DIR

    # Before ANY output: see cli.console.make_streams_utf8_safe.
    _console.make_streams_utf8_safe()
    # Fix Windows console encoding for UTF-8 support (standard approach). Once,
    # here, rather than at import: spawned workers re-import this module.
    _console.enable_utf8_console()
    # Reset diagnostic tracker at the start of analysis
    reset_tracker()

    args = parse_arguments()

    # A deferred (Windows) install from last time left its result: say it once.
    print_install_report(consume_install_report())

    # `flac-detective --update`: check PyPI now, install if newer, and stop.
    if args.update:
        sys.exit(run_update_command())

    # A machine-readable format with no --output means stdout carries DATA, so
    # every decorative print in the CLI has to go somewhere else. Reported by
    # Provir 2026-08-31: `--format json file.flac | jq .` failed on the first
    # byte, because stdout held the banner and the summary and the report itself
    # was quietly written to a timestamped file the caller never asked for.
    #
    # Rebinding sys.stdout is the surgical fix: every print() in the CLI
    # becomes correct at once, without auditing each one, and the report is
    # written to REAL_STDOUT at the end. The file is still written as before —
    # this adds a stream, it does not take one away.
    machine_stdout = args.format != "text" and not args.output
    if machine_stdout:
        sys.stdout = sys.stderr

    # Started here, on its own thread, so the network round trip overlaps the
    # scan; read at the very end. Off with --no-update-check or the environment
    # variable. See update_check.py for what is (not) sent.
    update_check = UpdateCheck(enabled=not args.no_update_check).start()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled (log level: DEBUG).")

    print()
    print(colorize("=" * 70, Colors.CYAN))
    print(f"  {colorize('FLAC AUTHENTICITY ANALYZER', Colors.BRIGHT_WHITE)}")
    print("  Detection of MP3s transcoded to FLAC")
    print("  Method: Advanced spectral analysis")
    print(colorize("=" * 70, Colors.CYAN))
    print()

    all_flac_files, all_non_flac_files = scan_files(args.paths)

    if not all_flac_files and not all_non_flac_files:
        logger.error("No audio files found!")
        return

    # Work directory for progress.json, the auto-named report and the console log:
    # --work-dir if given, else the scan directory, else (read-only scan dir) the
    # current directory. See resolve_work_dir().
    output_dir, work_dir_notes = resolve_work_dir(args.paths, args.work_dir)
    _WORK_DIR = output_dir

    log_file = setup_logging(output_dir)
    logger.info(f"Work directory (progress/report/log): {output_dir}")
    for note in work_dir_notes:
        # Console handlers are WARNING-level: this is how a fallback gets seen.
        logger.warning(note)

    with _pool.progress_event_writer(args.progress_events) as on_event:
        results = run_analysis_loop(
            all_flac_files,
            all_non_flac_files,
            output_dir,
            sample_duration=args.sample_duration,
            deep=args.deep,
            advanced=args.advanced,
            on_event=on_event,
            repair_in_place=args.repair_in_place,
        )

    generate_final_report(
        results,
        output_dir,
        all_flac_files,
        all_non_flac_files,
        log_file,
        args.paths,
        output_path=args.output,
        report_format=args.format,
        advanced=args.advanced,
    )

    # After the summary, where a reader's eye ends: the notice and, on a
    # terminal, the offer to install. In machine mode sys.stdout is stderr by
    # now, so the report on the real stdout stays clean, and nothing is asked:
    # a pipe, a cron job or an application driving this process must never
    # block on a question (see cli/update_flow.py).
    notice = update_check.notice(wait=1.0)
    if notice:
        unattended = machine_stdout or args.progress_events is not None
        offer_update(notice, interactive=False if unattended else None, latest=update_check.latest)


def main():
    """Console-script entry point (``flac-detective``).

    Ctrl-C is handled HERE, not only under ``if __name__ == "__main__"``: the
    installed command calls this function directly, and used to show a raw
    traceback where the script form printed where the progress was saved.
    """
    try:
        _run()
    except KeyboardInterrupt:
        print(f"\n\n{colorize('Interrupted by user', Colors.YELLOW)}")
        where = _WORK_DIR / "progress.json" if _WORK_DIR is not None else "progress.json"
        print(f"Progress is saved in {where}")
        print("Relaunch script to resume analysis")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
