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
_MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "cnn_v4_stereo.ts.pt"

# Mel-spec config — MUST match ml/extract_features.py used at training time.
_SAMPLE_RATE = 44100  # MUST match ml/extract_features.py SAMPLE_RATE
_SEGMENT_SEC = 10.0
_N_MELS = 128
_N_FFT = 2048
_HOP = 512

# Reliability gate (v0.13). A false-positive audit on 11 234 certified-authentic
# FLACs (ml/analyze_false_positives.py, ml/README.md) showed the model is most
# error-prone on band-limited material: for a source that rolls off below ~7 kHz
# (baroque, historical, acoustic), an MP3 transcode removes almost nothing, so
# authentic and fake look alike. Below this rolloff Rule 12 abstains (contributes
# 0) and defers to the heuristic rules.
#
# v0.14 stereo update: the v4 model reads the mid AND side channels, so it is far
# less blind here than the mono v3 was (real-world FP at rolloff<4k dropped from
# 57% to 25%). The gate is kept because it still helps — on the same audit, v4
# specificity is 87.6% un-gated vs 93.5% with this <7 kHz gate — and it remains
# faithful to the "protect authentic files first" philosophy: the band-limited
# detection given up is the least-harmful case (a 320 kbps MP3 of a 5 kHz-bandwidth
# source is sonically transparent). Measured on the file, so it works at inference.
_ROLLOFF_GATE_HZ = 7000.0


def _load_model():
    """Load the TorchScript model once, cache it. Returns None if unavailable."""
    global _MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL
    _MODEL_LOAD_ATTEMPTED = True

    try:
        import torch
    except ImportError:
        logger.debug("Rule 12: torch not installed; skipping (install with [ml] extra)")
        return None

    if not _MODEL_PATH.is_file():
        logger.debug(f"Rule 12: model not found at {_MODEL_PATH}; skipping")
        return None

    try:
        _MODEL = torch.jit.load(str(_MODEL_PATH), map_location="cpu")
        _MODEL.eval()
        logger.info(f"Rule 12: loaded CNN model from {_MODEL_PATH}")
    except Exception as e:
        logger.warning(f"Rule 12: failed to load model: {e}")
        _MODEL = None
    return _MODEL


def _compute_mel(filepath: Path):
    """Compute the 2-channel model input and 95% spectral rolloff from one decode.

    Returns ``(mel, rolloff_hz)`` where ``mel`` is a (1, 2, n_mels, T) mid+side
    mel-spec — each channel normalised to [-1, 1] — or ``(None, None)`` on failure.

    The v4 model is stereo: channel 0 is the mid (L+R)/2, channel 1 the side
    (L-R)/2 where MP3 joint-stereo coding leaves a fingerprint the mono v3 was
    blind to. Audio is quantised to 16-bit first so the model keys on that
    fingerprint rather than the authentic-vs-transcode bit-depth difference (the
    confound this avoids — see ml/extract_features_stereo.py). The rolloff (from
    the mid channel) drives the reliability gate and reuses the same decode.
    """
    try:
        import librosa
        import numpy as np
    except ImportError:
        return None, None
    try:
        duration = librosa.get_duration(path=str(filepath))
        offset = max(0.0, (duration - _SEGMENT_SEC) / 2)
        y, sr = librosa.load(
            str(filepath), sr=_SAMPLE_RATE, offset=offset, duration=_SEGMENT_SEC, mono=False
        )
        if y.ndim == 1:
            mid, side = y, np.zeros_like(y)
        else:
            mid, side = 0.5 * (y[0] + y[1]), 0.5 * (y[0] - y[1])

        target_len = int(_SAMPLE_RATE * _SEGMENT_SEC)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=_N_FFT)
        rolloff = 0.0
        chans = []
        for ci, sig in enumerate((mid, side)):
            if len(sig) < target_len:
                sig = np.pad(sig, (0, target_len - len(sig)))
            else:
                sig = sig[:target_len]
            sig = np.round(sig * 32768.0) / 32768.0  # 16-bit quant (matches training)
            mag = np.abs(librosa.stft(sig, n_fft=_N_FFT, hop_length=_HOP))
            if ci == 0:
                # 95% spectral rolloff from the mid channel's averaged spectrum.
                cumulative = np.cumsum(mag.mean(axis=1))
                if cumulative[-1] > 0:
                    rolloff = float(freqs[np.searchsorted(cumulative, 0.95 * cumulative[-1])])
            mel = librosa.feature.melspectrogram(S=mag**2, sr=sr, n_mels=_N_MELS, fmax=sr // 2)
            mel_db = librosa.power_to_db(mel, ref=np.max).astype(np.float32)
            mn, mx = mel_db.min(), mel_db.max()
            chans.append(2 * (mel_db - mn) / max(mx - mn, 1e-6) - 1.0)
        # Shape (1, 2, n_mels, T)
        return np.stack(chans, axis=0)[None, :, :, :], rolloff
    except Exception as e:
        logger.debug(f"Rule 12: mel extraction failed for {filepath}: {e}")
        return None, None


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

    mel, rolloff = _compute_mel(filepath)
    if mel is None:
        return 0, []

    # Reliability gate: below this rolloff the CNN is a coin flip on authentic vs
    # transcode (see _ROLLOFF_GATE_HZ). Abstain and let the heuristic rules decide.
    if rolloff < _ROLLOFF_GATE_HZ:
        logger.info(
            f"RULE 12: abstaining (rolloff {rolloff:.0f} Hz < {_ROLLOFF_GATE_HZ:.0f} Hz, "
            f"band-limited — CNN unreliable in this regime)"
        )
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
    # v2 model (ResNet-18 pretrained, trained on full-spectrum 44.1 kHz
    # features) is well-calibrated: balanced accuracy 81%, specificity 80%
    # on authentic inputs. We can use the natural 0.5 decision threshold
    # without the conservative-threshold hack v1 needed.
    #
    # Score mapping (linear, 0.5..0.95 → 0..30, saturating above 0.95):
    THRESHOLD = 0.5
    SATURATION = 0.95

    if p_transcoded < THRESHOLD:
        return 0, []
    if p_transcoded >= SATURATION:
        score = 30
        confidence_str = "very high"
    else:
        score = int(round((p_transcoded - THRESHOLD) / (SATURATION - THRESHOLD) * 30))
        if p_transcoded >= 0.8:
            confidence_str = "high"
        elif p_transcoded >= 0.65:
            confidence_str = "moderate"
        else:
            confidence_str = "low"

    reason = (
        f"R12: CNN classifier flags transcode "
        f"(p={p_transcoded:.2f}, confidence={confidence_str}, +{score}pts)"
    )
    logger.info(f"RULE 12: ML classifier score {score} (p={p_transcoded:.3f})")
    return score, [reason]
