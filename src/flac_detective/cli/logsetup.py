"""The console-log file and the logging handlers of a CLI run."""

import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import console as _console

logger = logging.getLogger(__name__)


class ResilientFileHandler(logging.FileHandler):
    """A FileHandler that disables itself on the first write/flush failure.

    The console log is written next to the scanned files. If that location turns
    out to be read-only or on a flaky external drive, a plain FileHandler raises
    (e.g. ``PermissionError`` on flush) for *every* record — and Python prints a
    full traceback each time, which on a large scan both floods the output and
    cripples throughput (the main thread blocks on logging once per file). Instead
    we no-op after the first failure and carry on console-only.

    We deliberately don't touch the logger's handler list from ``handleError``
    (lock-ordering risk while emitting); flipping a flag + closing the stream is
    enough to stop both the retries and the traceback flood.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._disabled = False

    def emit(self, record: logging.LogRecord) -> None:
        """Write the record unless a previous failure disabled this handler."""
        if self._disabled:
            return
        super().emit(record)

    def handleError(self, record: logging.LogRecord) -> None:
        """Disable the handler on the first failure instead of printing a traceback."""
        if not self._disabled:
            self._disabled = True
            try:
                self.close()
            except Exception:
                pass


def writable_log_file(preferred: Path) -> Optional[Path]:
    """Pick a writable console-log path: prefer the scan dir, fall back to temp.

    A music archive often lives on a read-only or external drive, so writing the
    log into the scanned tree can fail. We probe each candidate by actually
    writing **and flushing** (the failure mode is a flush error, not an open
    error), returning the first that works — or ``None`` if none is writable, in
    which case logging stays console-only.

    Args:
        preferred: First-choice directory (usually the scan directory).

    Returns:
        A writable log-file path, or None if no candidate location is writable.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"flac_console_log_{timestamp}.txt"
    for base in (preferred, Path(tempfile.gettempdir())):
        candidate = base / name
        try:
            with open(candidate, "w", encoding="utf-8") as probe:
                probe.write("flac-detective console log\n")
                probe.flush()
            return candidate
        except OSError:
            continue
    return None


def setup_logging(output_dir: Path) -> Optional[Path]:
    """Setup logging: Rich for console (if avail), File for persistence.

    The console-log file is placed in ``output_dir`` when writable, otherwise in
    the system temp dir; if neither is writable, logging stays console-only. This
    keeps a read-only / external scan drive from crippling a large scan with a
    per-record ``PermissionError``. See `writable_log_file` and
    `ResilientFileHandler`.

    Args:
        output_dir: Preferred directory for the log file (usually the scan dir).

    Returns:
        Path to the created log file, or None if file logging is unavailable.
    """
    log_file = writable_log_file(output_dir)

    # Root logger
    root_log = logging.getLogger()
    root_log.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    root_log.handlers = []

    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # File Handler (Always detailed) — only when a writable location was found.
    if log_file is not None:
        file_handler = ResilientFileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)
        root_log.addHandler(file_handler)

    # Console Handler
    if _console.HAS_RICH:
        from rich.logging import RichHandler

        # Rich Handler for beautiful output
        rich_handler = RichHandler(
            console=_console.console,
            show_time=True,
            omit_repeated_times=False,
            show_path=False,
            rich_tracebacks=True,
        )
        # Set to WARNING to reduce noise from retry/partial read messages
        # All details are still saved to the log file
        rich_handler.setLevel(logging.WARNING)
        root_log.addHandler(rich_handler)
    else:
        # Standard Console Handler (Legacy fallback)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(file_formatter)
        root_log.addHandler(console_handler)

    if log_file is None:
        warning = (
            "Could not create a console-log file (scan dir and temp dir both "
            "unwritable); continuing with console output only."
        )
        if _console.HAS_RICH and _console.console is not None:
            _console.console.print(f"[yellow]{warning}[/yellow]")
        else:
            logger.warning(warning)
    elif not _console.HAS_RICH:
        logger.info(f"Console log will be saved to: {log_file}")
    else:
        assert _console.console is not None
        _console.console.print(f"[dim]Log file: {log_file}[/dim]")

    return log_file


def cleanup_console_log_if_empty(log_file: Optional[Path]) -> bool:
    """Delete console log file if it's empty or contains no errors/warnings.

    Args:
        log_file: Path to the console log file, or None if file logging was
            unavailable (read-only scan dir + temp).

    Returns:
        True if log file was kept (has errors/warnings), False if deleted/absent.
    """
    if log_file is None:
        return False
    try:
        # Close all file handlers to allow file deletion on Windows
        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

        for handler in file_handlers:
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)

        if not log_file.exists():
            return False

        # Check if file is empty or contains only INFO messages
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # If empty, delete
        if not content:
            log_file.unlink()
            return False

        # Check if there are any ERROR or WARNING messages
        has_errors = "ERROR" in content or "WARNING" in content

        if not has_errors:
            # No errors or warnings, safe to delete
            log_file.unlink()
            return False

        # Keep the log file (has errors/warnings)
        return True

    except Exception as e:
        # If we can't check/delete, keep the file
        logger.warning(f"Could not cleanup log file: {e}")
        return True
