"""Probability calibration for Rule 12 (the CNN transcode classifier).

The CNN outputs a softmax probability ``p_raw`` that a file is transcoded. That
number is a *confidence*, not a *calibrated probability*: a model can be 0.90
"sure" and yet be right only 80% of the time at that operating point (modern
CNNs trained with cross-entropy are routinely over-confident). The scoring
pipeline, the high-confidence WARNING floor (``ml_classifier._WARNING_FLOOR_P``)
and any "87% chance this is a transcode" message the UI shows all read ``p`` as
if it were a real probability — so an un-calibrated ``p`` makes those thresholds
mean something different from what they claim.

This module maps ``p_raw`` to a calibrated ``p_cal`` using parameters fitted on
a held-out labelled set (``ml/calibrate_model.py``) and bundled next to the
TorchScript model as ``cnn_v4_stereo.calibration.json``. Two methods are
supported, both monotonic (they never reorder files, only rescale confidence):

* **platt** — a logistic fit on the logit of ``p``:
  ``p_cal = sigmoid(a * logit(p_raw) + b)``. Two parameters, robust on small
  calibration sets. This is the default.
* **isotonic** — a non-parametric monotonic step function stored as paired
  ``(x, y)`` breakpoints; ``p_cal`` is linearly interpolated between them.
  More flexible, needs more calibration data to be trustworthy.

If the calibration file is absent or unreadable, calibration is the **identity**
(``p_cal == p_raw``) — exactly the pre-calibration behaviour — so shipping
without a fitted file is safe and changes nothing. Apply-time uses only the
standard library (``json``, ``math``, ``bisect``); fitting (offline, in
``ml/``) may use numpy/scipy.
"""

from __future__ import annotations

import bisect
import json
import logging
import math
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Bundled calibration file, sitting next to cnn_v4_stereo.ts.pt. Optional.
_CALIB_PATH = Path(__file__).resolve().parents[3] / "models" / "cnn_v4_stereo.calibration.json"

# Process-level cache: load (and parse) the calibration file at most once.
_CALIBRATOR: "Optional[_Calibrator]" = None
_LOAD_ATTEMPTED = False

# Clamp p away from {0, 1} before taking a logit, so logit() stays finite.
_EPS = 1e-6


def _sigmoid(z: float) -> float:
    """Numerically stable logistic sigmoid."""
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _logit(p: float) -> float:
    """Inverse sigmoid, with ``p`` clamped to (0, 1) to stay finite."""
    p = min(1.0 - _EPS, max(_EPS, p))
    return math.log(p / (1.0 - p))


class _Calibrator:
    """A fitted probability mapping. Construct via :func:`_from_dict`."""

    def __init__(self, method: str, params: dict) -> None:
        self.method = method
        self._params = params
        if method == "platt":
            self._a = float(params["a"])
            self._b = float(params["b"])
        elif method == "isotonic":
            xs = [float(v) for v in params["x"]]
            ys = [float(v) for v in params["y"]]
            if len(xs) != len(ys) or len(xs) < 2:
                raise ValueError("isotonic calibration needs >=2 paired (x, y) points")
            # Sort by x so bisect works and interpolation is well-defined.
            order = sorted(range(len(xs)), key=lambda i: xs[i])
            self._xs: List[float] = [xs[i] for i in order]
            self._ys: List[float] = [ys[i] for i in order]
        else:
            raise ValueError(f"unknown calibration method: {method!r}")

    def apply(self, p_raw: float) -> float:
        """Map a raw probability to its calibrated value, clamped to [0, 1]."""
        if self.method == "platt":
            out = _sigmoid(self._a * _logit(p_raw) + self._b)
        else:  # isotonic
            out = self._interp(p_raw)
        return min(1.0, max(0.0, out))

    def _interp(self, x: float) -> float:
        """Piecewise-linear interpolation over the isotonic breakpoints."""
        xs, ys = self._xs, self._ys
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x)
        x0, x1 = xs[i - 1], xs[i]
        y0, y1 = ys[i - 1], ys[i]
        if x1 == x0:
            return y1
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _from_dict(data: dict) -> "_Calibrator":
    """Build a calibrator from a parsed calibration-file dict (raises on bad data)."""
    method = str(data.get("method", "")).lower()
    return _Calibrator(method, data)


def _load_calibrator() -> "Optional[_Calibrator]":
    """Load the bundled calibrator once; return None if absent/unreadable/invalid."""
    global _CALIBRATOR, _LOAD_ATTEMPTED
    if _LOAD_ATTEMPTED:
        return _CALIBRATOR
    _LOAD_ATTEMPTED = True

    if not _CALIB_PATH.is_file():
        logger.debug("Rule 12 calibration: no file at %s; using identity", _CALIB_PATH)
        return None
    try:
        with open(_CALIB_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _CALIBRATOR = _from_dict(data)
        logger.info(
            "Rule 12 calibration: loaded %s mapping from %s",
            _CALIBRATOR.method,
            _CALIB_PATH.name,
        )
    except Exception as exc:  # pragma: no cover - defensive; identity is the safe fallback
        logger.warning(
            "Rule 12 calibration: failed to load %s (%s); using identity", _CALIB_PATH, exc
        )
        _CALIBRATOR = None
    return _CALIBRATOR


def calibrate_probability(p_raw: float) -> float:
    """Return the calibrated probability for a raw CNN softmax probability.

    Falls back to the identity (``p_cal == p_raw``) when no calibration file is
    bundled, so callers can use this unconditionally.

    Args:
        p_raw: The model's raw P(transcoded), in [0, 1].

    Returns:
        Calibrated P(transcoded), in [0, 1]. Monotonic in ``p_raw``.
    """
    calibrator = _load_calibrator()
    if calibrator is None:
        return p_raw
    try:
        return calibrator.apply(p_raw)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Rule 12 calibration: apply failed (%s); using raw p", exc)
        return p_raw


def is_calibrated() -> bool:
    """True if a calibration mapping is bundled and loaded (else identity is used)."""
    return _load_calibrator() is not None


def _reset_cache_for_tests() -> None:
    """Clear the module-level cache (test helper; not part of the public API)."""
    global _CALIBRATOR, _LOAD_ATTEMPTED
    _CALIBRATOR = None
    _LOAD_ATTEMPTED = False
