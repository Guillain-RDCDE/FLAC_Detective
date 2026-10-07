"""Tests for the beets ``flacdetective`` plugin.

Skipped entirely when beets is not installed (it is part of the optional
``beets`` / ``dev`` extras), so the core test suite stays dependency-light.
"""

import pytest

# importorskip returns the module, so this doubles as the import without
# tripping E402 (a plain import after a statement).
flacdetective = pytest.importorskip("beetsplug.flacdetective")


def test_is_analysable_accepts_lossless_containers():
    for fmt in ("FLAC", "flac", "WAV", "ALAC", "APE", "ape"):
        assert flacdetective.is_analysable(fmt), fmt


def test_is_analysable_rejects_lossy_and_empty():
    for fmt in ("MP3", "AAC", "OGG", "OPUS", "", None):
        assert not flacdetective.is_analysable(fmt), fmt


def test_command_registers_with_alias():
    plugin = flacdetective.FlacDetectivePlugin()
    commands = plugin.commands()
    assert len(commands) == 1
    cmd = commands[0]
    assert cmd.name == "flacdetective"
    assert "flacdet" in cmd.aliases


def test_command_has_the_update_option():
    plugin = flacdetective.FlacDetectivePlugin()
    cmd = plugin.commands()[0]
    opts, _ = cmd.parser.parse_args(["--update"])
    assert opts.update is True


def test_update_option_installs_through_the_shared_updater(monkeypatch, capsys):
    from flac_detective import update_check as uc
    from flac_detective import updater as up

    monkeypatch.setattr(uc, "fetch_latest_version", lambda: "9.9.9")
    monkeypatch.setattr(
        up,
        "upgrade",
        lambda on_line=None, **kw: up.UpgradeResult(
            ok=True,
            method="pip",
            command=["x"],
            installed_version="9.9.9",
            message="Installed 9.9.9.",
        ),
    )
    plugin = flacdetective.FlacDetectivePlugin()
    cmd = plugin.commands()[0]
    opts, args = cmd.parser.parse_args(["--update"])
    plugin._run(lib=None, opts=opts, args=args)
    out = capsys.readouterr().out
    assert "9.9.9 is available" in out and "Installed 9.9.9." in out


def test_flexible_attribute_types_declared():
    # Lets users run numeric queries like `beet ls flacdetective_score:55..`.
    item_types = flacdetective.FlacDetectivePlugin.item_types
    assert "flacdetective_score" in item_types
    assert "flacdetective_verdict" in item_types


def test_flagged_verdicts_are_all_styleable():
    # Every flagged verdict must have a console colour mapping.
    for verdict in flacdetective.FLAGGED_VERDICTS:
        assert verdict in flacdetective._VERDICT_STYLE
        color, _gloss = flacdetective._VERDICT_STYLE[verdict]
        assert color
