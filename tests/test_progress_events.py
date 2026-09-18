"""Progress inside ONE file, asked for in issue #11.

The reporter drives the engine from his own application. ``progress.json`` and
the console bar count completed files, so an hour-long track is one tick that
arrives when it is already over, and his UI looks stuck for the whole of it.

What these tests pin is not that events exist — it is the three properties an
integrator has to be able to rely on:

* the stages arrive in a fixed order, so a UI can map them to labels it wrote
  in advance, and ``done`` arrives exactly once per file INCLUDING a file that
  failed, which is the case a UI hangs on if it is missed;
* a callback cannot change a verdict, however badly it behaves — progress
  observes the analysis, it is not part of it;
* the events survive the process boundary, because the CLI does its work in a
  pool and a callback does not cross a process. That last one is the whole
  reason the queue exists, and it is the part that a unit test of the analyser
  alone would never have caught.

The audio here is noise. None of these questions is about a verdict, and a file
that takes the fast path exercises the same six stages as any other.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective import main as fd_main  # noqa: E402
from flac_detective.analysis.analyzer import FLACAnalyzer  # noqa: E402
from flac_detective.analysis.progress import (  # noqa: E402
    STAGES,
    ProgressEvent,
    emit,
    get_sink,
    set_sink,
)

SAMPLE_RATE = 44_100


def _write_noise(path: Path, seconds: float = 4.0, seed: int = 11) -> Path:
    """A short, honest lossless file — enough audio for every stage to run."""
    rng = np.random.default_rng(seed)
    samples = rng.normal(0.0, 0.12, size=(int(SAMPLE_RATE * seconds), 2))
    sf.write(str(path), samples, SAMPLE_RATE, subtype="PCM_16")
    return path


@pytest.fixture(scope="module")
def audio(tmp_path_factory):
    """One analysable file, written once for the whole module."""
    return _write_noise(tmp_path_factory.mktemp("progress") / "noise.flac")


def test_the_stages_arrive_in_order_once_each(audio):
    """The published contract: STAGES, in that order, 1-based, out of len(STAGES)."""
    seen: list[ProgressEvent] = []
    FLACAnalyzer(sample_duration=5.0).analyze_file(audio, on_progress=seen.append)

    assert [e.stage for e in seen] == list(STAGES)
    assert [e.index for e in seen] == list(range(1, len(STAGES) + 1))
    assert {e.total for e in seen} == {len(STAGES)}
    assert {e.file for e in seen} == {str(audio)}


def test_done_arrives_even_when_the_file_cannot_be_analysed(tmp_path):
    """A UI waits on the terminal event; a file that fails must release it too.

    Without this, the files that hang an integrator's interface are exactly the
    broken ones — the case where a user most wants to be told something.
    """
    broken = tmp_path / "notaudio.flac"
    broken.write_bytes(b"this is not a FLAC at all")

    seen: list[ProgressEvent] = []
    result = FLACAnalyzer().analyze_file(broken, on_progress=seen.append)

    assert result["verdict"] == "ERROR"
    assert seen[-1].stage == "done"
    assert [e.stage for e in seen].count("done") == 1


def test_a_callback_that_raises_changes_nothing(audio):
    """Progress observes the work. A bad callback must not reach the verdict."""

    def hostile(_event: ProgressEvent) -> None:
        raise RuntimeError("the caller's UI thread is having a bad day")

    quiet = FLACAnalyzer(sample_duration=5.0).analyze_file(audio)
    noisy = FLACAnalyzer(sample_duration=5.0).analyze_file(audio, on_progress=hostile)

    assert noisy == quiet


def test_without_a_consumer_nothing_is_emitted():
    """The default path builds no event and calls nothing."""
    assert get_sink() is None
    emit("prepare", "some/file.flac")  # must not raise, must not need a sink


def test_an_unknown_stage_is_our_bug_and_is_loud():
    """A sink's failures are swallowed; a wrong stage name here is not one."""
    calls: list[ProgressEvent] = []
    with pytest.raises(KeyError):
        emit("not-a-stage", "x.flac", calls.append)
    assert calls == []


def test_the_explicit_callback_wins_over_the_process_sink():
    """A library caller's callback must not be affected by what the CLI installed."""
    installed: list[ProgressEvent] = []
    mine: list[ProgressEvent] = []
    set_sink(installed.append)
    try:
        emit("prepare", "x.flac", mine.append)
    finally:
        set_sink(None)
    assert [e.stage for e in mine] == ["prepare"]
    assert installed == []


def test_the_wire_form_carries_a_discriminator():
    """``event`` is what lets a consumer's parser survive a second kind of line."""
    payload = ProgressEvent("a.flac", "spectrum", 3, 6).as_dict()
    assert payload == {
        "event": "stage",
        "file": "a.flac",
        "stage": "spectrum",
        "index": 3,
        "total": 6,
    }


class _StrictAnalyzer:
    """An analyzer that accepts the OLD call shape and nothing else."""

    def analyze_file(self, path):
        return {"filename": Path(path).name, "verdict": "AUTHENTIC", "score": 0}


def test_the_default_call_shape_is_unchanged(tmp_path):
    """With no consumer, nothing new is passed to analyze_file.

    The beets plugin, the GUI worker and this repository's own test doubles all
    call the analyser with one argument. Adding a keyword unconditionally would
    have broken every one of them for a feature they never asked for.
    """
    files = [tmp_path / f"{i}.flac" for i in range(2)]
    pairs = list(fd_main._analyze_batch(files, _StrictAnalyzer(), workers=1))
    assert [p for p, _ in pairs] == files


def test_events_come_back_from_the_pool(tmp_path):
    """The one that matters: a callback does not cross a process, so events must.

    ``_analyze_batch`` with real workers is the CLI's own path. Two files so the
    test also shows the events are attributed to the file that produced them and
    not merged into one stream.
    """
    files = [_write_noise(tmp_path / f"w{i}.flac", seconds=3.0, seed=i) for i in range(2)]
    seen: list[ProgressEvent] = []

    pairs = list(
        fd_main._analyze_batch(
            files, FLACAnalyzer(sample_duration=5.0), workers=2, on_event=seen.append
        )
    )

    assert len(pairs) == 2
    assert len(seen) == 2 * len(STAGES)
    for path in files:
        stages = [e.stage for e in seen if e.file == str(path)]
        assert stages == list(STAGES)


def test_an_unwritable_destination_stops_before_the_scan(tmp_path):
    """Say the command is wrong now, not after an hour of analysis."""
    with pytest.raises(SystemExit):
        with fd_main._progress_event_writer(str(tmp_path / "no-such-dir" / "events.ndjson")):
            pass  # pragma: no cover - the context manager raises on entry


def test_off_by_default_creates_nothing():
    """No destination means no writer, no queue, no thread."""
    with fd_main._progress_event_writer(None) as on_event:
        assert on_event is None
    with fd_main._worker_event_channel(None) as (initializer, initargs):
        assert initializer is None
        assert initargs == ()


def test_the_cli_writes_ndjson_and_keeps_stdout_parseable(tmp_path):
    """End to end, the way an application will actually run it.

    ``--format json`` and ``--progress-events`` at once, because the two streams
    must not tread on each other: the report is stdout's, the events are not.
    """
    _write_noise(tmp_path / "one.flac", seconds=3.0, seed=21)
    events_path = tmp_path / "events.ndjson"

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from flac_detective.main import main; main()",
            "--workers",
            "2",
            "--sample-duration",
            "5",
            "--format",
            "json",
            "--progress-events",
            str(events_path),
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        env={
            **dict(__import__("os").environ),
            "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src"),
        },
        cwd=str(tmp_path),
        timeout=900,
    )

    assert proc.returncode == 0, proc.stderr[-2000:]
    report = json.loads(proc.stdout)
    assert len(report["results"]) == 1

    events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    assert [e["stage"] for e in events] == list(STAGES)
    assert all(e["event"] == "stage" for e in events)
    assert all(Path(e["file"]).name == "one.flac" for e in events)
