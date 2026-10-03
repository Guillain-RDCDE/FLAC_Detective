"""Console rendering for the CLI: Rich when installed, the banner, the per-file line."""

import logging
import os
import sys
from typing import Optional

from ..utils import LOGO

logger = logging.getLogger(__name__)

# RICH INTEGRATION — optional; everything degrades to plain logging without it.
try:
    from rich.console import Console
    from rich.theme import Theme

    # Custom theme for FLAC Detective
    custom_theme = Theme(
        {
            "info": "dim cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "fake": "bold red",
            "suspicious": "bold yellow",
            "authentic": "bold green",
        }
    )

    console: Optional[Console] = Console(theme=custom_theme)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


# Authoritative verdict -> (icon, Rich style, label). Single source of truth for the
# thresholds is new_scoring/constants.py via determine_verdict(); the console only
# renders the label it produced — it must NOT recompute its own from the score.
VERDICT_DISPLAY = {
    "FAKE_CERTAIN": ("❌", "fake", "FAKE"),
    "SUSPICIOUS": ("⚠️ ", "suspicious", "SUSPICIOUS"),
    "WARNING": ("❓", "warning", "WARNING"),
    "AUTHENTIC": ("✅", "authentic", "AUTHENTIC"),
    "NON_FLAC": ("🚫", "fake", "NON_FLAC"),
    "NOT_ASSESSED": ("🔍", "warning", "NOT ASSESSED"),
    "ERROR": ("⁉️ ", "warning", "ERROR"),
}


def enable_utf8_console() -> None:
    """Switch a Windows console to the UTF-8 code page (the standard approach)."""
    if sys.platform == "win32":
        os.system("chcp 65001 > nul 2>&1")


def make_streams_utf8_safe() -> None:
    """Stop a Windows console codepage from killing the process before it starts.

    Reported by Provir 2026-08-31 against 1.13.0 from PyPI, Windows 11, stock
    cmd/PowerShell: `flac-detective --version` dies with UnicodeEncodeError
    before a single argument is parsed, because `parse_arguments()` prints a
    banner containing box-drawing glyphs and Python gives `sys.stdout` the
    console's ANSI codepage (cp1252), where those glyphs have no mapping.

    **The tool did not start at all on a default Windows terminal.** No
    invocation worked, `--help` included, and no CI job caught it because the
    GitHub runners default to UTF-8 — the case that catches it is a stock user
    console, which is the one case nobody tests.

    `errors="replace"` rather than a fallback banner: a console that cannot draw
    a box should print a question mark and keep going, never raise. Wrapped in
    its own try/except because a stream that cannot be reconfigured (a pipe on
    an old Python, a captured stream under pytest) is not a reason to fail
    either.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # pragma: no cover - depends on the host console
            pass


def print_banner(machine_readable: bool = False) -> None:
    """The logo, on stderr when stdout is carrying machine-readable output."""
    print(LOGO, file=sys.stderr if machine_readable else sys.stdout)


def log_formatted_result(result: dict, processed: int, total: int, advanced: bool = False):
    """Log one analysis result, styled by its authoritative verdict.

    Args:
        result: Analysis result dict. Its ``verdict`` (from determine_verdict) is
            the source of truth — the console renders that label, never its own.
        processed: Number of files processed.
        total: Total number of files.
        advanced: If True, show the numeric score (plumbing). Default 'easy' mode
            shows a plain verdict label only.
    """
    score = result.get("score", 0)
    verdict = result.get("verdict", "UNKNOWN")
    filename = result["filename"]
    icon, style, label = VERDICT_DISPLAY.get(verdict, ("•", "info", verdict))

    # Truncate filename gracefully
    if len(filename) > 50:
        filename = filename[:47] + "..."

    # Easy mode hides the 0-150 score; advanced shows it.
    score_field = f" {score:>3}/100" if advanced else ""
    if HAS_RICH:
        # We rely on RichHandler for the timestamp and base formatting
        # Here we just construct the nice message content
        msg = f"[{style}]{icon} {label:<12}{score_field}[/]  {filename}"
        logger.info(msg, extra={"markup": True})
    else:
        # Fallback for standard logging
        msg = f"[{processed:03d}/{total:03d}] {icon} {label:<12}{score_field}  {filename}"
        logger.info(msg)
