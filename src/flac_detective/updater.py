"""Install the newer release that ``update_check`` found, from inside the tool.

2.3.0 told the user a newer version existed. 2.4.0 installs it on request, in
the CLI (``flac-detective --update``, or "Install now?" at the end of a run on
a terminal), in the GUI (an "Update" button in the header) and in the beets
plugin (``beet flacdetective --update``). The same code does it everywhere.

What it does, and what it refuses to guess:

* it works out **how this copy was installed** — ``pip`` into the running
  interpreter (a venv, a user site, a system Python), ``pipx``, a source
  checkout, or the Docker image — and runs the matching upgrade command
  (``python -m pip install --upgrade flac-detective`` with the SAME interpreter
  that is running, or ``pipx upgrade flac-detective``). A source checkout and
  the Docker image are not upgraded by this tool; they are told how;
* it never upgrades anything **without being asked**: the daily check only
  reports, the install is a user action every time;
* it streams the installer's output to the caller, waits at most 15 minutes,
  and ends with a **verification**: the version a fresh interpreter reports
  after the install, not the exit code's word for it;
* any failure is returned, with the output and the command to run by hand,
  never raised. The scan that may have just finished is not affected.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from .update_check import OPT_OUT_ENV, current_version, is_newer

PACKAGE = "flac-detective"

METHOD_PIP = "pip"
METHOD_PIPX = "pipx"
METHOD_SOURCE = "source"
METHOD_DOCKER = "docker"

UPGRADE_TIMEOUT_SECONDS = 15 * 60


@dataclass
class UpgradeResult:
    """What happened: ``ok`` only when a fresh interpreter reports the new version."""

    ok: bool
    method: str
    command: List[str]
    output: str = ""
    installed_version: Optional[str] = None
    message: str = ""
    lines: List[str] = field(default_factory=list)
    # Windows: the install was handed to a detached process that runs once
    # this program has exited (see start_deferred_install); nothing is
    # installed yet and ``ok`` is False.
    deferred: bool = False


def install_method(
    executable: Optional[str] = None,
    package_file: Optional[str] = None,
    environ: Optional[dict] = None,
) -> str:
    """How this copy of FLAC Detective was installed.

    ``docker`` when running in the image (the image sets the opt-out variable,
    and ``/.dockerenv`` exists); ``source`` when the package is imported from a
    checkout (``…/src/flac_detective`` next to a ``pyproject.toml``); ``pipx``
    when the interpreter lives in a pipx venv; ``pip`` otherwise.
    """
    env = os.environ if environ is None else environ
    exe = Path(executable or sys.executable)
    if env.get("FLAC_DETECTIVE_IN_DOCKER") or Path("/.dockerenv").exists():
        return METHOD_DOCKER
    if package_file is None:
        from . import __file__ as _pkg_init

        package_file = _pkg_init
    pkg_dir = Path(package_file).resolve().parent
    if pkg_dir.parent.name == "src" and (pkg_dir.parent.parent / "pyproject.toml").exists():
        return METHOD_SOURCE
    parts = [p.lower() for p in exe.parts]
    if "pipx" in parts or env.get("PIPX_HOME") and str(exe).startswith(env["PIPX_HOME"]):
        return METHOD_PIPX
    return METHOD_PIP


def upgrade_command(method: str, executable: Optional[str] = None) -> Optional[List[str]]:
    """The command that upgrades this install, or None when this tool must not run one."""
    exe = executable or sys.executable
    if method == METHOD_PIP:
        return [exe, "-m", "pip", "install", "--upgrade", "--no-input", PACKAGE]
    if method == METHOD_PIPX:
        return ["pipx", "upgrade", PACKAGE]
    return None


def manual_hint(method: str) -> str:
    """The one line to run by hand, for the method found."""
    if method == METHOD_PIPX:
        return f"pipx upgrade {PACKAGE}"
    if method == METHOD_SOURCE:
        return "git pull in your checkout (this is a source install; nothing to download)"
    if method == METHOD_DOCKER:
        return "docker pull ghcr.io/guillain-rdcde/flac_detective:latest"
    return f"{Path(sys.executable).name} -m pip install -U {PACKAGE}"


_READ_INSTALLED = "from importlib.metadata import version; print(version('flac-detective'))"


def installed_version(executable: Optional[str] = None, timeout: float = 60.0) -> Optional[str]:
    """The distribution version a FRESH interpreter reports, or None if it cannot say.

    The distribution's metadata, not an import of the package: an import would
    find whatever is first on ``sys.path``, the metadata is what pip wrote.
    """
    exe = executable or sys.executable
    try:
        out = subprocess.run(  # nosec B603 - our own interpreter, a fixed snippet
            [exe, "-c", _READ_INSTALLED],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        text = (out.stdout or "").strip().splitlines()
        return text[-1].strip() if out.returncode == 0 and text else None
    except Exception:  # noqa: BLE001 - a failed verification is a None, never a crash
        return None


def run_command(
    command: List[str],
    on_line: Optional[Callable[[str], None]] = None,
    timeout: float = UPGRADE_TIMEOUT_SECONDS,
) -> tuple:
    """Run ``command``, streaming each output line to ``on_line``; (returncode, output)."""
    lines: List[str] = []
    try:
        proc = subprocess.Popen(  # nosec B603 - the command is built here, not from input
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PYTHONUTF8": "1"},
        )
    except Exception as exc:  # noqa: BLE001 - e.g. pipx not on PATH
        return -1, f"could not start {command[0]}: {exc}"
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            lines.append(line)
            if on_line is not None:
                try:
                    on_line(line)
                except Exception:  # noqa: BLE001 - a listener must not stop the install
                    pass
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        lines.append(f"(stopped after {int(timeout)} s)")
        code = -2
    return code, "\n".join(lines)


# --------------------------------------------------------------------------
# Windows: a running program cannot be replaced
#
# The console-script launcher (flac-detective.exe, flac-detective-gui.exe) is
# the running process image, and pip's uninstall step has to delete it:
# "WinError 32, the file is in use". Worse, pip had already removed the old
# distribution when it failed, and left no package at all (seen on the first
# end-to-end test of 2.4.0). So on Windows the install is handed to a
# detached interpreter that waits for this process AND its launcher to exit,
# runs pip, verifies, and leaves a report the next launch prints.
# --------------------------------------------------------------------------


def needs_deferred_install(platform: str = sys.platform) -> bool:
    """True where a running program's files cannot be replaced (Windows)."""
    return platform == "win32"


def install_report_path() -> Path:
    """Where the deferred installer leaves its result (beside the update-check cache)."""
    from .update_check import cache_path

    return cache_path().parent / "update-install.json"


def _parent_launcher_pid() -> Optional[int]:
    """The pid of the console-script launcher that started this process, if that is what did.

    Windows only. The launcher is an .exe in the interpreter's own Scripts
    directory (not python.exe itself); a shell or an IDE as parent is not one,
    and must never be waited for.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        ppid = os.getppid()
        kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009 - absent off Windows
        handle = kernel32.OpenProcess(0x1000, False, ppid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return None
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            size = wintypes.DWORD(32768)
            if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return None
            image = Path(buffer.value)
        finally:
            kernel32.CloseHandle(handle)
        scripts = Path(sys.executable).resolve().parent
        if (
            image.resolve().parent == scripts
            and image.suffix.lower() == ".exe"
            and not image.stem.lower().startswith("python")
        ):
            return ppid
    except Exception:  # noqa: BLE001 - no launcher found is the safe answer
        return None
    return None


def wait_for_exit(pids: List[int], timeout: float = 600.0) -> bool:
    """Block until every pid has exited (or ``timeout`` passes); True if they all did."""
    import time

    deadline = time.monotonic() + timeout
    for pid in pids:
        if pid <= 0 or pid == os.getpid():
            continue
        if sys.platform == "win32":
            import ctypes

            kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009 - absent off Windows
            handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
            if not handle:
                continue  # already gone
            try:
                remaining = max(0.0, deadline - time.monotonic())
                rc = kernel32.WaitForSingleObject(handle, int(remaining * 1000))
                if rc != 0:  # WAIT_OBJECT_0
                    return False
            finally:
                kernel32.CloseHandle(handle)
        else:
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
                time.sleep(0.25)
            else:
                return False
    return True


def start_deferred_install(
    command: List[str], executable: Optional[str] = None, current: Optional[str] = None
) -> Path:
    """Spawn the detached installer; return the report path it will write.

    The child waits for this process and, when there is one, the console
    launcher that started it, then runs ``command`` and verifies. Its own
    output goes to ``update-install.log`` beside the report.
    """
    exe = executable or sys.executable
    current = current_version() if current is None else current
    pids = [os.getpid()]
    launcher = _parent_launcher_pid()
    if launcher:
        pids.append(launcher)
    report = install_report_path()
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    log = report.with_suffix(".log")
    args = [
        exe,
        "-m",
        "flac_detective.updater",
        "--deferred",
        ",".join(str(p) for p in pids),
        "--report",
        str(report),
        "--current",
        current,
        "--",
        *command,
    ]
    flags = 0
    if sys.platform == "win32":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    with open(log, "w", encoding="utf-8") as log_file:
        subprocess.Popen(  # nosec B603 - our own interpreter and module
            args,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
            cwd=str(Path.home()),
        )
    return report


def deferred_main(
    argv: List[str],
    waiter: Callable[..., bool] = wait_for_exit,
    runner: Callable[..., tuple] = run_command,
    verify: Callable[..., Optional[str]] = installed_version,
) -> int:
    """Entry point of the detached installer (``python -m flac_detective.updater``)."""
    import json
    import time

    pids: List[int] = []
    report = install_report_path()
    current = current_version()
    command: List[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--deferred":
            pids = [int(p) for p in argv[i + 1].split(",") if p.strip()]
            i += 2
        elif argv[i] == "--report":
            report = Path(argv[i + 1])
            i += 2
        elif argv[i] == "--current":
            current = argv[i + 1]
            i += 2
        elif argv[i] == "--":
            command = argv[i + 1 :]
            break
        else:
            i += 1
    if not command:
        print("deferred installer: no command", flush=True)
        return 2
    waited = waiter(pids)
    time.sleep(1.0)  # let the launcher release its file handles
    code, output = runner(command, on_line=lambda line: print(line, flush=True))
    now = verify(command[0]) if code == 0 else None
    ok = now is not None and is_newer(now, current)
    if ok:
        message = f"Update installed: FLAC Detective {now} (was {current})."
    elif code != 0:
        message = (
            f"The update did not install (installer exit code {code}). "
            f"To update by hand: {' '.join(command)}"
        )
    else:
        message = (
            f"The installer finished but the version reads {now!r} (was {current}); "
            f"check with: {Path(command[0]).name} -m flac_detective.main --version"
        )
    payload = {
        "ok": ok,
        "installed_version": now,
        "previous_version": current,
        "message": message,
        "waited_for_exit": waited,
        "exit_code": code,
        "output_tail": output[-2000:],
        "finished_at": time.time(),
    }
    try:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"deferred installer: report not written ({exc})", flush=True)
    print(message, flush=True)
    return 0 if ok else 1


def consume_install_report() -> Optional[dict]:
    """The deferred installer's report, read once and removed; None when there is none."""
    import json

    path = install_report_path()
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        path.unlink(missing_ok=True)
        return data if isinstance(data, dict) and "message" in data else None
    except Exception:  # noqa: BLE001 - a bad report is dropped, never shown as a crash
        try:
            path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
        return None


def upgrade(
    on_line: Optional[Callable[[str], None]] = None,
    executable: Optional[str] = None,
    method: Optional[str] = None,
    runner: Callable[..., tuple] = run_command,
    verify: Callable[..., Optional[str]] = installed_version,
    current: Optional[str] = None,
    deferred: Optional[bool] = None,
    starter: Callable[..., Path] = start_deferred_install,
) -> UpgradeResult:
    """Upgrade this install and verify it. Never raises.

    ``ok`` means a fresh interpreter now reports a distribution version newer
    than ``current`` (the installed distribution's version by default). The
    running process still has the old code loaded: the caller tells the user
    to relaunch. On Windows (``deferred``) the install is handed to a detached
    process that runs after exit, and the result carries ``deferred=True``.
    """
    current = current_version() if current is None else current
    method = method or install_method(executable=executable)
    command = upgrade_command(method, executable=executable)
    if command is None:
        return UpgradeResult(
            ok=False,
            method=method,
            command=[],
            message=f"This copy is not upgraded from inside the tool. To update: {manual_hint(method)}",
        )
    deferred = needs_deferred_install() if deferred is None else deferred
    if deferred and method == METHOD_PIP:
        try:
            report = starter(command, executable, current)
        except Exception as exc:  # noqa: BLE001 - could not even start it
            return UpgradeResult(
                ok=False,
                method=method,
                command=command,
                message=(
                    f"The background installer could not be started ({exc}). "
                    f"To update by hand, close FLAC Detective and run: {' '.join(command)}"
                ),
            )
        return UpgradeResult(
            ok=False,
            method=method,
            command=command,
            deferred=True,
            message=(
                "The update will be installed as soon as FLAC Detective exits "
                "(Windows cannot replace a program while it runs). The result is shown "
                f"the next time you start it; log: {report.with_suffix('.log')}"
            ),
        )
    code, output = runner(command, on_line)
    if code != 0:
        return UpgradeResult(
            ok=False,
            method=method,
            command=command,
            output=output,
            message=(
                f"The installer exited with code {code}. " f"To update by hand: {' '.join(command)}"
            ),
        )
    now = verify(executable)
    if now is None:
        return UpgradeResult(
            ok=False,
            method=method,
            command=command,
            output=output,
            message=(
                "The installer finished but the new version could not be read back. "
                f"Check with: {Path(executable or sys.executable).name} -m flac_detective.main --version"
            ),
        )
    if not is_newer(now, current) and now != current:
        pass  # a sideways move (pre-release?) is still reported as what it is
    ok = is_newer(now, current)
    message = (
        f"FLAC Detective {now} is installed. Restart it to use the new version "
        f"(this run is still {current})."
        if ok
        else f"Nothing newer was installed: the version reported is {now} (this run is {current})."
    )
    return UpgradeResult(
        ok=ok, method=method, command=command, output=output, installed_version=now, message=message
    )


def opt_out(environ: Optional[dict] = None) -> bool:
    """True when the user switched the update machinery off."""
    env = os.environ if environ is None else environ
    return env.get(OPT_OUT_ENV, "").strip() not in ("", "0", "false", "no")


if __name__ == "__main__":  # pragma: no cover - the detached installer's entry point
    sys.exit(deferred_main(sys.argv[1:]))
