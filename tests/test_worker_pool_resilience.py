"""A dying worker pool must not take the run down with it.

Reported from the field against v1.13.0: 36 files, 16 workers, Store Python
3.12 on Windows 11. Every worker died inside the import machinery with
``OSError: [WinError 1450] Insufficient system resources`` — raised while
LISTING a package directory, before a single sample was decoded — and the run
ended on a bare ``BrokenProcessPool`` traceback with nothing analysed.

The reporter's diagnosis was that the tool loads every FLAC into memory at once.
The traceback says otherwise: the failure is at start-up, in ``_fill_cache``.
Under spawn each worker is a fresh interpreter re-importing numpy, scipy,
soundfile and torch, and sixteen of those at once open thousands of handles in
the same instant.

Three defects, one report: no cap on the worker count, no way for the user to
lower it, and no recovery when the pool dies. These tests cover all three.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from concurrent.futures.process import BrokenProcessPool  # noqa: E402

from flac_detective import main as fd_main  # noqa: E402
from flac_detective.config import AnalysisConfig  # noqa: E402


def _result(path: Path) -> dict:
    # `filename` is required by the console line; a result without it is not a
    # result this code path ever sees.
    return {
        "file_path": str(path),
        "filename": path.name,
        "verdict": "AUTHENTIC",
        "score": 0,
    }


class _Analyzer:
    """An analyzer that answers for every file it is given."""

    def analyze_file(self, path):
        return _result(Path(path))


def test_the_worker_count_is_capped():
    """os.cpu_count() alone put 16 interpreters into the import machinery at once."""
    cfg = AnalysisConfig()
    assert cfg.MAX_WORKERS <= cfg.WORKER_CAP
    assert cfg.MAX_WORKERS >= 1


def test_one_worker_runs_in_process(tmp_path):
    """--workers 1 must spawn nothing at all, not spawn one."""
    files = [tmp_path / f"{i}.flac" for i in range(3)]
    pairs = list(fd_main._analyze_batch(files, _Analyzer(), workers=1))
    assert [p for p, _ in pairs] == files
    assert all(r["verdict"] == "AUTHENTIC" for _, r in pairs)


def test_a_broken_pool_is_finished_in_process(tmp_path, monkeypatch, caplog):
    """The reported failure: the pool dies mid-run and the rest must still be done.

    The first batch yields two results and then raises BrokenProcessPool, exactly
    as a worker killed during import does. The two already recorded must survive
    and the remaining three must be analysed in this process.
    """
    files = [tmp_path / f"{i}.flac" for i in range(5)]
    calls = []

    def fake_batch(batch, analyzer, workers):
        calls.append((list(batch), workers))
        if workers > 1:
            yield batch[0], _result(batch[0])
            yield batch[1], _result(batch[1])
            raise BrokenProcessPool("A process in the process pool was terminated abruptly")
        for path in batch:
            yield path, _result(path)

    monkeypatch.setattr(fd_main, "_analyze_batch", fake_batch)
    monkeypatch.setattr(fd_main, "HAS_RICH", False)
    monkeypatch.setattr(fd_main.analysis_config, "MAX_WORKERS", 8)

    tracker = MagicMock()
    fd_main._process_flac_files(files, tracker, _Analyzer(), advanced=False)

    # Every file has a result, and none was recorded twice.
    recorded = [c.args[0]["file_path"] for c in tracker.add_result.call_args_list]
    assert sorted(recorded) == sorted(str(f) for f in files)
    assert len(recorded) == len(set(recorded))

    # The retry asked for no workers, and only for what was left.
    assert calls[0][1] == 8
    assert calls[1][1] == 1
    assert calls[1][0] == files[2:]

    # And it said so, in terms that point at the cause rather than at the audio.
    assert any("worker pool died" in r.message for r in caplog.records)


def test_a_broken_pool_saves_what_it_had(tmp_path, monkeypatch):
    """Progress is flushed before the retry: a second failure must not cost the first half."""
    files = [tmp_path / f"{i}.flac" for i in range(4)]

    def fake_batch(batch, analyzer, workers):
        if workers > 1:
            yield batch[0], _result(batch[0])
            raise BrokenProcessPool("boom")
        for path in batch:
            yield path, _result(path)

    monkeypatch.setattr(fd_main, "_analyze_batch", fake_batch)
    monkeypatch.setattr(fd_main, "HAS_RICH", False)
    monkeypatch.setattr(fd_main.analysis_config, "MAX_WORKERS", 4)

    tracker = MagicMock()
    fd_main._process_flac_files(files, tracker, _Analyzer(), advanced=False)
    assert tracker.save.called, "the pool died and nothing was written to disk"
