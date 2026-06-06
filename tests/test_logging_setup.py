"""Tests for resilient logging setup (read-only / external scan dirs).

Regression: scanning a music archive on a read-only or external drive used to
write the console log into the scanned tree, where every record failed to flush
(PermissionError) — flooding tracebacks and crippling throughput on a large scan.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest

from flac_detective.main import (
    _ResilientFileHandler,
    _writable_log_file,
    setup_logging,
)


@pytest.fixture(autouse=True)
def _restore_root_logger():
    """Snapshot/restore the root logger so setup_logging() can't leak into other tests."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        yield
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)


def test_writable_log_file_uses_preferred_dir(tmp_path):
    p = _writable_log_file(tmp_path)
    assert p is not None
    assert p.parent == tmp_path
    assert p.exists()


def test_writable_log_file_falls_back_to_temp_when_preferred_unwritable(tmp_path):
    # A path whose parent dir does not exist → open() fails → fall back to temp.
    bogus = tmp_path / "no_such_subdir" / "deeper"
    p = _writable_log_file(bogus)
    assert p is not None
    # Fell back to the system temp dir, not the unwritable preferred dir.
    assert p.parent == Path(tempfile.gettempdir())
    p.unlink(missing_ok=True)


def test_setup_logging_returns_path_and_does_not_crash(tmp_path):
    log_file = setup_logging(tmp_path)
    assert log_file is not None
    assert log_file.parent == tmp_path


def test_setup_logging_falls_back_for_unwritable_scan_dir(tmp_path):
    # A scan dir that isn't writable → log lands in temp instead of crashing.
    log_file = setup_logging(tmp_path / "missing_subdir")
    assert log_file is not None
    assert log_file.parent == Path(tempfile.gettempdir())


def test_resilient_handler_disables_itself_on_write_error(tmp_path):
    handler = _ResilientFileHandler(tmp_path / "log.txt", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))

    class _BrokenStream:
        def write(self, *_):
            raise PermissionError("simulated read-only drive")

        def flush(self):
            raise PermissionError("simulated read-only drive")

        def close(self):
            pass

    handler.stream = _BrokenStream()
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)

    # First emit hits the broken stream → handleError disables the handler (no raise).
    handler.emit(record)
    assert handler._disabled is True

    # Subsequent emits are a no-op and must not raise.
    handler.emit(record)
