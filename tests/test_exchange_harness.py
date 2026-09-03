"""The harness that produced the numbers we published was outside every gate.

`src/` has five gates. The exchange harness had none: `score_v3_return.py`
carries a ten-case self-test that only ran when someone typed it, and the two
translation scripts — the ones that turned his key into our scorer's format and
his verdict tiers into ours — had no tests at all. A mistake in either would have
been invisible to CI and would have travelled in a letter.

This is the same defect the exchange keeps finding, one level up: excellent
checks on the engine, none on the instrument that generates the evidence.

The cases below are chosen so each can FAIL. A translation test that only feeds
correct input proves the script runs, not that it is right, so every one of these
either feeds something wrong and demands a refusal, or feeds something whose
correct answer is known and different from the obvious one.
"""

import csv
import json
import sys
from pathlib import Path

import pytest

ML = Path(__file__).resolve().parent.parent / "ml"
sys.path.insert(0, str(ML))

import prepare_setA_return  # noqa: E402
import prepare_setB_key  # noqa: E402
import run_engine_on_set  # noqa: E402
import score_v3_return  # noqa: E402

# --------------------------------------------------------------------------
# The scorer's own self-test, which CI never ran
# --------------------------------------------------------------------------


def test_the_scorer_selftest_passes():
    """Ten fabricated cases with known answers. Now a gate, not a habit.

    It covers the criteria, the two amendments about blanks and errors, the
    untestable-direction rule and the per-stratum split. If any of them breaks,
    this fails in CI instead of staying green until someone runs the script by
    hand.
    """
    assert score_v3_return.selftest() == 0


def test_a_direction_needs_rows_on_both_sides():
    held, line = score_v3_return.direction("K2", 3, 3, 0, 30, "band hurts more")
    assert held is None and "NOT TESTABLE" in line


def test_two_zeros_have_no_direction():
    held, line = score_v3_return.direction("K2", 0, 20, 0, 20, "band hurts more")
    assert held is None and "either side" in line


def test_a_real_direction_is_read():
    held, _ = score_v3_return.direction("K2", 15, 20, 5, 20, "band hurts more")
    assert held is True
    held, _ = score_v3_return.direction("K2", 5, 20, 15, 20, "band hurts more")
    assert held is False


# --------------------------------------------------------------------------
# His key CSV -> the scorer's JSON
# --------------------------------------------------------------------------

CLASSES = [
    "genuine",
    "mp3_320_lame",
    "mp3_320_pretag",
    "mp3_V0_lame",
    "aac_256",
    "opus_256",
    "vorbis_q10",
    "atrac3plus",
]


def _key_csv(path: Path, per_class: int = 35, vinyl_stems: int = 3) -> Path:
    """A key in his shipped shape: 8 classes x per_class, stems shared by 8 files."""
    rows = []
    file_no = 0
    for stem_index in range(per_class):
        stem = f"S{stem_index + 1:02d}"
        bucket = "VINYL_TRANSFER" if stem_index < vinyl_stems else "OWNER_CD_RIP"
        for cls in CLASSES:
            file_no += 1
            rows.append(
                {
                    "id": f"b{file_no:03d}.wav",
                    "class": cls,
                    "source_stem": stem,
                    "source_bucket": bucket,
                    "basis": "test",
                }
            )
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_his_key_becomes_the_scorers_format(tmp_path, capsys):
    csv_path = _key_csv(tmp_path / "key.csv")
    out = tmp_path / "key.json"
    assert prepare_setB_key.main(["--csv", str(csv_path), "--out", str(out)]) == 0

    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["labels"]) == 280
    # The id loses its extension, because the scorer joins on the stem.
    assert "b001" in data["labels"] and "b001.wav" not in data["labels"]
    assert len(data["strata"]) == 35
    band = [s for s, v in data["strata"].items() if v.startswith("band_limited")]
    assert len(band) == 3, "the three vinyl sources are the declared stratum"


def test_a_short_key_is_refused(tmp_path):
    """A key with the wrong row count is refused rather than scored partially."""
    csv_path = _key_csv(tmp_path / "key.csv", per_class=34)
    with pytest.raises(SystemExit, match="272 rows"):
        prepare_setB_key.main(["--csv", str(csv_path), "--out", str(tmp_path / "k.json")])


def test_an_unbalanced_key_is_refused(tmp_path):
    """280 rows but not 8 x 35 — the shape he declared has to hold, not just the total."""
    csv_path = _key_csv(tmp_path / "key.csv")
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    rows[0]["class"] = "genuine"  # 36 genuine, 34 of another
    for row in rows:
        if row["class"] == "mp3_320_lame":
            row["class"] = "genuine"
            break
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(SystemExit, match="classes are not"):
        prepare_setB_key.main(["--csv", str(csv_path), "--out", str(tmp_path / "k.json")])


def test_one_source_in_two_buckets_is_refused(tmp_path):
    """A stem that is vinyl on one row and not on another cannot be stratified."""
    csv_path = _key_csv(tmp_path / "key.csv")
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    rows[0]["source_bucket"] = "OWNER_CD_RIP"  # S01 is VINYL on its other seven rows
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(SystemExit, match="two buckets"):
        prepare_setB_key.main(["--csv", str(csv_path), "--out", str(tmp_path / "k.json")])


# --------------------------------------------------------------------------
# His verdict tiers -> ours, and the dash that means two things
# --------------------------------------------------------------------------


def _our_key(path: Path) -> Path:
    labels = {}
    arms = ["genuine", "mp3_320", "mp3_V0", "vorbis_q8", "aac_ff256", "opus_256", "mp2_256"]
    for index, arm in enumerate(arms, 1):
        labels[f"f{index:03d}"] = {"label": arm, "source_slug": f"s{index:03d}"}
    path.write_text(json.dumps({"labels": labels}), encoding="utf-8")
    return path


def _his_return(path: Path, rows) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["file", "engine_verdict", "mp3_lattice", "vorbis_detector"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _run_translation(tmp_path, rows):
    key = _our_key(tmp_path / "key.json")
    verdicts = _his_return(tmp_path / "his.csv", rows)
    out_a, out_b = tmp_path / "a.csv", tmp_path / "b.csv"
    code = prepare_setA_return.main(
        [
            "--verdicts",
            str(verdicts),
            "--key",
            str(key),
            "--out-a",
            str(out_a),
            "--out-b",
            str(out_b),
        ]
    )
    assert code == 0

    def read(path):
        with open(path, newline="", encoding="utf-8") as fh:
            return {r["file"]: r["verdict"] for r in csv.DictReader(fh)}

    return read(out_a), read(out_b)


def test_his_tiers_map_to_ours_as_he_declared(tmp_path):
    """His tiers map to ours exactly as he declared them.

    UPSCALE and LOSSY_MASTER convict; SUSPECT only signals. Conflating the two
    would turn every flag into a conviction and inflate his rate.
    """
    rows = [
        {
            "file": "f001.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
        {
            "file": "f002.flac",
            "engine_verdict": "UPSCALE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
        {
            "file": "f003.flac",
            "engine_verdict": "LOSSY_MASTER",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
        {
            "file": "f004.flac",
            "engine_verdict": "SUSPECT",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
    ]
    col_a, _ = _run_translation(tmp_path, rows)
    assert col_a["f001"] == "AUTHENTIC"
    assert col_a["f002"] == "FAKE_CERTAIN"
    assert col_a["f003"] == "FAKE_CERTAIN"
    assert col_a["f004"] == "SUSPICIOUS"


def test_an_unknown_tier_is_refused_rather_than_guessed(tmp_path):
    rows = [
        {
            "file": "f001.flac",
            "engine_verdict": "PROBABLY?",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        }
    ]
    with pytest.raises(SystemExit, match="unmapped tier"):
        _run_translation(tmp_path, rows)


def test_the_dash_is_read_by_class_and_not_by_symbol(tmp_path):
    """The whole point of the second column's translation.

    Identical input — a dash from both instruments — must mean a MISS on a row
    his instruments cover, and NO CLAIM on a row they do not. Reading the symbol
    instead of the class is how a coverage limit gets published as a detection
    rate, which is what the scorer was amended twice to prevent.
    """
    rows = [
        {
            "file": "f002.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
        {
            "file": "f004.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
        {
            "file": "f005.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
        {
            "file": "f007.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        },
    ]
    _, col_b = _run_translation(tmp_path, rows)
    assert col_b["f002"] == "AUTHENTIC", "mp3_320 is covered by the lattice: a dash is a miss"
    assert col_b["f004"] == "AUTHENTIC", "vorbis_q8 is covered: a dash is a miss"
    assert col_b["f005"] == "-", "aac has no instrument: a dash is not a miss"
    assert col_b["f007"] == "-", "mp2 has no instrument either"


def test_a_fire_on_a_genuine_row_is_kept_as_a_false_positive(tmp_path):
    """His one false positive must survive translation, not be filtered as noise."""
    rows = [
        {
            "file": "f001.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "FIRES",
        }
    ]
    _, col_b = _run_translation(tmp_path, rows)
    assert col_b["f001"] == "FAKE_CERTAIN"


def test_a_verdict_for_a_file_outside_the_key_is_refused(tmp_path):
    rows = [
        {
            "file": "ghost.flac",
            "engine_verdict": "GENUINE",
            "mp3_lattice": "-",
            "vorbis_detector": "-",
        }
    ]
    with pytest.raises(SystemExit, match="not in the key"):
        _run_translation(tmp_path, rows)


# --------------------------------------------------------------------------
# The guard that refused to score a rotten file
# --------------------------------------------------------------------------


def _frozen_set(tmp_path: Path, corrupt: str = "") -> Path:
    """A tiny set with a real manifest, optionally damaged the way Dropbox damaged one."""
    import hashlib

    root = tmp_path / "set"
    (root / "audio").mkdir(parents=True)
    lines = []
    for index in range(3):
        payload = f"audio-{index}".encode() * 10
        path = root / "audio" / f"f{index}.flac"
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        lines.append(f"{digest}  audio/f{index}.flac  {len(payload)}")
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    target = root / "audio" / "f1.flac"
    if corrupt == "bytes":  # same length, different content — the v2 incident
        target.write_bytes(b"x" * target.stat().st_size)
    elif corrupt == "truncated":  # the 2026-09-02 incident, 50 KB short
        target.write_bytes(target.read_bytes()[:-5])
    elif corrupt == "missing":
        target.unlink()
    return root


def test_an_intact_set_is_accepted(tmp_path):
    files = run_engine_on_set.verify_manifest(_frozen_set(tmp_path))
    assert len(files) == 3


def test_wrong_bytes_at_the_same_size_stop_the_run(tmp_path):
    with pytest.raises(SystemExit, match="do not match the manifest"):
        run_engine_on_set.verify_manifest(_frozen_set(tmp_path, corrupt="bytes"))


def test_a_truncated_file_stops_the_run(tmp_path):
    with pytest.raises(SystemExit, match="do not match the manifest"):
        run_engine_on_set.verify_manifest(_frozen_set(tmp_path, corrupt="truncated"))


def test_a_missing_file_stops_the_run(tmp_path):
    with pytest.raises(SystemExit, match="do not match the manifest"):
        run_engine_on_set.verify_manifest(_frozen_set(tmp_path, corrupt="missing"))


def test_a_set_without_a_manifest_is_refused(tmp_path):
    (tmp_path / "audio").mkdir()
    with pytest.raises(SystemExit, match="refusing to score an unverified set"):
        run_engine_on_set.verify_manifest(tmp_path)
