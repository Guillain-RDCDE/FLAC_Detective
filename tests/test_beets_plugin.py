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
