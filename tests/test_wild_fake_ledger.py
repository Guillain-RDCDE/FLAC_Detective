"""The wild ledger's adjudication schema, pinned at the three gaps the wild53 found.

Provir's 53-file feature ledger (2026-08-20) was the first real material this
schema ever met, and it failed three ways before a row was entered: no basis for
an owner's attestation, no way to record a ruling made by extension, and no way
to record a selection pipeline. These tests pin the repairs — and pin that a
group-scope ruling without its examination note is refused, because 19 rulings
presented as 19 examinations is precisely the silent lie the field exists to
prevent.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest

_LEDGER_PATH = Path(__file__).resolve().parent.parent / "ml" / "wild_fake_ledger.py"
_SPEC = importlib.util.spec_from_file_location("wild_fake_ledger", _LEDGER_PATH)
ledger = importlib.util.module_from_spec(_SPEC)
sys.modules["wild_fake_ledger"] = ledger
_SPEC.loader.exec_module(ledger)


def _seeded_ledger(tmp_path, monkeypatch):
    """One undecided record, in a ledger file the test owns."""
    path = tmp_path / "ledger.json"
    monkeypatch.setattr(ledger, "LEDGER", path)
    key = "a" * 64
    ledger.save(
        {
            key: {
                "sha256": key,
                "filename": "x.flac",
                "bytes": 1,
                "source": "test",
                "added": "2026-08-20T00:00:00Z",
                "adjudication": {
                    "label": "undecided",
                    "basis": None,
                    "selection": None,
                    "referee": False,
                    "by": None,
                    "at": None,
                    "note": None,
                },
                "verdicts": [],
            }
        }
    )
    return key


def _adjudicate(key, **kw):
    args = argparse.Namespace(
        sha=key[:8],
        label="fake",
        basis="tracker_staff",
        selection="systematic",
        scope="file",
        by="test",
        note=None,
    )
    for name, value in kw.items():
        setattr(args, name, value)
    return ledger.cmd_adjudicate(args)


def test_owner_attestation_is_a_basis_and_referee_grade(tmp_path, monkeypatch):
    key = _seeded_ledger(tmp_path, monkeypatch)
    assert "owner_attestation" in ledger.BASES
    assert _adjudicate(key, basis="owner_attestation") == 0
    row = ledger.load()[key]["adjudication"]
    assert row["basis"] == "owner_attestation"
    assert row["referee"] is True


def test_selection_pipeline_is_accepted_link_by_link(tmp_path, monkeypatch):
    key = _seeded_ledger(tmp_path, monkeypatch)
    assert _adjudicate(key, selection="detector+human_eye") == 0
    assert ledger.load()[key]["adjudication"]["selection"] == "detector+human_eye"


def test_unknown_selection_link_is_refused(tmp_path, monkeypatch):
    key = _seeded_ledger(tmp_path, monkeypatch)
    assert _adjudicate(key, selection="detector+vibes") == 1
    assert ledger.load()[key]["adjudication"]["label"] == "undecided"


def test_group_scope_without_examination_note_is_refused(tmp_path, monkeypatch):
    key = _seeded_ledger(tmp_path, monkeypatch)
    assert _adjudicate(key, scope="group", note=None) == 1
    assert ledger.load()[key]["adjudication"]["label"] == "undecided"


def test_group_scope_with_note_is_recorded(tmp_path, monkeypatch):
    key = _seeded_ledger(tmp_path, monkeypatch)
    assert _adjudicate(key, scope="group", note="5 of 19 tracks examined, one master per disc") == 0
    row = ledger.load()[key]["adjudication"]
    assert row["scope"] == "group"
    assert "5 of 19" in row["note"]


def test_a_chain_is_tainted_by_its_most_sensory_link(tmp_path, monkeypatch, capsys):
    """detector+human_eye must land in the eyeball warning population."""
    key = _seeded_ledger(tmp_path, monkeypatch)
    assert _adjudicate(key, selection="detector+human_eye") == 0
    records = ledger.load()
    records[key]["verdicts"] = [
        {"version": "t", "at": "t", "verdict": "AUTHENTIC", "score": 0, "families": []}
    ]
    ledger.save(records)
    assert ledger.cmd_status(argparse.Namespace()) == 0
    out = capsys.readouterr().out
    assert "every fake here was chosen by a human's eyes or ears" in out


@pytest.mark.parametrize("basis", sorted(ledger.REFEREE_BASES))
def test_every_referee_basis_is_a_known_basis(basis):
    assert basis in ledger.BASES
