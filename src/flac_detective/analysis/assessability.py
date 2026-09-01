"""Whether the accusing instruments could run at all on this file.

``AUTHENTIC`` used to mean two different things: the instruments ran and found
nothing, and the instruments could not run. The second is not a finding, it is
the absence of one, and reporting it in the same word as a clean bill of health
is the typed-absence defect of v1.13.1 one level up — at the verdict rather than
at a float.

Registered first, with its populations and its refusal clause, in
``ml/exchange/ABSTENTION_REGISTRATION_2026-09-01.md``, and amended the same day
when its own control population caught it: a **mono** file is assessable. It
loses the stereo and temporal witnesses, but the spectral family, the CNN and the
MDCT statistic all run on it, and the corroboration barrier already handles
having fewer witnesses. Being unable to hear one instrument is not being unable
to hear.

Measured price on 1,248 real files — 80 authentic, 880 arms, the 288 of exchange
set A: **not one abstains**. That is recorded rather than buried: nothing here
repairs an observed failure on real material, and no later document may cite it
as if it had. What it removes is a verdict the engine had no standing to issue,
on files it was never able to read — of which the shipped corpora contain none,
and a user's disk contains plenty.

What this does NOT do: it gives the engine no instrument for a codec it cannot
measure. A file transcoded through ATRAC3+, or any format outside the panel, has
every rule run on it and every rule find nothing. That is a genuine limit and
stays one; an abstention here would be claiming to know something.
"""

from __future__ import annotations

import math
from typing import Optional

from .new_scoring.stereo_image import FFT_SIZE as _SI_FFT_SIZE
from .new_scoring.stereo_image import HOP as _SI_HOP
from .new_scoring.stereo_image import MIN_FRAMES as _SI_MIN_FRAMES

# Below this sample rate there is no content above 16 kHz at all, which is the
# band every accusing rule reads. Declared rather than swept: it is the edge of
# the instruments' domain, not a tuning parameter. Rule 11 does not merely say
# nothing on an 8 kHz file — its bandpass design raises, and the error is caught
# and logged, so the file arrives at the verdict looking clean.
MIN_ASSESSABLE_RATE_HZ = 32000

# A file with no signal offers nothing for any instrument to be right or wrong
# about. Its spectrum still yields a cutoff, which is exactly why the cutoff
# alone cannot answer this question.
SILENCE_FLOOR_RMS = 1e-6

# The frame-based witness's own arithmetic, not a round number.
#
# Rule 15 needs ``MIN_FRAMES`` frames of a ``FFT_SIZE``-point STFT hopped by
# ``HOP``. Deriving the floor from those three constants means it cannot drift
# away from the instrument it describes, and it cannot be quietly tuned.
#
# This replaces a 10-second threshold I chose because it sounded reasonable. The
# real figure is 17,408 samples — **0.39 s at 44.1 kHz**, twenty-five times
# smaller. Two existing tests caught it by failing: they build 2-second synthetic
# WAVs and assert AUTHENTIC, and a 2-second file is assessable by the spectral
# family, the CNN and the MDCT statistic. The tests were right and the constant
# was wrong. See the second amendment of 1 September.
MIN_ASSESSABLE_SAMPLES = _SI_FFT_SIZE + _SI_HOP * (_SI_MIN_FRAMES - 1)


def unassessable_reason(
    sample_rate: Optional[int],
    duration_s: Optional[float],
    cutoff_freq: Optional[float],
    rms: Optional[float],
) -> Optional[str]:
    """Why this file could not be assessed, or ``None`` if it could.

    Every argument is optional because every one of them can be genuinely
    unknown, and an unknown is never treated as a zero. The order is the order
    the reason is worth reporting in: the domain first, then the signal, then
    the instruments.

    Args:
        sample_rate: Sample rate in Hz, or None if unreadable.
        duration_s: Duration in seconds, or None if unreadable.
        cutoff_freq: Detected spectral cutoff, or None/NaN if unanalysable.
        rms: Root-mean-square level of a sampled segment, or None if not measured.

    Returns:
        A short, specific sentence naming the condition, or None. The sentence is
        surfaced to the user: an abstention that does not say why is worse than a
        wrong answer, because it cannot be argued with.
    """
    if sample_rate is None:
        return "the sample rate could not be read"
    if sample_rate < MIN_ASSESSABLE_RATE_HZ:
        return (
            f"sampled at {sample_rate} Hz, below {MIN_ASSESSABLE_RATE_HZ} Hz — "
            "there is no band here for the transcode rules to read"
        )
    if rms is not None and rms <= SILENCE_FLOOR_RMS:
        return "there is no measurable signal in this file"
    if cutoff_freq is None or math.isnan(cutoff_freq) or cutoff_freq <= 0:
        return "the spectrum could not be analysed, so no rule had an input"
    if duration_s is not None and duration_s * sample_rate < MIN_ASSESSABLE_SAMPLES:
        return (
            f"only {duration_s:.2f} s long — fewer than the {MIN_ASSESSABLE_SAMPLES} samples "
            "the frame-based witness needs for a single reading"
        )
    return None
