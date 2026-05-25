"""Rule 12: CNN-based transcode detection.

Loads a TorchScript classifier (`cnn_v1.ts.pt`) bundled with the package.
For each input, it computes a mel-spectrogram of a 10-second segment near the
middle of the file, runs it through the CNN, and adds a score proportional
to the model's confidence that the file is transcoded.

PyTorch and librosa are optional dependencies. If they aren't installed, or
if the model file isn't bundled / accessible, this rule is a no-op: it
returns ``(0, [])`` without raising. The classic 11-rule heuristic pipeline
continues to work unchanged.

Install the ML support with::

    pip install "flac-detective[ml]"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Module-level model cache: only load the model once per process.
_MODEL = None
_MODEL_LOAD_ATTEMPTED = False
_MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "cnn_v1.ts.pt"

# Mel-spec config — MUST match ml/extract_features.py used at training time.
_SAMPLE_RATE = 22050
_SEGMENT_SEC = 10.0
_N_MELS = 128
_N_FFT = 2048
_HOP = 512


def _load_model():
    """Load the TorchScript model once, cache it. Returns None if unavailable."""
    global _MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL
    _MODEL_LOAD_ATTEMPTED = True

    try:
        import torch  # noqa: F401
    except ImportError:
        logger.debug("Rule 12: torch not installed; skipping (install with [ml] extra)")
        return None

    if not _MODEL_PATH.is_file():
        logger.debug(f"Rule 12: model not found at {_MODEL_PATH}; skipping")
        return None

    try:
        import torch
        _MODEL = torch.jit.load(str(_MODEL_PATH), map_location="cpu")
        _MODEL.eval()
        logger.info(f"Rule 12: loaded CNN model from {_MODEL_PATH}")
    except Exception as e:
        logger.warning(f"Rule 12: failed to load model: {e}")
        _MODEL = None
    return _MODEL


def _compute_mel(filepath: Path):
    """Compute a (1, 1, n_mels, T) normalised mel-spectrogram, or None on failure."""
    try:
        import numpy as np
        import librosa
    except ImportError:
        return None
    try:
        duration = librosa.get_duration(path=str(filepath))
        offset = max(0.0, (duration - _SEGMENT_SEC) / 2)
        y, sr = librosa.load(str(filepath), sr=_SAMPLE_RATE,
                             offset=offset, duration=_SEGMENT_SEC, mono=True)
        target_len = int(_SAMPLE_RATE * _SEGMENT_SEC)
        if len(y) < target_len:
            y = np.pad(y, (0, target_len - len(y)))
        else:
            y = y[:target_len]
        mel = librosa.feature.melspectrogram(
            y=y, sr=sr, n_fft=_N_FFT, hop_length=_HOP, n_mels=_N_MELS, fmax=sr // 2,
        )
        mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
        mn, mx = mel_db.min(), mel_db.max()
        rng = max(mx - mn, 1e-6)
        mel_db = 2 * (mel_db - mn) / rng - 1.0
        # Shape (1, 1, n_mels, T)
        return mel_db[None, None, :, :]
    except Exception as e:
        logger.debug(f"Rule 12: mel extraction failed for {filepath}: {e}")
        return None


def apply_rule_12_ml_classifier(filepath: Path) -> Tuple[int, List[str]]:
    """Apply Rule 12: ML-based transcode detection.

    Args:
        filepath: Path to the FLAC file under analysis.

    Returns:
        Tuple of (score_contribution, reason_strings). Score is in [0, 30]:
            * 0  if the model is unavailable, or it predicts "authentic"
            * up to +30 when the model is highly confident the file is
              transcoded (confidence ≥ 0.95)
        Confidence between 0.5 and 0.95 is mapped linearly to [0, 25].
    """
    model = _load_model()
    if model is None:
        return 0, []

    mel = _compute_mel(filepath)
    if mel is None:
        return 0, []

    try:
        import torch
        x = torch.from_numpy(mel)
        with torch.no_grad():
            logits = model(x)
            probs = torch.softmax(logits, dim=1)[0]
        p_transcoded = float(probs[1].item())
    except Exception as e:
        logger.warning(f"Rule 12: inference failed: {e}")
        return 0, []

    # Map confidence -> score contribution.
    #
    # The v1 model has a notable skew: trained on a 1:7 authentic-to-transcoded
    # ratio, it overestimates the transcoded class on authentic inputs (95%
    # false positives at the natural 0.5 threshold on a balanced test set).
    # To compensate without retraining, we use a conservative threshold of
    # 0.85 — meaning Rule 12 only fires when the model is highly confident.
    # This trades some recall for much better specificity, which matches the
    # rest of FLAC Detective's "protect authentic files first" philosophy.
    THRESHOLD = 0.85
    SATURATION = 0.99

    if p_transcoded < THRESHOLD:
        return 0, []
    if p_transcoded >= SATURATION:
        score = 30
        confidence_str = "very high"
    else:
        score = int(round((p_transcoded - THRESHOLD) / (SATURATION - THRESHOLD) * 25))
        confidence_str = "high"

    reason = (f"R12: CNN classifier flags transcode "
              f"(p={p_transcoded:.2f}, confidence={confidence_str}, +{score}pts)")
    logger.info(f"RULE 12: ML classifier score {score} (p={p_transcoded:.3f})")
    return score, [reason]
