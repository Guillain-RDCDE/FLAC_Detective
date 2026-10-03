"""The worker pool, its in-process fallback, and the progress-event channel."""

import json
import logging
import multiprocessing
import sys
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Tuple

from ..analysis import FLACAnalyzer
from ..analysis.diagnostic_tracker import get_tracker
from ..analysis.progress import ProgressCallback, ProgressEvent, install_queue_sink
from ..config import analysis_config
from ..tracker import ProgressTracker
from . import console as _console
from .console import log_formatted_result
from .discovery import add_non_flac_results

logger = logging.getLogger(__name__)


@contextmanager
def progress_event_writer(dest: Optional[str]) -> Iterator[Optional[ProgressCallback]]:
    """Yield a callable writing one JSON object per line to ``dest``, or ``None``.

    ``dest`` is ``None`` (the feature is off and nothing is created), ``-`` for
    stderr, or a path. stderr rather than stdout because stdout already carries
    the report under ``--format json`` and that stream has to stay parseable —
    the same rule the banner obeys.

    Every line is flushed: a consumer reading this pipe wants the event now, and
    a block-buffered stream would hand it six at once when the file is over,
    which is the very problem this exists to solve. ASCII-escaped (json.dumps'
    default) so no console encoding can break a line — a filename outside the
    console codepage crashed the CLI once already.
    """
    if dest is None:
        yield None
        return

    stream: Any
    if dest == "-":
        stream, close = sys.stderr, False
    else:
        try:
            # Line-buffered and UTF-8: the bytes are ASCII either way, and a
            # reader tailing the file sees each event as it happens.
            stream, close = open(dest, "w", encoding="utf-8", buffering=1), True
        except OSError as exc:
            # A destination that cannot be written is a mistake in the command,
            # not a reason to analyse a library and then fail: say so and stop.
            raise SystemExit(f"--progress-events: cannot write to {dest}: {exc}")

    def write(event: ProgressEvent) -> None:
        stream.write(json.dumps(event.as_dict()) + "\n")
        stream.flush()

    try:
        yield write
    finally:
        if close:
            stream.close()


@contextmanager
def worker_event_channel(
    on_event: Optional[ProgressCallback],
) -> Iterator[Tuple[Optional[Callable[..., None]], tuple]]:
    """Carry progress events from pool workers back into this process.

    Yields the ``(initializer, initargs)`` pair for ``ProcessPoolExecutor``.
    With no consumer that pair is ``(None, ())`` and nothing whatsoever is
    built — no manager, no queue, no thread — so an ordinary scan is byte for
    byte the run it was before this feature existed.

    A manager queue rather than a plain ``multiprocessing.Queue``: its proxy is
    picklable by contract, which is what sending it through the pool's
    initargs needs on spawn platforms. It is bound once per worker by
    :func:`install_queue_sink`, so nothing extra is pickled per file.
    """
    if on_event is None:
        yield None, ()
        return

    manager = multiprocessing.Manager()
    queue = manager.Queue()

    def drain() -> None:
        # None is the sentinel, not a unique object(): the queue pickles what
        # goes through it, so identity does not survive the trip and `is` on a
        # sentinel object would never match. An event is never None.
        while True:
            try:
                item = queue.get()
            except (EOFError, OSError):  # BrokenPipeError is an OSError
                return
            if item is None:
                return
            try:
                on_event(item)
            except Exception as exc:  # a closed pipe downstream, typically
                logger.debug("Progress writer raised (%s); dropping the event", exc)

    thread = threading.Thread(target=drain, name="fd-progress-drain", daemon=True)
    thread.start()
    try:
        yield install_queue_sink, (queue,)
    finally:
        try:
            queue.put(None)
            thread.join(timeout=5)
        except Exception as exc:  # pragma: no cover - manager already gone
            logger.debug("Progress channel shutdown: %s", exc)
        manager.shutdown()


def analyze_batch(
    files: list[Path],
    analyzer: Any,
    workers: int,
    on_event: Optional[ProgressCallback] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> Iterator[tuple[Path, dict]]:
    """Yield ``(path, result)`` for each file, in a pool or in this process.

    ``workers <= 1`` runs here: no pool to break, and the heavy stack is imported
    once instead of once per worker. That is the fallback path, and it is also
    what ``--workers 1`` gives anyone whose machine cannot spawn workers at all.

    Args:
        files: Files to analyse.
        analyzer: The analyzer; must be picklable when ``workers > 1``.
        workers: Process count. 1 or less means in-process.
        on_event: Per-stage progress consumer (issue #11), or None for none. In
            process the analyzer is handed the callback; in the pool the events
            come back over a queue, because a callback does not cross a process.
        should_stop: Polled before each file (in process) or after each result
            (pooled). When it answers True the batch ends: queued files are
            cancelled and in-flight ones are left to finish. The GUI's cancel.

    Yields:
        ``(path, result)`` pairs, in completion order when pooled.
    """
    if workers <= 1:
        for path in files:
            if should_stop is not None and should_stop():
                return
            # The call keeps its old shape when the feature is off, so anything
            # duck-typed as an analyzer elsewhere is unaffected by this argument.
            if on_event is None:
                yield path, analyzer.analyze_file(path)
            else:
                yield path, analyzer.analyze_file(path, on_progress=on_event)
        return
    with worker_event_channel(on_event) as (initializer, initargs):
        with ProcessPoolExecutor(
            max_workers=workers, initializer=initializer, initargs=initargs
        ) as executor:
            futures = {executor.submit(analyzer.analyze_file, f): f for f in files}
            for future in as_completed(futures):
                if should_stop is not None and should_stop():
                    executor.shutdown(wait=False, cancel_futures=True)
                    return
                yield futures[future], future.result()


def process_flac_files(
    files_to_process: list[Path],
    tracker: ProgressTracker,
    analyzer: FLACAnalyzer,
    advanced: bool = False,
    on_event: Optional[ProgressCallback] = None,
):
    """Process FLAC files with multi-processing and rich progress.

    Falls back to this process if the worker pool dies. See ``run`` below.

    Args:
        files_to_process: List of FLAC files to analyze.
        tracker: Progress tracker instance.
        analyzer: FLAC analyzer instance.
        advanced: Pass-through to the per-file console line (show score or not).
        on_event: Per-stage progress consumer (``--progress-events``), or None.
    """
    total_files = len(files_to_process)

    # Use Rich Progress if available. Read from the console module at call time
    # so a test can switch Rich off in one place.
    progress_ctx: Any
    if _console.HAS_RICH:
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeRemainingColumn,
        )

        progress_ctx = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=_console.console,
        )
    else:
        progress_ctx = nullcontext()

    processed_count = 0
    done: set[Path] = set()

    def consume(files: list[Path], workers: int, progress: Any = None, task_id: Any = None) -> None:
        """Analyse ``files`` and record every result as it lands."""
        nonlocal processed_count
        for path, result in analyze_batch(files, analyzer, workers, on_event):
            done.add(path)
            # A worker's reading issues ride in the result; the parent's
            # tracker is the one the diagnostic report is written from.
            get_tracker().absorb_result(result)
            tracker.add_result(result)
            processed_count += 1
            if progress is not None:
                progress.update(task_id, advance=1)
            # Logged inside the progress block so RichHandler puts it above the bar.
            log_formatted_result(result, processed_count, total_files, advanced)
            if processed_count % analysis_config.SAVE_INTERVAL == 0:
                tracker.save()

    def run(progress: Any = None, task_id: Any = None) -> None:
        """Run the pool, and finish the job by hand if the pool dies.

        A BrokenProcessPool used to reach the user as a bare traceback with every
        remaining file unanalysed. The pool dies for reasons that have nothing to
        do with the audio — most often a worker killed while importing, which on
        Windows is `WinError 1450` — so the right answer is to stop asking for
        workers, not to stop working. What is already recorded stays recorded;
        the rest is finished in this process, slower and reliably.
        """
        workers = max(1, int(analysis_config.MAX_WORKERS))
        try:
            consume(files_to_process, workers, progress, task_id)
        except BrokenProcessPool:
            left = [f for f in files_to_process if f not in done]
            logger.error(
                "The worker pool died after %d of %d files. This is a start-up failure "
                "in the workers, not a problem with your audio — on Windows it is usually "
                "'WinError 1450' while importing. Finishing the remaining %d file(s) in "
                "this process. Use --workers to set a lower number next time.",
                len(done),
                total_files,
                len(left),
            )
            tracker.save()
            consume(left, 1, progress, task_id)

    if _console.HAS_RICH:
        with progress_ctx as progress:
            task_id = progress.add_task("[cyan]Analyzing audio files...", total=total_files)
            run(progress, task_id)
    else:
        run()


def run_analysis_loop(
    all_flac_files: list[Path],
    all_non_flac_files: list[Path],
    output_dir: Path,
    sample_duration: Optional[float] = None,
    deep: bool = False,
    advanced: bool = False,
    on_event: Optional[ProgressCallback] = None,
    repair_in_place: bool = False,
) -> list[dict]:
    """Run the main analysis loop on the provided files.

    Args:
        all_flac_files: List of FLAC files to analyze.
        all_non_flac_files: List of non-FLAC files to report.
        output_dir: Directory for saving progress and reports.
        sample_duration: Override the default audio sample duration (seconds).
            None falls back to `analysis_config.SAMPLE_DURATION`.
        deep: Run Rule 12 (ML) on every file, bypassing the authentic fast path.
            See the ``--deep`` flag.
        advanced: Show numeric scores in the per-file console line (else easy mode).
        on_event: Per-stage progress consumer (``--progress-events``), or None.
        repair_in_place: Replace undecodable files with their lossless repair
            (``--repair-in-place``); off by default.

    Returns:
        List of result dictionaries.
    """
    effective_duration = (
        sample_duration if sample_duration is not None else analysis_config.SAMPLE_DURATION
    )
    analyzer = FLACAnalyzer(
        sample_duration=effective_duration, deep=deep, repair_in_place=repair_in_place
    )
    tracker = ProgressTracker(progress_file=output_dir / "progress.json")

    # Filter already processed files
    files_to_process = [f for f in all_flac_files if not tracker.is_processed(str(f))]

    if not files_to_process:
        logger.info("All files have already been processed!")
        logger.info("Delete progress.json to restart analysis")
    else:
        tracker.set_total(len(all_flac_files))
        processed, total = tracker.get_progress()

        logger.info(f"Resuming: {processed}/{total} files already processed")
        logger.info(f"{len(files_to_process)} files remaining to analyze")
        logger.info(f"Multi-processing: {analysis_config.MAX_WORKERS} workers")
        print()

        # Multi-process analysis
        process_flac_files(files_to_process, tracker, analyzer, advanced, on_event)

        # Final save
        tracker.save()

    # Add non-FLAC audio files to results
    add_non_flac_results(all_non_flac_files, tracker)

    # Clean up progress file after successful completion
    tracker.cleanup()

    return tracker.get_results()
