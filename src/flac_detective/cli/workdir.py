"""Where progress.json, the auto-named report and the console log go."""

import sys
import tempfile
from pathlib import Path
from typing import Optional

from ..colors import Colors, colorize


def is_writable_dir(path: Path) -> bool:
    """Return True if we can actually create and write a file in ``path``.

    ``os.access(W_OK)`` lies on read-only mounts, network shares and Windows
    ACLs, so we probe by really writing a scratch file and flushing it — the same
    approach as `logsetup.writable_log_file` — and remove it afterwards.
    """
    try:
        if not path.is_dir():
            return False
        with tempfile.NamedTemporaryFile(
            dir=path, prefix=".flac-detective-probe-", suffix=".tmp", delete=True
        ) as probe:
            probe.write(b"probe")
            probe.flush()
        return True
    except OSError:
        return False


def resolve_work_dir(paths: list[Path], work_dir: Optional[Path] = None) -> tuple[Path, list[str]]:
    """Decide where ``progress.json``, the report and the console log go.

    * ``--work-dir`` given → that directory (created if needed). It must be
      writable, otherwise we fail early with a clear message rather than after a
      full scan.
    * Otherwise, the scan directory (first path, or its parent for a file) — the
      historical default, chosen so that re-running ``flac-detective /same/dir``
      from anywhere resumes an interrupted scan.
    * If the scan directory is read-only (external drive, container ``:ro``
      mount, immutable archive), fall back to the current working directory —
      which is what the old comment always promised. Resume then works as long
      as you re-run from the same working directory.
    * If even the CWD is read-only, fall back to the system temp directory so
      the scan can still complete and produce a report.

    Args:
        paths: The user's scan roots (non-empty).
        work_dir: Explicit ``--work-dir`` value, or None.

    Returns:
        ``(directory, notes)`` — a writable directory, and warnings to show the
        user when a fallback was taken (empty when the default or an explicit
        ``--work-dir`` was used). Returned rather than logged because this runs
        before logging is configured (logging needs the directory).

    Raises:
        SystemExit: when an explicit ``--work-dir`` cannot be created or written.
    """
    if work_dir is not None:
        try:
            work_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(
                colorize(f"--work-dir {work_dir}: cannot create directory ({e})", Colors.RED),
                file=sys.stderr,
            )
            sys.exit(2)
        if not is_writable_dir(work_dir):
            print(
                colorize(f"--work-dir {work_dir}: directory is not writable", Colors.RED),
                file=sys.stderr,
            )
            sys.exit(2)
        return work_dir, []

    scan_dir = paths[0] if paths[0].is_dir() else paths[0].parent
    if is_writable_dir(scan_dir):
        return scan_dir, []

    cwd = Path.cwd()
    if is_writable_dir(cwd):
        return cwd, [
            f"Scan directory is read-only ({scan_dir}); progress, report and log "
            f"will be written to the current directory instead: {cwd}",
            "Re-run from this same directory to resume an interrupted scan "
            "(or pass --work-dir DIR to choose the location).",
        ]

    tmp = Path(tempfile.gettempdir())
    return tmp, [
        f"Neither the scan directory ({scan_dir}) nor the current directory ({cwd}) "
        f"is writable; falling back to the system temp directory: {tmp}",
        "Use --work-dir DIR to choose where progress and reports are written.",
    ]
