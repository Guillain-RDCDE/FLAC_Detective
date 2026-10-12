"""The version is written once; everything else reads it or is checked against it.

`src/flac_detective/__version__.py` is the single source. pyproject.toml reads it
at build time, and Commitizen keeps its own record, which the release workflow
compares with the tag. These tests catch a drift before a tag does.
"""

import re
from importlib.metadata import version
from pathlib import Path

from flac_detective.__version__ import __version__

PYPROJECT = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")


def _section(name: str) -> str:
    match = re.search(rf"^\[{re.escape(name)}\]\s*$(.*?)(?=^\[|\Z)", PYPROJECT, re.M | re.S)
    assert match, f"[{name}] missing from pyproject.toml"
    return match.group(1)


def test_project_version_is_read_from_the_source_file():
    project = _section("project")
    assert not re.search(r"^version\s*=", project, re.M), "a static version is back in [project]"
    assert re.search(r'^dynamic\s*=\s*\[[^\]]*"version"', project, re.M)
    dynamic = _section("tool.setuptools.dynamic")
    assert 'attr = "flac_detective.__version__.__version__"' in dynamic


def test_commitizen_record_matches_the_source_file():
    match = re.search(r'^version\s*=\s*"([^"]+)"', _section("tool.commitizen"), re.M)
    assert match, "[tool.commitizen] has no version"
    assert match.group(1) == __version__


def test_installed_metadata_matches_the_source_file():
    assert version("flac-detective") == __version__
