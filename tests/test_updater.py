"""The in-tool installer, tested without installing anything.

It finds how this copy was installed, runs the matching upgrade, and believes
a fresh interpreter rather than an exit code. No test touches the network or installs anything: the command runner and the
version reader are injected. One test does run a real subprocess — the
current interpreter printing lines — to prove the streaming runner itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

from flac_detective import updater as up
from flac_detective.cli import update_flow

# ------------------------------------------------------------ install method


def test_pip_is_the_default_method(tmp_path):
    pkg = tmp_path / "site-packages" / "flac_detective" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    exe = tmp_path / "venv" / "Scripts" / "python.exe"
    assert (
        up.install_method(executable=str(exe), package_file=str(pkg), environ={}) == up.METHOD_PIP
    )


def test_a_pipx_venv_is_recognised(tmp_path):
    pkg = tmp_path / "x" / "flac_detective" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    exe = tmp_path / "pipx" / "venvs" / "flac-detective" / "bin" / "python"
    assert (
        up.install_method(executable=str(exe), package_file=str(pkg), environ={}) == up.METHOD_PIPX
    )


def test_a_source_checkout_is_recognised(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    pkg = tmp_path / "src" / "flac_detective" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    assert (
        up.install_method(executable=sys.executable, package_file=str(pkg), environ={})
        == up.METHOD_SOURCE
    )


def test_docker_is_recognised_by_its_variable(tmp_path):
    pkg = tmp_path / "sp" / "flac_detective" / "__init__.py"
    pkg.parent.mkdir(parents=True)
    pkg.write_text("", encoding="utf-8")
    method = up.install_method(
        executable="/usr/local/bin/python",
        package_file=str(pkg),
        environ={"FLAC_DETECTIVE_IN_DOCKER": "1"},
    )
    assert method == up.METHOD_DOCKER


def test_commands_and_hints_per_method():
    assert up.upgrade_command(up.METHOD_PIP, executable="/py")[:4] == [
        "/py",
        "-m",
        "pip",
        "install",
    ]
    assert "--upgrade" in up.upgrade_command(up.METHOD_PIP, executable="/py")
    assert up.upgrade_command(up.METHOD_PIPX) == ["pipx", "upgrade", "flac-detective"]
    assert up.upgrade_command(up.METHOD_SOURCE) is None
    assert up.upgrade_command(up.METHOD_DOCKER) is None
    assert "docker pull" in up.manual_hint(up.METHOD_DOCKER)
    assert "git pull" in up.manual_hint(up.METHOD_SOURCE)
    assert "pipx upgrade" in up.manual_hint(up.METHOD_PIPX)
    assert "pip install -U flac-detective" in up.manual_hint(up.METHOD_PIP)


# ------------------------------------------------------------------ the runner


def test_run_command_streams_lines_and_returns_them():
    seen = []
    code, output = up.run_command(
        [sys.executable, "-c", "print('one'); print('two')"], on_line=seen.append, timeout=60
    )
    assert code == 0
    assert seen == ["one", "two"]
    assert output.splitlines() == ["one", "two"]


def test_run_command_reports_a_failing_command():
    code, output = up.run_command(
        [sys.executable, "-c", "import sys; print('x'); sys.exit(3)"], timeout=60
    )
    assert code == 3 and "x" in output


def test_run_command_that_cannot_start_is_a_code_not_an_exception():
    code, output = up.run_command(["no-such-program-flac-detective-test"])
    assert code == -1 and "could not start" in output


def test_installed_version_reads_the_distribution_of_this_interpreter():
    from flac_detective.update_check import current_version

    assert up.installed_version(sys.executable) == current_version()


def test_current_version_is_the_distribution_not_the_import(monkeypatch):
    """What pip manages is the distribution; the import may be a checkout on sys.path."""
    import importlib.metadata as md

    from flac_detective import update_check as uc

    monkeypatch.setattr(md, "version", lambda name: "1.2.3")
    assert uc.current_version() == "1.2.3"

    def boom(name):
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "version", boom)
    from flac_detective.__version__ import __version__

    assert uc.current_version() == __version__


# ------------------------------------------------------------------- upgrade()


def _runner(code, output="pip says hi"):
    calls = []

    def run(command, on_line=None):
        calls.append(command)
        if on_line:
            on_line(output)
        return code, output

    return run, calls


def test_upgrade_ok_when_a_fresh_interpreter_reports_a_newer_version():
    run, calls = _runner(0)
    result = up.upgrade(
        method=up.METHOD_PIP,
        executable="/py",
        runner=run,
        verify=lambda exe: "9.9.9",
        current="2.3.0",
        deferred=False,
    )
    assert result.ok is True
    assert result.installed_version == "9.9.9"
    assert calls and calls[0][0] == "/py"
    assert "Restart" in result.message


def test_upgrade_not_ok_when_the_version_did_not_move():
    run, _ = _runner(0)
    result = up.upgrade(
        method=up.METHOD_PIP,
        executable="/py",
        runner=run,
        verify=lambda exe: "2.3.0",
        current="2.3.0",
        deferred=False,
    )
    assert result.ok is False
    assert "Nothing newer" in result.message


def test_upgrade_reports_the_installer_failure_with_the_manual_command():
    run, _ = _runner(1, "ERROR: no permission")
    result = up.upgrade(
        method=up.METHOD_PIP,
        executable="/py",
        runner=run,
        verify=lambda exe: "9.9.9",
        deferred=False,
    )
    assert result.ok is False
    assert "code 1" in result.message and "/py -m pip install" in result.message
    assert "no permission" in result.output


def test_upgrade_refuses_a_source_checkout_and_docker():
    for method in (up.METHOD_SOURCE, up.METHOD_DOCKER):
        result = up.upgrade(
            method=method, runner=lambda *a, **k: (0, ""), verify=lambda exe: "9.9.9"
        )
        assert result.ok is False and result.command == []
        assert "not upgraded from inside" in result.message


def test_upgrade_handles_an_unreadable_new_version():
    run, _ = _runner(0)
    result = up.upgrade(
        method=up.METHOD_PIP,
        executable="/py",
        runner=run,
        verify=lambda exe: None,
        deferred=False,
    )
    assert result.ok is False and "could not be read back" in result.message


# ------------------------------------------------- Windows: the deferred install


def test_deferred_is_windows_only():
    assert up.needs_deferred_install("win32") is True
    assert up.needs_deferred_install("linux") is False
    assert up.needs_deferred_install("darwin") is False


def test_upgrade_hands_the_install_to_the_detached_process_when_deferred(tmp_path):
    started = []

    def starter(command, executable, current):
        started.append((command, executable, current))
        return tmp_path / "update-install.json"

    run, calls = _runner(0)
    result = up.upgrade(
        method=up.METHOD_PIP,
        executable="/py",
        runner=run,
        deferred=True,
        starter=starter,
        current="2.3.0",
    )
    assert result.deferred is True and result.ok is False
    assert calls == []  # nothing ran in this process
    assert started and started[0][1] == "/py" and started[0][2] == "2.3.0"
    assert "as soon as FLAC Detective exits" in result.message
    assert "update-install.log" in result.message


def test_upgrade_deferred_but_pipx_runs_inline():
    """The pipx launcher is not ours to lock: the pipx path stays inline."""
    run, calls = _runner(0)
    result = up.upgrade(
        method=up.METHOD_PIPX,
        runner=run,
        verify=lambda exe: "9.9.9",
        deferred=True,
        current="2.3.0",
    )
    assert result.deferred is False and result.ok is True and calls


def test_deferred_main_waits_runs_verifies_and_writes_the_report(tmp_path, capsys):
    report = tmp_path / "r" / "update-install.json"
    waited = []
    ran = []

    def waiter(pids):
        waited.append(pids)
        return True

    def runner(command, on_line=None):
        ran.append(command)
        if on_line:
            on_line("Successfully installed flac-detective-9.9.9")
        return 0, "Successfully installed flac-detective-9.9.9"

    code = up.deferred_main(
        [
            "--deferred",
            "123,456",
            "--report",
            str(report),
            "--current",
            "2.3.0",
            "--",
            "/py",
            "-m",
            "pip",
            "x",
        ],
        waiter=waiter,
        runner=runner,
        verify=lambda exe: "9.9.9",
    )
    assert code == 0
    assert waited == [[123, 456]]
    assert ran == [["/py", "-m", "pip", "x"]]
    data = (
        up.consume_install_report.__wrapped__(report)
        if hasattr(up.consume_install_report, "__wrapped__")
        else None
    )
    import json

    data = json.loads(report.read_text(encoding="utf-8"))
    assert (
        data["ok"] is True
        and data["installed_version"] == "9.9.9"
        and data["previous_version"] == "2.3.0"
    )
    assert "Update installed" in data["message"]
    assert "Successfully installed" in capsys.readouterr().out


def test_deferred_main_reports_a_failed_install(tmp_path):
    report = tmp_path / "update-install.json"
    code = up.deferred_main(
        ["--deferred", "1", "--report", str(report), "--current", "2.3.0", "--", "/py", "x"],
        waiter=lambda pids: True,
        runner=lambda command, on_line=None: (1, "ERROR"),
        verify=lambda exe: None,
    )
    import json

    assert code == 1
    data = json.loads(report.read_text(encoding="utf-8"))
    assert (
        data["ok"] is False and "did not install" in data["message"] and "/py x" in data["message"]
    )


def test_deferred_main_without_a_command_does_nothing(tmp_path):
    assert up.deferred_main(["--report", str(tmp_path / "r.json")]) == 2
    assert not (tmp_path / "r.json").exists()


def test_consume_install_report_reads_once(tmp_path, monkeypatch):
    import json

    path = tmp_path / "update-install.json"
    monkeypatch.setattr(up, "install_report_path", lambda: path)
    assert up.consume_install_report() is None
    path.write_text(
        json.dumps({"ok": True, "message": "Update installed: 9.9.9"}), encoding="utf-8"
    )
    first = up.consume_install_report()
    assert first and first["message"].startswith("Update installed")
    assert not path.exists()
    assert up.consume_install_report() is None
    path.write_text("{broken", encoding="utf-8")
    assert up.consume_install_report() is None and not path.exists()


def test_wait_for_exit_on_a_real_short_process():
    import subprocess
    import time

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.6)"])
    t0 = time.perf_counter()
    assert up.wait_for_exit([proc.pid], timeout=30) is True
    assert proc.poll() is not None
    assert time.perf_counter() - t0 < 25
    assert up.wait_for_exit([0, -1], timeout=1) is True  # nothing to wait for


def test_wait_for_exit_sees_through_a_zombie_child():
    """An exited child nobody waited for must count as exited (CI on Linux/macOS, 2026-10-07).

    ``os.kill(pid, 0)`` succeeds on a zombie; the POSIX probe reaps a child
    with ``waitpid`` first. On Windows the handle wait already does the right
    thing, so this is the same assertion on every platform.
    """
    import subprocess
    import time

    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    time.sleep(1.0)  # the child has exited; it is not reaped (no proc.wait())
    assert up.wait_for_exit([proc.pid], timeout=10) is True
    proc.wait()


def test_wait_for_exit_times_out_on_a_long_process():
    import subprocess

    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
    try:
        assert up.wait_for_exit([proc.pid], timeout=1.0) is False
    finally:
        proc.kill()
        proc.wait()


def test_cli_prints_a_deferred_result_as_a_notice_not_a_failure(capsys):
    result = up.UpgradeResult(
        ok=False, method="pip", command=["x"], deferred=True, message="will install on exit"
    )
    assert update_flow._report(result) == 0
    assert "will install on exit" in capsys.readouterr().out


def test_cli_prints_the_last_install_report_once(capsys):
    update_flow.print_install_report(
        {"ok": True, "message": "Update installed: FLAC Detective 9.9.9"}
    )
    assert "Update installed" in capsys.readouterr().out
    update_flow.print_install_report(None)
    assert capsys.readouterr().out == ""


# ------------------------------------------------------------- the CLI flows


def _upgrader(ok=True):
    calls = []

    def go(on_line=None):
        calls.append(1)
        if on_line:
            on_line("Successfully installed flac-detective-9.9.9")
        return up.UpgradeResult(
            ok=ok,
            method="pip",
            command=["x"],
            installed_version="9.9.9",
            message="done" if ok else "failed",
        )

    return go, calls


def test_update_command_installs_when_newer(capsys):
    go, calls = _upgrader()
    code = update_flow.run_update_command(fetch=lambda: "9.9.9", upgrader=go, current="2.3.0")
    assert code == 0 and calls == [1]
    assert "9.9.9 is available" in capsys.readouterr().out


def test_update_command_says_up_to_date_and_runs_nothing(capsys):
    go, calls = _upgrader()
    code = update_flow.run_update_command(fetch=lambda: "2.3.0", upgrader=go, current="2.3.0")
    assert code == 0 and calls == []
    assert "latest release" in capsys.readouterr().out


def test_update_command_without_network_changes_nothing(capsys):
    go, calls = _upgrader()
    code = update_flow.run_update_command(fetch=lambda: None, upgrader=go, current="2.3.0")
    assert code == 2 and calls == []
    assert "could not be reached" in capsys.readouterr().out


def test_update_command_failure_exit_code():
    go, _ = _upgrader(ok=False)
    assert update_flow.run_update_command(fetch=lambda: "9.9.9", upgrader=go, current="2.3.0") == 1


def test_offer_update_does_nothing_without_a_notice():
    go, calls = _upgrader()
    assert update_flow.offer_update(None, interactive=True, upgrader=go) is None
    assert calls == []


def test_offer_update_unattended_prints_the_command_and_asks_nothing(capsys):
    go, calls = _upgrader()
    asked = []

    def ask(prompt):
        asked.append(prompt)
        return "y"

    out = update_flow.offer_update(
        "A newer FLAC Detective is available: 9.9.9", interactive=False, ask=ask, upgrader=go
    )
    assert out is None and calls == [] and asked == []
    assert "flac-detective --update" in capsys.readouterr().out


def test_offer_update_no_is_the_default(capsys):
    go, calls = _upgrader()
    out = update_flow.offer_update("notice", interactive=True, ask=lambda p: "", upgrader=go)
    assert out is None and calls == []
    assert "Not now" in capsys.readouterr().out


def test_offer_update_yes_installs(capsys):
    go, calls = _upgrader()
    out = update_flow.offer_update("notice", interactive=True, ask=lambda p: "Y", upgrader=go)
    assert out is not None and out.ok and calls == [1]
    assert "Successfully installed" in capsys.readouterr().out


def test_offer_update_eof_means_no():
    go, calls = _upgrader()

    def ask(prompt):
        raise EOFError

    assert update_flow.offer_update("notice", interactive=True, ask=ask, upgrader=go) is None
    assert calls == []


def test_cli_has_the_update_flag_and_needs_no_path():
    from flac_detective.cli.args import build_parser

    args = build_parser().parse_args(["--update"])
    assert args.update is True and args.paths == []
    assert Path  # keep the import honest for the pipx test above
