"""The CLI side of updating: ``--update``, and the offer at the end of a run.

Two entry points, both built so a test can drive them without a terminal or a
network: the question is asked through an injectable ``ask`` and the install
runs through an injectable ``upgrader``.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from ..colors import Colors, colorize
from ..update_check import current_version, fetch_latest_version, is_newer
from ..updater import UpgradeResult, manual_hint, upgrade

Ask = Callable[[str], str]
Upgrader = Callable[..., UpgradeResult]


def _say(text: str, color: Optional[str] = None) -> None:
    print(colorize(text, color) if color else text)


def run_update_command(
    fetch: Callable[[], Optional[str]] = fetch_latest_version,
    upgrader: Upgrader = upgrade,
    current: Optional[str] = None,
) -> int:
    """``flac-detective --update``: ask PyPI now (no cache), install if newer. Exit code."""
    current = current_version() if current is None else current
    _say(f"  FLAC Detective {current} — checking PyPI…")
    latest = fetch()
    if latest is None:
        _say("  PyPI could not be reached. Nothing was changed.", Colors.YELLOW)
        _say(f"  To update by hand: {manual_hint('pip')}")
        return 2
    if not is_newer(latest, current):
        _say(f"  You have the latest release ({current}).", Colors.GREEN)
        return 0
    _say(f"  {latest} is available. Installing…", Colors.YELLOW)
    result = upgrader(on_line=lambda line: print(f"    {line}"), target=latest)
    return _report(result)


def _report(result: UpgradeResult) -> int:
    """Print the result in its colour; the exit code (a deferred install is not a failure)."""
    if result.deferred:
        _say(f"  {result.message}", Colors.YELLOW)
        return 0
    _say(f"  {result.message}", Colors.GREEN if result.ok else Colors.RED)
    return 0 if result.ok else 1


def print_install_report(report: Optional[dict]) -> None:
    """What the deferred installer did last time, printed once at start."""
    if not report:
        return
    print()
    _say(f"  {report.get('message', '')}", Colors.GREEN if report.get("ok") else Colors.RED)
    print()


def offer_update(
    notice: Optional[str],
    interactive: Optional[bool] = None,
    ask: Ask = input,
    upgrader: Upgrader = upgrade,
    latest: Optional[str] = None,
) -> Optional[UpgradeResult]:
    """After the summary: print the notice and, on a terminal, offer to install.

    ``interactive`` defaults to "stdin and stdout are both terminals". When it
    is False the notice is printed with the command to run and nothing is
    asked: a cron job, a pipe or a GUI driving the CLI must never block on a
    question. Returns the upgrade result when an install was run.
    """
    if not notice:
        return None
    if interactive is None:
        try:
            interactive = sys.stdin.isatty() and sys.stdout.isatty()
        except Exception:  # noqa: BLE001 - a closed or replaced stream
            interactive = False
    print()
    _say(f"  {notice}", Colors.YELLOW)
    if not interactive:
        _say("  Run `flac-detective --update` to install it.")
        print()
        return None
    try:
        answer = ask("  Install it now? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    if answer not in ("y", "yes", "o", "oui"):
        _say("  Not now. Run `flac-detective --update` whenever you like.")
        print()
        return None
    result = upgrader(on_line=lambda line: print(f"    {line}"), target=latest)
    _report(result)
    print()
    return result
