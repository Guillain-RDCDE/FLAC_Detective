"""Several folders, one right click: one window, one scan.

Explorer runs a plain menu command once per selected item. Four folders
selected, "Scan with FLAC Detective" clicked: four copies of the GUI start at
the same moment, each on one folder, and open on top of one another at the
same place — so it looks as if only one folder was taken.

The copies started by the same click find each other here. The first one to
take a lock becomes the *gatherer*: it opens a local socket and its window.
The others hand their folders to it and leave without opening anything. The
gatherer waits until the arrivals have been quiet for a moment, then scans
everything in one window and stops gathering, so a right click made later
opens its own window, as before.

Nothing is lost if the hand-over fails: a copy that gets no acknowledgement
opens its own window on its own folder, which is what happened before.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QDir, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket

# How long the gatherer waits after the last arrival before it scans.
SETTLE_MS = 1200
# A copy keeps trying to reach the gatherer for this long before opening its own window.
_FIND_S = 20.0
_CONNECT_MS = 300
# The gatherer only reads its socket once its window is built, which takes
# several seconds on a first launch (matplotlib, the analysis stack).
_ACK_MS = 60_000
_ACK = b"ok\n"


def _name() -> str:
    # Per user: a Windows pipe name is visible to every session on the machine.
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    return "flac-detective-gather-" + "".join(c for c in user if c.isalnum())


def _encode(paths: list[Path]) -> bytes:
    return json.dumps([str(p) for p in paths]).encode("utf-8") + b"\n"


def _hand_over(paths: list[Path], name: str) -> bool:
    """Give the paths to a running gatherer; True once it has acknowledged them."""
    sock = QLocalSocket()
    sock.connectToServer(name)
    if not sock.waitForConnected(_CONNECT_MS):
        return False
    sock.write(_encode(paths))
    sock.flush()
    reply = b""
    deadline = time.monotonic() + _ACK_MS / 1000
    while not reply.endswith(b"\n") and time.monotonic() < deadline:
        if (
            not sock.waitForReadyRead(500)
            and sock.state() != QLocalSocket.LocalSocketState.ConnectedState
        ):
            break
        reply += bytes(sock.readAll().data())
    sock.disconnectFromServer()
    return reply == _ACK


class Gatherer:
    """Collects the folders of every copy started by the same right click."""

    def __init__(self, paths: list[Path], lock: QLockFile, server: QLocalServer) -> None:
        self.paths: list[Path] = []
        self.on_arrival: Callable[[], None] | None = None
        self._lock = lock
        self._server = server
        self._buffers: dict[QLocalSocket, bytes] = {}
        self._stopped = False
        self._add(paths)
        server.newConnection.connect(self._accept)

    def _add(self, paths: list[Path]) -> None:
        seen = {str(p).lower() for p in self.paths}
        for p in paths:
            if str(p).lower() not in seen:
                seen.add(str(p).lower())
                self.paths.append(p)

    def _accept(self) -> None:
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            self._buffers[sock] = b""
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(lambda s=sock: self._forget(s))
            self._read(sock)  # data may already be waiting

    def _read(self, sock: QLocalSocket) -> None:
        if sock not in self._buffers:
            return
        if self._stopped:
            # Too late for this scan: no acknowledgement, so the sender opens its own window.
            sock.disconnectFromServer()
            return
        self._buffers[sock] += bytes(sock.readAll().data())
        data = self._buffers[sock]
        if not data.endswith(b"\n"):
            return
        del self._buffers[sock]
        try:
            paths = [Path(p) for p in json.loads(data.decode("utf-8"))]
        except ValueError:
            sock.disconnectFromServer()
            return
        self._add(paths)
        sock.write(_ACK)
        sock.flush()
        if self.on_arrival is not None:
            self.on_arrival()

    def _forget(self, sock: QLocalSocket) -> None:
        self._buffers.pop(sock, None)
        sock.deleteLater()

    def stop(self) -> None:
        """Stop gathering: a later right click opens its own window."""
        self._stopped = True
        self._server.close()
        for sock in list(self._buffers):
            sock.disconnectFromServer()
        self._lock.unlock()


def gather(paths: list[Path]) -> Gatherer | None:
    """Join the copies started by the same right click.

    Returns ``None`` when the paths were handed to another copy (this one has
    nothing left to do), otherwise the :class:`Gatherer` this copy now runs.
    """
    name = _name()
    lock = QLockFile(str(Path(QDir.tempPath()) / f"{name}.lock"))
    lock.setStaleLockTime(0)  # stale only if its owner is dead
    deadline = time.monotonic() + _FIND_S
    while True:
        if _hand_over(paths, name):
            return None
        if lock.tryLock(0):
            server = QLocalServer()
            QLocalServer.removeServer(name)  # a leftover of a copy that crashed
            if server.listen(name):
                return Gatherer(paths, lock, server)
            lock.unlock()
            break
        if time.monotonic() > deadline:
            break
        time.sleep(0.1)
    # Neither joined nor gathering: scan these folders alone, as before.
    return Gatherer(paths, QLockFile(""), QLocalServer())
