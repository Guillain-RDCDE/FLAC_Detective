#!/usr/bin/env python3
"""Layer 3, measured on the wild bytes: what fills the cliff above the MP3 cutoff?

Where this question comes from
-------------------------------
`ml/remaster_arm.py` decomposed the lab-to-wild gap into layers, each proven by
the instrument it kills: (1) limiting destroys the codec fixed point; (2) a
decorrelated noise floor kills the side-channel and temporal tells; and (3) an
UNMODELLED layer masks the spectral cliff — the v2 arm still gets signaled at
55 % by the spectral/CNN families while the wild reads 8.8 %. The registration
forbade tuning the simulator further, so layer 3 is characterised here the only
honest way left: by measuring the wild bytes themselves.

The observable: cliff depth. Welch magnitude (16384), reference = median dB in
10–14 kHz, and the depth of the 20.5–21.8 kHz band below that reference — the
region a LAME 320 lowpass empties on a direct transcode. Whatever the wild
mastering chain puts THERE is layer 3 by definition.

Registered before the run:

    L1  The owner-attested wilds' median cliff depth is at least 10 dB
        SHALLOWER than the direct arm's — layer 3 is real energy above the
        cutoff, not a measurement artifact.
    L2  Cliff depth separates wild-owner from direct at AUC >= 0.80.
    L3  The v2 noise floor (-72 dBFS) did NOT fill the cliff: v2's median
        depth stays within 6 dB of direct's. (This is why A1[v2] failed — the
        engine's spectral families still see a naked cliff the wild does not
        show.)

Populations: genuine (40), direct mp3_320 (40), remastered_v2 (40),
wild-owner (34), wild-eye (19, separated per the standing rule).

MEASURED 2026-08-21 — ALL THREE L-PREDICTIONS FAILED, and the reversal is the
finding of the day:

    population         n   med depth   p10     p90
    genuine           40      -19.1   -37.5    -0.8
    direct            40      -56.7   -68.2   -37.5
    remastered_v2     40      -36.0   -41.6    -8.8
    wild_owner        34      -63.9   -68.2   -60.0   <- DEEPER than direct
    wild_eye          19      -58.0   -62.3   -55.1

    L1 FAILED (gap -7.2 dB, wrong sign) · L2 FAILED (AUC 0.25, wrong side) ·
    L3 FAILED (v2 filled the cliff by 20 dB — our -72 dB noise dominated the
    empty band and manufactured an upscale-like artifact the CNN over-reads).

THE CLIFF IS NOT MASKED. The wild walls are cleaner and deeper than our own
lab transcodes', in the same grid cells (median cell 19,750–20,250, zero files
in Rule 1's near-Nyquist mute zone). So "layer 3 masks the cliff" is DEAD, and
the follow-up dissection (analyze_spectrum inputs + Rule 1 source, same
session) found what actually silences the engine on the wild 34 — three Rule 1
admission gates, each calibrated on the direct-lab population:

  (a) VARIANCE GATE vs THE GRID: Rule 1 exits when cutoff_std > 100 Hz, but
      detect_cutoff quantizes to 250 Hz cells — a perfectly stable wall near a
      cell boundary oscillates one cell and reads std ≈ 118 Hz (measured on
      '01 Sunlight': std 117.9, wall rock-solid). The gate's threshold is
      SMALLER than the instrument's quantization step.
  (b) THE 20,000-EXACT EXCEPTION: a wall snapped to the 20,000 Hz cell is
      discarded as "FFT rounding" whenever energy_ratio > 1e-6 — and the wild
      chain's press/console noise guarantees energy_ratio > 1e-6 on every
      file (measured: 8.9e-6 to 3.4e-5). Two of the first five CD1 walls sit
      exactly there.
  (c) THE CONTAINER-BITRATE RANGE: mp3_ranges[320] = (700, 1050) kbps was
      calibrated for MP3-decoded-to-FLAC. A WAV reads 1411 kbps — outside the
      range BY FORMAT, so every WAV is structurally beyond Rule 1's reach —
      and dense material FLAC-compresses above 1050 and exits too.

Plus the CNN: the v2 residual was carried 100 % by cnn (22/22) while the wild
reads cnn on 3/53 — out-of-distribution, as Provir's own CNN audit warned.

So the true anatomy of 8.8 %: layers 1-2 (fixed point; side/temporal) are
killed by the mastering chain as demonstrated in ml/remaster_arm.py — and the
SPECTRAL silence is not the chain at all, it is our own admission gates tuned
on lab material. None of (a)-(c) is retouched here: each gate protects real
authentic populations, and moving any of them changes verdicts — that is the
v1.12 engine campaign, to be priced against the full 800-file audit corpus
with the wild53 as the held-out bench.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.spectrum import _welch_magnitude_db  # noqa: E402
from edge_width_probe import auc  # noqa: E402

AUDIT = Path(r"C:\Users\loutr\audit_corpus")
V2 = Path(r"C:\Users\loutr\remaster_arm_v2")
WILD = Path(r"C:\Users\loutr\wild53\21-08-26\Original Hardcore The Nu Breed (2004)")

POPULATIONS = {
    "genuine": [AUDIT / "authentic"],
    "direct": [AUDIT / "fake" / "mp3_320"],
    "remastered_v2": [V2],
    "wild_owner": [WILD / "CD1 Darren Styles", WILD / "CD2 Dougal"],
    "wild_eye": [WILD / "CD3 Bonus (Mixed by Styles and Dougal)"],
}
LIMIT = 40

REF_LO, REF_HI = 10000.0, 14000.0
CLIFF_LO, CLIFF_HI = 20500.0, 21800.0
EXCERPT_SEC = 30.0


def cliff_depth(path: Path) -> Optional[float]:
    """Median dB of the 20.5-21.8 kHz band, relative to the 10-14 kHz reference."""
    try:
        info = sf.info(str(path))
        data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if rate != 44100:
        return None
    mono = np.asarray(data if data.ndim == 1 else np.mean(data, axis=1), dtype=np.float64)
    freq, mag = _welch_magnitude_db(mono, rate)
    if freq is None:
        return None
    ref = (freq >= REF_LO) & (freq <= REF_HI)
    band = (freq >= CLIFF_LO) & (freq <= CLIFF_HI)
    if not ref.any() or not band.any():
        return None
    return float(np.median(mag[band]) - np.median(mag[ref]))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("ml/wild53_cliff.csv"))
    args = parser.parse_args(argv)

    rows: List[dict] = []
    for population, dirs in POPULATIONS.items():
        n = 0
        for folder in dirs:
            for path in sorted(list(folder.glob("*.flac")) + list(folder.glob("*.wav"))):
                if n >= LIMIT and population in ("genuine", "direct", "remastered_v2"):
                    break
                depth = cliff_depth(path)
                if depth is not None:
                    rows.append(
                        {
                            "population": population,
                            "track": path.name,
                            "cliff_depth_db": f"{depth:.1f}",
                        }
                    )
                    n += 1
        print(f"{population}: {n} mesures", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["population", "track", "cliff_depth_db"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} lignes -> {args.out}\n")

    vals = {
        p: np.array([float(r["cliff_depth_db"]) for r in rows if r["population"] == p])
        for p in POPULATIONS
    }
    print(f"{'population':16}{'n':>4}{'med depth dB':>14}{'p10':>8}{'p90':>8}")
    for population, v in vals.items():
        if v.size:
            print(
                f"{population:16}{v.size:>4}{np.median(v):>14.1f}"
                f"{np.percentile(v, 10):>8.1f}{np.percentile(v, 90):>8.1f}"
            )

    direct, owner, v2 = vals["direct"], vals["wild_owner"], vals["remastered_v2"]
    if direct.size and owner.size:
        gap = float(np.median(owner) - np.median(direct))
        l1 = gap >= 10.0
        l2 = auc(owner, direct) >= 0.80
        print(
            f"\nL1  wild-owner >= 10 dB shallower than direct: "
            f"{'HELD' if l1 else 'FAILED'} (gap {gap:+.1f} dB)"
        )
        print(
            f"L2  depth separates owner vs direct at AUC >= 0.80: "
            f"{'HELD' if l2 else 'FAILED'} (AUC {auc(owner, direct):.2f})"
        )
    if direct.size and v2.size:
        l3 = abs(float(np.median(v2) - np.median(direct))) < 6.0
        print(
            f"L3  v2 noise did NOT fill the cliff: {'HELD' if l3 else 'FAILED'} "
            f"(v2 {np.median(v2):.1f} vs direct {np.median(direct):.1f} dB)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
