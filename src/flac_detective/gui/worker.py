"""Background analysis worker for the GUI.

Runs the same multiprocess analysis as the CLI (``ProcessPoolExecutor`` over
``FLACAnalyzer.analyze_file``) but on a Qt ``QThread`` so the UI stays responsive,
emitting a signal per completed file plus progress and lifecycle signals. Supports
cooperative cancellation.
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

from ..analysis import FLACAnalyzer
from ..config import analysis_config

logger = logging.getLogger(__name__)


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
        done = 0
        try:
            # Match the CLI: a process pool keeps a big scan fast. One worker may be
            # plenty on small selections, but reuse the configured cap for parity.
            with ProcessPoolExecutor(max_workers=analysis_config.MAX_WORKERS) as executor:
                futures = {executor.submit(analyzer.analyze_file, f): f for f in self._files}
                for future in as_completed(futures):
                    if self._cancel:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        res = future.result()
                    except Exception as exc:  # one file failing must not kill the run
                        logger.warning("Analysis failed for %s: %s", futures[future], exc)
                        res = {
                            "filepath": str(futures[future]),
                            "filename": Path(futures[future]).name,
                            "score": 0,
                            "verdict": "ERROR",
                            "reason": f"Error: {exc}",
                            "hires_verdict": "UNKNOWN",
                        }
                    self.result.emit(res)
                    done += 1
                    self.progress.emit(done, total)
        except Exception as exc:  # pool-level failure
            logger.error("Analysis run aborted: %s", exc)
            self.failed.emit(str(exc))
            return
        self.finished_ok.emit(self._cancel)
