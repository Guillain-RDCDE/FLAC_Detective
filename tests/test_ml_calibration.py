"""Tests for Rule 12 probability calibration (ml_calibration)."""

import json
import math

import pytest

from flac_detective.analysis.new_scoring.rules import ml_calibration as mc


@pytest.fixture(autouse=True)
def _reset_cache():
    """Each test starts from a clean module-level calibrator cache."""
    mc._reset_cache_for_tests()
    yield
    mc._reset_cache_for_tests()


def _point_to(tmp_path, payload):
    """Write a calibration JSON to tmp and point the module at it."""
    path = tmp_path / "cnn_v4_stereo.calibration.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    mc._CALIB_PATH = path  # type: ignore[attr-defined]
    mc._reset_cache_for_tests()
    return path


def test_identity_when_no_file(tmp_path):
    """With no calibration file, calibration is the identity and is_calibrated() is False."""
    mc._CALIB_PATH = tmp_path / "does_not_exist.json"  # type: ignore[attr-defined]
    mc._reset_cache_for_tests()
    assert not mc.is_calibrated()
    for p in (0.0, 0.1, 0.5, 0.9, 1.0):
        assert mc.calibrate_probability(p) == p


def test_platt_matches_formula(tmp_path):
    """Platt output equals sigmoid(a*logit(p)+b)."""
    a, b = 1.7, -0.4
    _point_to(tmp_path, {"method": "platt", "a": a, "b": b})
    assert mc.is_calibrated()
    for p in (0.2, 0.5, 0.73, 0.95):
        z = math.log(p / (1 - p))
        expected = 1.0 / (1.0 + math.exp(-(a * z + b)))
        assert mc.calibrate_probability(p) == pytest.approx(expected, abs=1e-9)


def test_platt_monotonic_and_clamped(tmp_path):
    """A positive-slope Platt mapping is increasing and stays within [0, 1]."""
    _point_to(tmp_path, {"method": "platt", "a": 2.0, "b": 0.3})
    xs = [i / 50 for i in range(51)]
    ys = [mc.calibrate_probability(x) for x in xs]
    assert all(0.0 <= y <= 1.0 for y in ys)
    assert all(ys[i] <= ys[i + 1] + 1e-12 for i in range(len(ys) - 1))


def test_isotonic_interpolation(tmp_path):
    """Isotonic mapping interpolates linearly between breakpoints and clamps at ends."""
    _point_to(tmp_path, {"method": "isotonic", "x": [0.0, 0.5, 1.0], "y": [0.0, 0.2, 1.0]})
    assert mc.calibrate_probability(0.0) == pytest.approx(0.0)
    assert mc.calibrate_probability(0.5) == pytest.approx(0.2)
    assert mc.calibrate_probability(0.25) == pytest.approx(0.1)  # midpoint of first segment
    assert mc.calibrate_probability(0.75) == pytest.approx(0.6)  # midpoint of second segment
    # Below/above the range clamps to the endpoints.
    assert mc.calibrate_probability(-0.3) == pytest.approx(0.0)
    assert mc.calibrate_probability(1.3) == pytest.approx(1.0)


def test_corrupt_file_falls_back_to_identity(tmp_path):
    """An unparseable / invalid calibration file degrades to identity, never raises."""
    path = tmp_path / "cnn_v4_stereo.calibration.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    mc._CALIB_PATH = path  # type: ignore[attr-defined]
    mc._reset_cache_for_tests()
    assert not mc.is_calibrated()
    assert mc.calibrate_probability(0.8) == 0.8


def test_unknown_method_is_identity(tmp_path):
    """An unknown method is rejected and falls back to identity."""
    _point_to(tmp_path, {"method": "magic", "a": 1.0})
    assert not mc.is_calibrated()
    assert mc.calibrate_probability(0.6) == 0.6
