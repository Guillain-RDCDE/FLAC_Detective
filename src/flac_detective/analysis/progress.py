"""Stage-level progress while ONE file is being analysed (issue #11).

``progress.json`` and the console bar both count COMPLETED files. That is the
right granularity for a library and none at all for a single long track: an
hour-long file is one tick that arrives minutes after it was earned, and an
application driving this engine has nothing to show in between. From the
outside the run does not look slow, it looks stuck.

This module carries the missing signal — which stage of one file's analysis has
just STARTED — and deliberately nothing else.

**There is no percentage, and there should not be one.** Which rules run
depends on what the earlier ones found: the authentic fast path returns before
the expensive half, ``--deep`` bypasses it, Rule 1's container test is skipped
at cutoffs where nothing reads the ratio, and Rules 11-15 each have their own
entry condition. The work left inside a file is not knowable when the file is
opened, so a percentage would be a progress bar that lies — which is the
failure the reporter already has. ``index``/``total`` is a position in a fixed
list of stages, not a fraction of the time.

Two ways in, one way out:

* an application passes ``on_progress=`` to :meth:`FLACAnalyzer.analyze_file`
  and receives events in its own process;
* the CLI installs a process-wide sink with :func:`set_sink`. That is what a
  pool worker uses — bound once by the pool initializer, so no callback is
  pickled per file and the submit call keeps its shape.

A sink is never trusted. :func:`emit` swallows anything it raises: a faulty
callback, or a queue whose parent has gone away, must not alter a verdict or
end a scan that would otherwise finish. Progress observes the work; it never
takes part in it.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)

#: The stages of one file's analysis, in the order they are entered.
#:
#: This is the published contract of ``--progress-events``: names are added at
#: the end if the pipeline ever grows one, never renamed or reordered, so a
#: consumer can match on them. ``done`` is terminal and is emitted exactly once
#: per file whatever the outcome — including for a file that fails, where it is
#: the only way a caller learns the engine has let go of it.
STAGES: Tuple[str, ...] = (
    "prepare",  # copy to local temp, or decode a non-native container via ffmpeg
    "metadata",  # header read, then the duration consistency check
    "spectrum",  # the cutoff, the edge step and the floor above it
    "quality",  # clipping, DC offset, silence, bit depth, upsampling
    "scoring",  # the rules — the long one: FLAC-equivalent sizing, R11-R15, the CNN
    "done",  # terminal, once per file, success or failure
)

_STAGE_INDEX: Dict[str, int] = {name: i + 1 for i, name in enumerate(STAGES)}


@dataclass(frozen=True)
class ProgressEvent:
    """One stage of one file has just started.

    A frozen dataclass rather than a ``NamedTuple``: ``index`` is the name this
    field has to carry, and on a tuple subclass that name shadows ``tuple.index``.
    Nothing here needs to be a tuple, so the clearer field name wins.

    Attributes:
        file: The path as the caller gave it.
        stage: One of :data:`STAGES`.
        index: 1-based position of ``stage`` in :data:`STAGES`.
        total: ``len(STAGES)`` — a count of stages, never a percentage of time.
    """

    file: str
    stage: str
    index: int
    total: int

    def as_dict(self) -> Dict[str, Any]:
        """The wire form, one JSON object per line on ``--progress-events``.

        ``event`` is a discriminator, so a consumer's parser keeps working if a
        second kind of event is ever added next to this one.
        """
        return {
            "event": "stage",
            "file": self.file,
            "stage": self.stage,
            "index": self.index,
            "total": self.total,
        }


ProgressCallback = Callable[[ProgressEvent], None]

# Process-wide sink, used when no callback is passed. Set in a pool worker by
# install_queue_sink(); None everywhere else, which is why an ordinary run
# neither builds an event nor calls anything.
_sink: Optional[ProgressCallback] = None


def set_sink(sink: Optional[ProgressCallback]) -> None:
    """Route events with no explicit callback to ``sink`` (``None`` disables)."""
    global _sink
    _sink = sink


def get_sink() -> Optional[ProgressCallback]:
    """The process-wide sink, or ``None``."""
    return _sink


def install_queue_sink(queue: Any) -> None:
    """Pool initializer: send this worker's events to ``queue``.

    Passed to ``ProcessPoolExecutor(initializer=...)`` with the queue as the
    single initarg. It must stay a module-level function: the initializer is
    pickled to reach the worker, and a closure or a lambda is not.
    """
    set_sink(queue.put)


def emit(
    stage: str,
    filepath: Union[str, Any],
    callback: Optional[ProgressCallback] = None,
) -> None:
    """Announce that ``stage`` has started for ``filepath``. Never raises.

    The explicit ``callback`` wins over the process-wide sink, so a library
    caller's callback is not affected by whatever the CLI installed.

    Args:
        stage: One of :data:`STAGES`. An unknown name is a bug here and raises,
            rather than being swallowed with the sink's own failures.
        filepath: The file being analysed; coerced with ``str``.
        callback: The caller's callback, if it passed one.
    """
    target = callback if callback is not None else _sink
    if target is None:
        return
    # Built before the guarded call on purpose: a KeyError here is OUR mistake
    # and must be loud, while anything the sink raises is the sink's problem.
    event = ProgressEvent(str(filepath), stage, _STAGE_INDEX[stage], len(STAGES))
    try:
        target(event)
    except Exception as exc:  # a sink must never reach the analysis
        logger.debug("Progress sink raised on stage %s (%s); continuing", stage, exc)
