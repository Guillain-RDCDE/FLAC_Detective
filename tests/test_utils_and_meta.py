"""Coverage quick wins: easy-to-test surface (version metadata, file discovery,
LOGO assembly, colorize). These modules sit at the boundary of the package and
are exercised by every CLI run, but were previously untested.
"""

from pathlib import Path

import pytest

from flac_detective import __version__
from flac_detective.__version__ import (
    __author__,
    __email__,
    __license__,
    __release_date__,
    __release_name__,
    __url__,
)
from flac_detective.__version__ import __version__ as v
from flac_detective.__version__ import (
    __version_info__,
)
from flac_detective.colors import Colors, colorize
from flac_detective.utils import LOGO, find_flac_files, find_non_flac_audio_files

# ---------------------------------------------------------------------------
# __version__
# ---------------------------------------------------------------------------


class TestVersionMetadata:
    def test_version_string_present(self):
        assert isinstance(__version__, str)
        assert __version__ == v
        assert len(__version__.split(".")) == 3

    def test_version_info_tuple(self):
        assert isinstance(__version_info__, tuple)
        assert all(isinstance(n, int) for n in __version_info__)
        assert __version_info__ == tuple(int(n) for n in __version__.split("."))

    def test_metadata_fields(self):
        assert __author__
        assert "@" in __email__
        assert __license__ == "MIT"
        assert __url__.startswith("https://github.com/")
        assert __release_date__  # format checked by utils.py
        assert __release_name__


# ---------------------------------------------------------------------------
# colors
# ---------------------------------------------------------------------------


class TestColors:
    def test_colorize_wraps_with_color_and_reset(self):
        result = colorize("hello", Colors.GREEN)
        assert result.startswith(Colors.GREEN)
        assert result.endswith(Colors.RESET)
        assert "hello" in result

    def test_colorize_empty_string(self):
        result = colorize("", Colors.RED)
        assert Colors.RED in result
        assert Colors.RESET in result

    def test_color_constants_are_ansi_escape_codes(self):
        for name in ("RED", "GREEN", "CYAN", "RESET"):
            value = getattr(Colors, name)
            assert isinstance(value, str)
            assert value.startswith("\x1b[")


# ---------------------------------------------------------------------------
# LOGO
# ---------------------------------------------------------------------------


class TestLogo:
    def test_logo_is_non_empty(self):
        assert isinstance(LOGO, str)
        assert len(LOGO) > 100

    def test_logo_contains_version(self):
        # The version string is embedded inside the LOGO box.
        assert __version__ in LOGO

    def test_logo_contains_ansi_resets(self):
        # We expect at least one color reset so the terminal returns to normal.
        assert Colors.RESET in LOGO


# ---------------------------------------------------------------------------
# find_flac_files / find_non_flac_audio_files
# ---------------------------------------------------------------------------


class TestFileDiscovery:
    def test_find_flac_in_empty_dir(self, tmp_path):
        assert find_flac_files(tmp_path) == []
        assert find_non_flac_audio_files(tmp_path) == []

    def test_find_flac_picks_up_flac_only(self, tmp_path):
        (tmp_path / "song1.flac").touch()
        (tmp_path / "song2.FLAC").touch()  # case-sensitivity is platform-dependent
        (tmp_path / "song3.mp3").touch()
        (tmp_path / "song4.txt").touch()

        found = find_flac_files(tmp_path)
        names = {p.name.lower() for p in found}
        assert "song1.flac" in names
        # song3.mp3 must not be reported as FLAC
        assert all(p.suffix.lower() == ".flac" for p in found)

    def test_find_non_flac_picks_up_common_lossy(self, tmp_path):
        for name in ("a.mp3", "b.m4a", "c.aac", "d.ogg", "e.wma", "f.opus", "g.ape"):
            (tmp_path / name).touch()
        (tmp_path / "lossless.flac").touch()  # must NOT be reported as non-FLAC

        found = find_non_flac_audio_files(tmp_path)
        suffixes = {p.suffix.lower() for p in found}
        assert ".mp3" in suffixes
        assert ".m4a" in suffixes
        assert ".ogg" in suffixes
        assert ".flac" not in suffixes
        assert len(found) == 7

    def test_find_flac_recursive(self, tmp_path):
        nested = tmp_path / "artist" / "album"
        nested.mkdir(parents=True)
        (nested / "track01.flac").touch()
        (tmp_path / "top.flac").touch()

        found = find_flac_files(tmp_path)
        assert len(found) == 2
