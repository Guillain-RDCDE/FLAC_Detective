"""Background analysis worker for the GUI.

Runs the CLI's own batch runner (``flac_detective.cli.pool.analyze_batch``) on a
Qt ``QThread`` so the UI stays responsive, emitting a signal per completed file
plus progress and lifecycle signals. Supports cooperative cancellation.

Until v2.0 this class carried its own copy of the process pool, without the
CLI's fallback when the pool dies (every remaining file was lost on a
BrokenProcessPool) and without the reading issues the diagnostic report is
built from. It now takes both from the one implementation.
"""

from __future__ import annotations

import logging
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

from ..analysis import FLACAnalyzer
from ..analysis.diagnostic_tracker import get_tracker
from ..cli.pool import analyze_batch
from ..config import analysis_config

logger = logging.getLogger(__name__)


class UpdateCheckWorker(QThread):
    """Ask PyPI for a newer release off the UI thread (``update_check.py``).

    Emits ``notice(str)`` only when there is something newer; stays silent on
    every failure, like the CLI. Honours ``FLAC_DETECTIVE_NO_UPDATE_CHECK``.
    """

    notice = Signal(str)

    def run(self) -> None:  # noqa: D102 - QThread entry point
        from ..update_check import latest_version, update_notice

        text = update_notice(latest_version())
        if text:
            self.notice.emit(text)


class AnalysisWorker(QThread):
    """Analyse a list of files off the UI thread, emitting results as they land.

    Signals:
        result(dict): one completed per-file analysis result.
        progress(int, int): (done, total) after each file.
        failed(str): a fatal error aborted the run.
        finished_ok(bool): run finished; the flag is True if it was cancelled.
    """

    result = Signal(dict)
    progress = Signal(int, int)
    failed = Signal(str)
    finished_ok = Signal(bool)

    def __init__(self, files: List[Path], sample_duration: float, deep: bool) -> None:
        super().__init__()
        self._files = list(files)
        self._sample_duration = sample_duration
        self._deep = deep
        self._cancel = False

    def cancel(self) -> None:
        """Request cancellation; the run stops after in-flight files complete."""
        self._cancel = True

    def run(self) -> None:  # noqa: D102 - QThread entry point
        total = len(self._files)
        if total == 0:
            self.finished_ok.emit(False)
            return

        analyzer = FLACAnalyzer(sample_duration=self._sample_duration, deep=self._deep)
        done: set[Path] = set()

        def consume(files: List[Path], workers: int) -> None:
            for path, res in analyze_batch(
                files, analyzer, workers, should_stop=lambda: self._cancel
            ):
                done.add(path)
                get_tracker().absorb_result(res)
                self.result.emit(res)
                self.progress.emit(len(done), total)

        try:
            workers = max(1, int(analysis_config.MAX_WORKERS))
            try:
                consume(self._files, workers)
            except BrokenProcessPool:
                # The CLI's answer, same reasoning: the pool dying is a start-up
                # failure in the workers, not a verdict on the audio. Finish the
                # rest here, slower and reliably.
                left = [f for f in self._files if f not in done]
                logger.error(
                    "The worker pool died after %d of %d files; finishing %d in this process",
                    len(done),
                    total,
                    len(left),
                )
                consume(left, 1)
        except Exception as exc:  # pool-level failure
            logger.error("Analysis run aborted: %s", exc)
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit(self._cancel)
