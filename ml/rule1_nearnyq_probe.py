"""Which of Rule 1's four near-Nyquist guards actually silences what.

RETRACTED 2026-08-21. The frequency below came from Provir and Jamie Dodd withdrew
it himself: it is one reading of one file by one edge-finder, early 3.9x LAME at
-b 320 applies no lowpass at all (so it measured the SOURCE, not the encoder), and
503 of his 1,180 lawful files already read an edge at or above it. He also disclosed
fusing two different 8 Hz figures — 8.1 Hz store-vs-recreation and ~8 Hz
build-to-build — so "five builds within 8 Hz of a frequency" is unsupported.

The conclusion survives and is stronger: 11 of his 17 real 2009 MP3s wall below
21,479 Hz while 6 have no wall to 22,023, and 28 of his 75 lawful masters sit above
21,570. No edge POSITION separates the populations. See ml/edge_width_probe.py for
what replaced it.

Kept below as written, because a probe's stated premise is part of its result.

Jamie Dodd's exhibit (Scott Brown, "Goodbye My Friend") falsifies a claim written
into this rule in plain English: "MP3s never have cutoffs above 21.5 kHz (even 320
kbps tops out around 20.5-21 kHz)". He owns the CD the store download also comes
from. The CD runs clean to Nyquist; the store file walls at 21,562.8 Hz; and the
CD's OWN audio through LAME 3.92 -b 320 reproduces that wall to 8.1 Hz. He
re-measured five era builds today: 3.90.3, 3.92, 3.93.1r, 3.93.1w32 and a 2002
daily all land within 8 Hz of each other at -b 320, in both -m s and -m j. Only the
later builds move down (3.96.1 -> 19,842.8; 3.97/3.98.4 -> 19,999.0).

So the entire pre-3.96 LAME era walls ABOVE the threshold this rule says MP3s never
reach, and four stacked guards close that door:

    1. cutoff >= 0.95 * Nyquist (20,947.5 Hz)      -> return
    2. cutoff >  21,500 Hz                          -> return
    3. MP3_SIGNATURES tops out at 21,500            -> estimate 0
    4. for a 320 estimate, cutoff >= 0.94 * Nyquist (20,727 Hz) -> return

Guard 4 binds first for 320, at 20,727 Hz. Guards 2 and 3 are unreachable behind
guard 1 and cannot fire at all.

And the instrument that could actually settle this zone already exists in the file.
``compute_residual_floor_db`` separates a digital-silence brickwall from an analog
rolloff at ROC AUC 0.95, and Rule 1 consults it — at line 155, AFTER guard 4 has
returned at line 143. It is described in its own comment as the "near-Nyquist 320
kbps wall-hardness gate" and it can never see a file above 94 % of Nyquist.

That is the same defect class as our Rule 14 reachability bug and Jamie's six
mumbling witnesses: an instrument that is never called for the population it was
built for.

This probe measures, per arm:
  - the cutoff distribution,
  - which guard fires first,
  - and whether the residual floor separates genuine from transcode in the zone the
    guards currently own.

Nothing is changed on the strength of the argument alone. Rule 1 awards +50, and
every false conviction this project has ever shipped came from Rule 1 + Rule 3 at
+50 each, so the genuine arm decides.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")

from flac_detective.analysis.new_scoring.bitrate import (  # noqa: E402
    calculate_real_bitrate,
    estimate_mp3_bitrate,
)
from flac_detective.analysis.spectrum import analyze_spectrum  # noqa: E402

NYQ = 22050.0
GUARD1 = 0.95 * NYQ  # 20947.5
GUARD4 = 0.94 * NYQ  # 20727.0
TABLE_TOP = 21500.0


def which_guard(cutoff: float, std: float, est: int) -> str:
    """The first guard that returns, in Rule 1's own order."""
    if cutoff >= GUARD1:
        return "1_nyquist95"
    if cutoff > TABLE_TOP:
        return "2_dead_code"
    if std > 100.0:
        return "3_variance"
    if est == 0:
        return "4_no_signature"
    if est == 320 and cutoff >= GUARD4:
        return "5_nyquist94_320"
    return "-_reaches_residual"


def collect(pattern: str, limit: int) -> list:
    rows = []
    for path in sorted(glob.glob(pattern))[:limit]:
        try:
            cutoff, energy_ratio, std, residual = analyze_spectrum(Path(path), 30)
        except Exception:
            continue
        if cutoff is None:
            continue
        est = estimate_mp3_bitrate(float(cutoff))
        try:
            import soundfile as sf

            dur = sf.info(path).duration
            container = calculate_real_bitrate(Path(path), dur)
        except Exception:
            container = float("nan")
        rows.append(
            {
                "cutoff": float(cutoff),
                "std": float(std),
                "residual": float(residual),
                "container": float(container),
                "guard": which_guard(float(cutoff), float(std), est),
            }
        )
    return rows


ARMS = {
    "genuine": ("C:/Users/loutr/audit_corpus/authentic/*.flac", 60),
    "genuine_wild": ("C:/Users/loutr/wild_authentic/**/*.flac", 60),
    "mp3_320": ("C:/Users/loutr/audit_corpus/fake/mp3_320/*.flac", 40),
    "mp3_V0": ("C:/Users/loutr/audit_corpus/fake/mp3_V0/*.flac", 40),
    "aac_ff320": ("C:/Users/loutr/audit_corpus/fake/aac_ff320/*.flac", 40),
}

data = {}
for name, (pattern, limit) in ARMS.items():
    rec = pattern.endswith("**/*.flac")
    paths = sorted(glob.glob(pattern, recursive=rec))[:limit]
    rows = []
    for path in paths:
        try:
            cutoff, energy_ratio, std, residual = analyze_spectrum(Path(path), 30)
        except Exception:
            continue
        if cutoff is None:
            continue
        est = estimate_mp3_bitrate(float(cutoff))
        try:
            import soundfile as sf

            container = calculate_real_bitrate(Path(path), sf.info(path).duration)
        except Exception:
            container = float("nan")
        rows.append(
            {
                "cutoff": float(cutoff),
                "std": float(std),
                "residual": float(residual),
                "container": float(container),
                "guard": which_guard(float(cutoff), float(std), est),
            }
        )
    data[name] = rows
    print(f"{name}: {len(rows)} fichiers mesures", flush=True)

print("\n=== distribution des cutoffs ===")
for name, rows in data.items():
    if not rows:
        continue
    c = np.array([r["cutoff"] for r in rows])
    print(
        f"{name:14} n={c.size:3d}  median {np.median(c):8.0f}  "
        f">=20727 {int((c >= GUARD4).sum()):3d}  >=20947 {int((c >= GUARD1).sum()):3d}"
    )

print("\n=== quel garde-fou tire en premier ===")
guards = sorted({r["guard"] for rows in data.values() for r in rows})
print(f"{'arm':14}" + "".join(f"{g[:16]:>18}" for g in guards))
for name, rows in data.items():
    if not rows:
        continue
    line = f"{name:14}"
    for g in guards:
        line += f"{sum(1 for r in rows if r['guard'] == g):>18d}"
    print(line)

print("\n=== residu dans la zone que les gardes possedent (cutoff >= 20727) ===")
for name, rows in data.items():
    zone = [r["residual"] for r in rows if r["cutoff"] >= GUARD4 and np.isfinite(r["residual"])]
    if not zone:
        print(f"{name:14} aucun fichier dans la zone (ou residu NaN)")
        continue
    z = np.array(zone)
    print(
        f"{name:14} n={z.size:3d}  median {np.median(z):7.1f} dB  "
        f"p05 {np.percentile(z, 5):7.1f}  p95 {np.percentile(z, 95):7.1f}  "
        f"<=-55dB {int((z <= -55).sum()):3d}"
    )

print("\nLecture : si le residu separe (transcodes tres negatifs, authentiques hauts),")
print("le garde-fou 5 peut ceder la place a l'instrument calibre qui existe deja.")
