"""The two Windows bugs Provir reported against 1.13.0, pinned.

Both were found by a user running the shipped PyPI wheel on a stock Windows
console, and neither could be seen on Linux or on a GitHub runner, whose
consoles default to UTF-8. That is the whole lesson: the case that catches these
is the one nobody tests.

1. **FATAL.** `parse_arguments()` printed a banner containing box-drawing glyphs
   before parsing anything, and Python gives `sys.stdout` the console's ANSI
   codepage on Windows. On cp1252 those glyphs have no mapping, `print` raised
   `UnicodeEncodeError`, and **the tool did not start at all** — `--help`
   included.

2. **FUNCTIONAL.** `--format json` put the banner and the summary on stdout and
   wrote the report to a timestamped file, so `| jq .` could never work: stdout
   held decoration and no data.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flac_detective.main import _make_streams_utf8_safe, _print_banner
from flac_detective.utils import LOGO


class _Cp1252Stream(io.TextIOWrapper):
    """A stream that behaves like a stock Windows console: cp1252, strict."""

    def __init__(self) -> None:
        super().__init__(io.BytesIO(), encoding="cp1252", errors="strict")


def test_logo_is_unprintable_on_cp1252_which_is_why_the_fix_exists():
    """The precondition. If this ever stops holding, the guard can go."""
    with pytest.raises(UnicodeEncodeError):
        LOGO.encode("cp1252")


def test_streams_are_made_utf8_safe(monkeypatch):
    """After the guard, a cp1252 stream must swallow the banner rather than raise."""
    stream = _Cp1252Stream()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", stream)
    _make_streams_utf8_safe()
    # Whatever the host did with reconfigure(), printing the banner must not raise.
    print(LOGO)


def test_banner_goes_to_stderr_when_the_output_is_machine_readable(capsys):
    """stdout carries data in that mode, so decoration belongs on stderr."""
    _print_banner(machine_readable=True)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip()

    _print_banner(machine_readable=False)
    captured = capsys.readouterr()
    assert captured.out.strip()


@pytest.mark.skipif(
    not Path("C:/Users/loutr/audit_corpus/authentic").exists(),
    reason="needs the local audit corpus",
)
def test_json_format_puts_parseable_json_on_stdout(tmp_path):
    """End to end, on a cp1252 console: `--format json` must be pipeable.

    The regression this pins is not cosmetic — before the fix the report existed
    only as a file whose name the caller had to guess, and stdout held a banner.
    """
    sample = next(Path("C:/Users/loutr/audit_corpus/authentic").glob("*.flac"))
    env = {
        **dict(__import__("os").environ),
        "PYTHONIOENCODING": "cp1252",
        "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src"),
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from flac_detective.main import main; main()",
            "--format",
            "json",
            str(sample),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )
    payload = json.loads(proc.stdout)
    assert set(payload) >= {"scan_info", "results"}
    assert len(payload["results"]) == 1
