"""Is there a newer FLAC Detective on PyPI?

A user who reports a bug against a version eight releases old is not at fault:
nothing told them. Until 2.3.0 nothing did — the tool never looked. This module
asks PyPI once a day, in a background thread, and never gets in the way:

* one small GET on ``https://pypi.org/pypi/flac-detective/json`` (what ``pip``
  itself reads), two-second timeout, result cached for 24 hours in the user's
  cache directory, so a library scan does not open a connection on every run;
* nothing but the request itself leaves the machine (no file name, no verdict,
  no identifier beyond the ``User-Agent`` naming this tool and its version);
* **any** failure — no network, a proxy, a malformed answer, a cache directory
  that cannot be written — is a silent "no notice", never an error and never a
  delay of more than the join timeout the caller chooses;
* off with ``--no-update-check`` or ``FLAC_DETECTIVE_NO_UPDATE_CHECK=1`` (the
  Docker image sets the variable: ``pip install -U`` is the wrong advice there).

Only final releases are compared (``X.Y.Z``); a pre-release or development
version on either side disables the comparison rather than guess.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional, Tuple

from .__version__ import __version__

logger = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/flac-detective/json"
OPT_OUT_ENV = "FLAC_DETECTIVE_NO_UPDATE_CHECK"
CACHE_TTL_SECONDS = 24 * 3600
FETCH_TIMEOUT_SECONDS = 2.0
_CACHE_FILE_NAME = "update-check.json"


def current_version() -> str:
    """The version of the INSTALLED distribution, which is what pip upgrades.

    In an ordinary install it equals ``__version__``. They differ only when the
    code running is not the code installed (a checkout on ``PYTHONPATH`` over an
    installed package): the installer must then decide and verify against the
    distribution, or it would say "up to date" about a package it never looked
    at — which is exactly what the first end-to-end test of 2.4.0 did.
    """
    try:
        from importlib.metadata import version

        return version("flac-detective")
    except Exception:  # noqa: BLE001 - not installed as a distribution (a bare checkout)
        return __version__


def parse_version(text: str) -> Optional[Tuple[int, ...]]:
    """``"2.2.0"`` → ``(2, 2, 0)``; anything that is not plain digits and dots → None."""
    parts = text.strip().split(".")
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def is_newer(latest: str, current: str) -> bool:
    """True when ``latest`` is a final release strictly after ``current``."""
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    return a > b


def cache_path() -> Path:
    """The cache file: ``%LOCALAPPDATA%`` on Windows, ``$XDG_CACHE_HOME`` or ``~/.cache`` elsewhere."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "flac-detective" / _CACHE_FILE_NAME


def fetch_latest_version(timeout: float = FETCH_TIMEOUT_SECONDS) -> Optional[str]:
    """Ask PyPI for the latest release; None on any failure."""
    request = urllib.request.Request(
        PYPI_URL,
        headers={"User-Agent": f"flac-detective/{__version__}", "Accept": "application/json"},
    )
    try:
        # nosec B310: the URL is the https constant above, never user input.
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))
        version = payload["info"]["version"]
        return str(version) if isinstance(version, str) else None
    except Exception as exc:  # noqa: BLE001 - a failed check is not an event
        logger.debug("update check: PyPI not reachable (%s)", exc)
        return None


def _read_cache(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _write_cache(path: Path, latest: str, now: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"latest": latest, "checked_at": now}), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - an unwritable cache is not an event
        logger.debug("update check: cache not written (%s)", exc)


def latest_version(
    *,
    now: Optional[float] = None,
    fetch: Callable[[], Optional[str]] = fetch_latest_version,
    cache_file: Optional[Path] = None,
    environ: Optional[dict] = None,
) -> Optional[str]:
    """The latest release on PyPI, from the day's cache or a fresh request.

    None when the check is switched off, when PyPI could not be reached and no
    cache exists, or when the answer is not a version. Never raises.
    """
    env = os.environ if environ is None else environ
    if env.get(OPT_OUT_ENV, "").strip() not in ("", "0", "false", "no"):
        return None
    try:
        now = time.time() if now is None else now
        path = cache_path() if cache_file is None else cache_file
        cached = _read_cache(path)
        if cached is not None:
            checked_at = cached.get("checked_at")
            latest = cached.get("latest")
            if (
                isinstance(checked_at, (int, float))
                and isinstance(latest, str)
                and 0 <= now - checked_at < CACHE_TTL_SECONDS
            ):
                return latest
        latest = fetch()
        if latest is None or parse_version(latest) is None:
            return None
        _write_cache(path, latest, now)
        return latest
    except Exception as exc:  # noqa: BLE001 - the check must never become the problem
        logger.debug("update check failed: %s", exc)
        return None


def update_notice(latest: Optional[str], current: Optional[str] = None) -> Optional[str]:
    """The one-line notice to print, or None when there is nothing newer."""
    current = current_version() if current is None else current
    if latest is None or not is_newer(latest, current):
        return None
    return (
        f"A newer FLAC Detective is available: {latest} (you have {current}). "
        f"Upgrade with: pip install -U flac-detective"
    )


class UpdateCheck:
    """Run the check on a daemon thread; ask for the notice when convenient.

    ``start()`` returns at once. ``notice(wait)`` waits at most ``wait`` seconds
    for the thread and returns the notice or None — a check that has not
    finished by then is simply dropped (its result lands in the cache for the
    next run).
    """

    def __init__(self, enabled: bool = True, current: Optional[str] = None) -> None:
        self._enabled = enabled
        self._current = current_version() if current is None else current
        self._latest: Optional[str] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "UpdateCheck":
        """Launch the check in the background (a no-op when disabled)."""
        if not self._enabled or self._thread is not None:
            return self
        self._thread = threading.Thread(target=self._run, name="flac-detective-update-check")
        self._thread.daemon = True
        self._thread.start()
        return self

    def _run(self) -> None:
        self._latest = latest_version()

    def notice(self, wait: float = 1.0) -> Optional[str]:
        """The notice, if the check finished within ``wait`` seconds and found a newer release."""
        if self._thread is None:
            return None
        self._thread.join(timeout=max(0.0, wait))
        if self._thread.is_alive():
            return None
        return update_notice(self._latest, self._current)
