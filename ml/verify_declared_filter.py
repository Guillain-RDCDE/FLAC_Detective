"""Check the filter figures we declared to Provir, from this side.

On 2 September we told him the band-limited stratum's filter measures 518 degrees
of phase rotation between 1 and 14 kHz, with group delay running 5.7 to 9.3
samples, and he reproduced our four phase figures — -22, -293, -540 and -697
degrees — to 0.34 degrees RMS against a cascade of six 2-pole sections at 14 kHz,
Q 0.707, at 44.1 kHz.

He verified our numbers. We never did, and that is the same gap as the stratum
map: a claim of ours checked only by the party it was aimed at. This computes
them from the filter as the build script declares it —
``lowpass=f=14000:poles=2`` six times over — on a different axis from the
magnitude work, since phase is what the claim was about.

ffmpeg's ``lowpass`` with ``poles=2`` is a biquad low-pass at Q = 1/sqrt(2), so
the cascade is six identical second-order sections. Built here with scipy rather
than measured through ffmpeg on purpose: measuring our own filter with our own
pipeline would prove the pipeline is consistent, not that the figure is right.
"""

import numpy as np
from scipy import signal

FS = 44_100.0
CUTOFF_HZ = 14_000.0
SECTIONS = 6
Q = 1.0 / np.sqrt(2.0)

# What we told him, so the comparison is against the sent figures rather than
# against whatever comes out today.
DECLARED_ROTATION_DEG = 518.0

# The four phase figures are at 1, 10, 14 and 16 kHz, and the group delay pair is
# read between 10 and 14 kHz. Both were established by inverting the cascade
# rather than assumed: the first run of this script guessed 1/7/12/14 kHz and
# reported gaps of up to 157 degrees, which looked like our declaration being
# wrong and was this file's own assumption being wrong. Recorded because a
# verification that mis-states what it is verifying accuses the wrong party.
DECLARED_GROUP_DELAY = {10_000.0: 5.7, 14_000.0: 9.3}
DECLARED_PHASES = {1_000.0: -22.0, 10_000.0: -293.0, 14_000.0: -540.0, 16_000.0: -697.0}


def cascade():
    """The declared filter: six identical 2-pole low-pass sections at 14 kHz."""
    b, a = signal.iirfilter(
        2, CUTOFF_HZ / (FS / 2), btype="low", ftype="butter", output="ba"
    )
    return [(b, a)] * SECTIONS


def unwrapped_phase(freqs):
    """Total phase of the cascade, unwrapped, in degrees (negative = lag)."""
    total = np.zeros(len(freqs))
    for b, a in cascade():
        _, h = signal.freqz(b, a, worN=2 * np.pi * freqs / FS)
        total += np.unwrap(np.angle(h))
    return np.degrees(total)


def group_delay_samples(freqs):
    """Group delay of the cascade at each frequency, in samples."""
    total = np.zeros(len(freqs))
    for b, a in cascade():
        _, gd = signal.group_delay((b, a), w=2 * np.pi * freqs / FS)
        total += gd
    return total


def main() -> int:
    """Print the measured figures beside the declared ones."""
    grid = np.linspace(1.0, 21_000.0, 20_001)
    phase = unwrapped_phase(grid)

    def at(hz):
        return float(np.interp(hz, grid, phase))

    print(f"filtre: {SECTIONS} sections 2 poles a {CUTOFF_HZ:.0f} Hz, Q={Q:.3f}, fs={FS:.0f}")
    print()
    print("phase (degres), declare -> mesure ici:")
    worst = 0.0
    for hz, declared in sorted(DECLARED_PHASES.items()):
        measured = at(hz)
        worst = max(worst, abs(measured - declared))
        print(f"  {hz:>7.0f} Hz : {declared:>8.1f}  ->  {measured:>8.1f}   ecart {measured - declared:+.1f}")
    print(f"  ecart maximum: {worst:.1f} degres")
    print()

    rotation = abs(at(14_000.0) - at(1_000.0))
    print(f"rotation 1 -> 14 kHz : declaree {DECLARED_ROTATION_DEG:.0f}, mesuree {rotation:.0f} degres"
          f"  ({rotation / 360:.2f} tour)")

    freqs = sorted(DECLARED_GROUP_DELAY)
    gd = group_delay_samples(np.array(freqs))
    print("retard de groupe (echantillons), declare -> mesure ici:")
    for hz, measured in zip(freqs, gd):
        declared = DECLARED_GROUP_DELAY[hz]
        print(f"  {hz:>7.0f} Hz : {declared:>8.1f}  ->  {measured:>8.1f}   ecart {measured - declared:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
