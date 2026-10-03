"""The report files and the end-of-run summary."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..__version__ import __version__
from ..analysis.diagnostic_tracker import get_tracker
from ..colors import Colors, colorize
from ..presentation import verdict_plain
from ..reporting import CSVReporter, HTMLReporter, TextReporter
from ..reporting.common import rank_by_score
from .logsetup import cleanup_console_log_if_empty

logger = logging.getLogger(__name__)

# The real stdout, captured before anything can redirect it. When --format asks
# for machine-readable output and no --output path is given, the report goes
# here and every decorative print goes to stderr instead — see main().
REAL_STDOUT = sys.stdout

# Verdicts the console summary counts as "fake or suspicious".
SUMMARY_FLAGGED_VERDICTS = ("SUSPICIOUS", "FAKE_CERTAIN")

# How many of the most suspicious files the summary names before pointing at
# the report for the rest.
_TOP_N = 5

_REPORT_EXTENSION = {"json": "json", "csv": "csv", "html": "html"}


def json_payload(
    results: list[dict],
    input_paths: list[Path],
    total_flac_files: int,
    total_non_flac_files: int,
) -> dict:
    """The ``--format json`` document: scan metadata plus every result row.

    Shared with the GUI's export, so both read the same to a consumer.
    """
    return {
        "scan_info": {
            "timestamp": datetime.now().isoformat(),
            "analyzer_version": __version__,
            "scan_paths": [str(p) for p in input_paths],
            "total_flac_files": total_flac_files,
            "total_non_flac_files": total_non_flac_files,
        },
        "results": results,
    }


def write_report(
    results: list[dict],
    output_file: Path,
    report_format: str,
    input_paths: list[Path],
    all_flac_files: list[Path],
    all_non_flac_files: list[Path],
    advanced: bool = False,
) -> None:
    """Write ``results`` to ``output_file`` in the requested format.

    Args:
        results: Per-file analysis result dicts.
        output_file: Destination path (extension already chosen by the caller).
        report_format: "text", "json", "csv" or "html".
        input_paths: Scan roots (passed to reporters for relative paths / scan_info).
        all_flac_files: All FLAC files analyzed (json scan_info only).
        all_non_flac_files: All non-FLAC files found (json scan_info only).
        advanced: Text report verbosity — easy (plain language) vs advanced (plumbing).
    """
    if report_format == "json":
        payload = json_payload(results, input_paths, len(all_flac_files), len(all_non_flac_files))
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    elif report_format == "csv":
        CSVReporter().generate_report(results, output_file, scan_paths=input_paths)
    elif report_format == "html":
        HTMLReporter().generate_report(results, output_file, scan_paths=input_paths)
    else:
        TextReporter(advanced=advanced).generate_report(
            results, output_file, scan_paths=input_paths
        )


def _report_path(output_dir: Path, output_path: Optional[Path], report_format: str) -> Path:
    """The explicit ``--output`` path (parents created), or an auto-named file."""
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
    ext = _REPORT_EXTENSION.get(report_format, "txt")
    return output_dir / f"flac_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"


def _echo_to_real_stdout(output_file: Path) -> None:
    """Copy a machine-readable report onto the real stdout.

    Piping is the whole point of a machine-readable format; before this the
    report existed only as a file whose name the caller had to guess.
    """
    try:
        REAL_STDOUT.write(output_file.read_text(encoding="utf-8"))
        REAL_STDOUT.flush()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("could not echo the report to stdout: %s", exc)


def _write_diagnostic_report(output_dir: Path, stats: dict) -> Optional[Path]:
    """Write the reading-issues report when any file had one; return its path."""
    if stats["files_with_issues"] <= 0:
        return None
    path = output_dir / f"flac_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(get_tracker().generate_report())
    logger.warning(f"\n⚠️  {stats['files_with_issues']} file(s) had reading issues during analysis")
    logger.warning(f"   Diagnostic report saved to: {path.name}")
    return path


def _print_top_suspicious(suspicious: list[dict], advanced: bool) -> None:
    """Name the most suspicious files, ranked.

    So a library scan surfaces what to check first without opening the full
    report. Advanced shows the raw score; easy mode shows the plain verdict
    label instead.
    """
    top = rank_by_score(suspicious)
    print(f"\n  {colorize('Most suspicious (top of the list):', Colors.YELLOW)}")
    for r in top[:_TOP_N]:
        if advanced:
            lead = f"{r.get('score', 0):>4}  {r.get('verdict', ''):<12}"
        else:
            icon, label, _ = verdict_plain(r.get("verdict", ""))
            lead = f"{icon}  {label:<14}"
        print(f"    {lead}  {r.get('filename', '')}")
    if len(top) > _TOP_N:
        print(f"    … and {len(top) - _TOP_N} more (full ranking in the report)")


def generate_final_report(
    results: list[dict],
    output_dir: Path,
    all_flac_files: list[Path],
    all_non_flac_files: list[Path],
    log_file: Optional[Path],
    input_paths: list[Path],
    output_path: Optional[Path] = None,
    report_format: str = "text",
    advanced: bool = False,
):
    """Generate the final report and print summary.

    Args:
        results: List of analysis results.
        output_dir: Directory to save the report.
        all_flac_files: List of FLAC files analyzed.
        all_non_flac_files: List of non-FLAC files found.
        log_file: Path to the console log file.
        input_paths: List of user input paths (scan roots).
        output_path: Explicit output path; if None, auto-named in `output_dir`.
        report_format: "text", "json", "csv" or "html".
        advanced: Text report verbosity — easy (default) vs advanced (plumbing).
    """
    logger.info("\nGenerating report...")

    output_file = _report_path(output_dir, output_path, report_format)
    write_report(
        results,
        output_file,
        report_format,
        input_paths,
        all_flac_files,
        all_non_flac_files,
        advanced=advanced,
    )
    # …and onto the real stdout when that is where the caller is reading.
    if report_format != "text" and output_path is None:
        _echo_to_real_stdout(output_file)

    stats = get_tracker().get_statistics()
    diagnostic_report_path = _write_diagnostic_report(output_dir, stats)

    # Summary — count by the authoritative verdict (determine_verdict), not by
    # ad-hoc score cut points, so these stay consistent with the reports/API.
    suspicious_flac = [r for r in results if r.get("verdict") in SUMMARY_FLAGGED_VERDICTS]
    fake_certain = [r for r in results if r.get("verdict") == "FAKE_CERTAIN"]
    non_flac_count = len(all_non_flac_files)

    # Check if console log contains errors/warnings, delete if empty or no issues
    log_file_kept = cleanup_console_log_if_empty(log_file)

    print()
    print(colorize("=" * 70, Colors.CYAN))
    print(f"  {colorize('ANALYSIS COMPLETE', Colors.BRIGHT_GREEN)}")
    print(colorize("=" * 70, Colors.CYAN))
    print(f"  FLAC files analyzed: {len(all_flac_files)}")
    print(
        f"  {colorize('Fake/Suspicious FLAC files', Colors.RED)}: {len(suspicious_flac)} (including {len(fake_certain)} certain fakes)"
    )
    if non_flac_count > 0:
        print(f"  {colorize('Non-FLAC files (need replacement)', Colors.RED)}: {non_flac_count}")

    if suspicious_flac:
        _print_top_suspicious(suspicious_flac, advanced)

    if stats["files_with_issues"] > 0:
        print(
            f"  {colorize('⚠️  Files with reading issues', Colors.YELLOW)}: {stats['files_with_issues']} ({stats['critical_failures']} critical)"
        )

    print(f"  Report ({report_format}): {output_file.name}")
    if diagnostic_report_path:
        print(f"  {colorize('Diagnostic report', Colors.YELLOW)}: {diagnostic_report_path.name}")
    if log_file_kept and log_file is not None:
        print(f"  Console log: {log_file.name}")
    print(colorize("=" * 70, Colors.CYAN))
