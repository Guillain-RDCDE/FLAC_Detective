"""The update check: asks PyPI once a day, says one line, never gets in the way.

No test here touches the network: the fetch is injected. What is pinned is the
contract — opt-out respected, cache honoured for a day and refreshed after,
every failure a silent None, the notice only for a strictly newer final
release, and the background thread returning on time.
"""

from __future__ import annotations

import json
import threading
import time

from flac_detective import update_check as uc
from flac_detective.cli.args import build_parser

# ----------------------------------------------------------------- versions


def test_parse_version_accepts_final_releases_only():
    assert uc.parse_version("2.2.0") == (2, 2, 0)
    assert uc.parse_version("10.0.1") == (10, 0, 1)
    assert uc.parse_version("2.3.0rc1") is None
    assert uc.parse_version("2.3.0.dev4") is None
    assert uc.parse_version("") is None


def test_is_newer_compares_numerically_not_textually():
    assert uc.is_newer("2.10.0", "2.9.0") is True
    assert uc.is_newer("2.2.0", "2.2.0") is False
    assert uc.is_newer("2.1.9", "2.2.0") is False
    assert uc.is_newer("3.0.0", "2.2.0") is True
    # a pre-release on either side disables the comparison rather than guess
    assert uc.is_newer("2.3.0rc1", "2.2.0") is False
    assert uc.is_newer("2.3.0", "2.3.0.dev1") is False


def test_notice_only_for_a_newer_release():
    assert uc.update_notice(None, "2.2.0") is None
    assert uc.update_notice("2.2.0", "2.2.0") is None
    assert uc.update_notice("2.1.0", "2.2.0") is None
    text = uc.update_notice("2.3.0", "2.2.0")
    assert text is not None
    assert "2.3.0" in text and "2.2.0" in text
    assert "pip install -U flac-detective" in text


# ------------------------------------------------------------ latest_version


def _calls(value):
    """A fetch stub that records how many times it was asked."""
    calls = []

    def fetch():
        calls.append(1)
        return value

    return fetch, calls


def test_opt_out_env_means_no_request_at_all(tmp_path):
    fetch, calls = _calls("9.9.9")
    out = uc.latest_version(
        fetch=fetch, cache_file=tmp_path / "c.json", environ={uc.OPT_OUT_ENV: "1"}
    )
    assert out is None
    assert calls == []


def test_opt_out_env_false_values_do_not_opt_out(tmp_path):
    for value in ("", "0", "false", "no"):
        fetch, calls = _calls("2.9.0")
        out = uc.latest_version(
            fetch=fetch, cache_file=tmp_path / f"c{value}.json", environ={uc.OPT_OUT_ENV: value}
        )
        assert out == "2.9.0" and calls == [1]


def test_first_run_fetches_and_writes_the_cache(tmp_path):
    cache = tmp_path / "cache" / "update-check.json"
    fetch, calls = _calls("2.9.0")
    out = uc.latest_version(now=1000.0, fetch=fetch, cache_file=cache, environ={})
    assert out == "2.9.0" and calls == [1]
    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert saved == {"latest": "2.9.0", "checked_at": 1000.0}


def test_a_fresh_cache_is_used_without_a_request(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"latest": "2.8.0", "checked_at": 1000.0}), encoding="utf-8")
    fetch, calls = _calls("9.9.9")
    out = uc.latest_version(
        now=1000.0 + uc.CACHE_TTL_SECONDS - 1, fetch=fetch, cache_file=cache, environ={}
    )
    assert out == "2.8.0" and calls == []


def test_a_stale_cache_is_refreshed(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"latest": "2.8.0", "checked_at": 1000.0}), encoding="utf-8")
    fetch, calls = _calls("2.9.0")
    out = uc.latest_version(
        now=1000.0 + uc.CACHE_TTL_SECONDS, fetch=fetch, cache_file=cache, environ={}
    )
    assert out == "2.9.0" and calls == [1]
    assert json.loads(cache.read_text(encoding="utf-8"))["latest"] == "2.9.0"


def test_a_clock_set_back_does_not_trust_the_cache(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text(json.dumps({"latest": "2.8.0", "checked_at": 5000.0}), encoding="utf-8")
    fetch, calls = _calls("2.9.0")
    assert uc.latest_version(now=1000.0, fetch=fetch, cache_file=cache, environ={}) == "2.9.0"
    assert calls == [1]


def test_a_corrupt_cache_is_ignored_not_fatal(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text("{not json", encoding="utf-8")
    fetch, calls = _calls("2.9.0")
    assert uc.latest_version(fetch=fetch, cache_file=cache, environ={}) == "2.9.0"


def test_fetch_failure_is_a_silent_none(tmp_path):
    def fetch():
        return None

    assert uc.latest_version(fetch=fetch, cache_file=tmp_path / "c.json", environ={}) is None
    assert not (tmp_path / "c.json").exists()


def test_fetch_raising_is_a_silent_none(tmp_path):
    def fetch():
        raise RuntimeError("proxy said no")

    assert uc.latest_version(fetch=fetch, cache_file=tmp_path / "c.json", environ={}) is None


def test_a_non_version_answer_is_not_cached(tmp_path):
    fetch, _ = _calls("latest")
    assert uc.latest_version(fetch=fetch, cache_file=tmp_path / "c.json", environ={}) is None
    assert not (tmp_path / "c.json").exists()


def test_an_unwritable_cache_does_not_lose_the_answer(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    fetch, _ = _calls("2.9.0")
    # the cache "directory" is a file: mkdir fails, the answer still comes back
    assert uc.latest_version(fetch=fetch, cache_file=blocker / "c.json", environ={}) == "2.9.0"


def test_real_fetch_tolerates_no_network(monkeypatch):
    """The real fetch, pointed at nothing: None, not an exception."""
    monkeypatch.setattr(uc, "PYPI_URL", "http://127.0.0.1:9/nothing")
    assert uc.fetch_latest_version(timeout=0.5) is None


# -------------------------------------------------------------- the thread


def test_update_check_thread_returns_the_notice(monkeypatch):
    monkeypatch.setattr(uc, "latest_version", lambda: "2.9.0")
    check = uc.UpdateCheck(enabled=True, current="2.2.0").start()
    text = check.notice(wait=5.0)
    assert text is not None and "2.9.0" in text


def test_update_check_disabled_never_starts(monkeypatch):
    def boom():
        raise AssertionError("must not be called")

    monkeypatch.setattr(uc, "latest_version", boom)
    check = uc.UpdateCheck(enabled=False).start()
    assert check.notice(wait=1.0) is None


def test_update_check_that_is_still_running_is_dropped_on_time(monkeypatch):
    gate = threading.Event()

    def slow():
        gate.wait(5.0)
        return "2.9.0"

    monkeypatch.setattr(uc, "latest_version", slow)
    check = uc.UpdateCheck(enabled=True, current="2.2.0").start()
    t0 = time.perf_counter()
    assert check.notice(wait=0.2) is None
    assert time.perf_counter() - t0 < 2.0
    gate.set()


# ------------------------------------------------------------------- the CLI


def test_cli_has_the_opt_out_flag():
    args = build_parser().parse_args(["--no-update-check", "x.flac"])
    assert args.no_update_check is True
    assert build_parser().parse_args(["x.flac"]).no_update_check is False
