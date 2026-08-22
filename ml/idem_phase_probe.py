#!/usr/bin/env python3
"""The idem read at the best grid phase — W4's instrument question, priced.

The finding this answers (received 2026-08-22)
-----------------------------------------------
Provir, FINDINGS_2026-08-21_idem_grid_lock (archived ml/exchange/): the idem
fixed point is GRID-LOCKED — the same decoded MP3, cropped k samples from the
start, reads R = 4.33 at k = 0/576/1152/2304 and ~7.0 at any other k. Period
576 samples (one MDCT granule), zero tolerance. Every fixture row either lab
holds was at phase 0 by construction (our arms are ffmpeg decodes of our own
tagged encodes); a lossless master has no grid so the lawful null is fair; but
a wild WAV that is a decoded transcode sits wherever its decoder and its edits
left it, and reads lawful at every phase but one. Our W4 (0/34 under the
phase-0 read, "the mastering chain destroys the fixed point") and his wild 27%
are phase-0 reads of populations that are not at phase 0.

Our instrument has the same blind spot: ml/mp3_idem_probe.py feeds the excerpt
at the file's native phase. The align() inside dist() aligns the decode to the
input AFTER the probe encode — it cannot move the encode grid.

What survives his correction, measured on his bench: family-locking (a LAME
file drops under the LAME probe at its true phase; Fraunhofer arms stay high
at every phase). What must be re-measured before any wild idem number is
quoted again: the lawful price under the same search ("min-over-576 on lawful
is a draws question until it is measured" — his words, adopted), and then the
wild 34. Our remaster arm is implicated too: its v1 chain (EQ + dynaudnorm +
alimiter) may have moved the grid by a constant filter delay, so the measured
"destruction" (idem AUC 0.98 -> 0.46) may be partly phase artifact.

The instrument
---------------
For one file: read R at the three canonical phases {0, 529, 47} on the full
60-s excerpt, then search all 576 phases on a short excerpt by d1 alone (one
probe roundtrip per phase — d1 is small only at the aligned phase of a
pre-transcoded input), then read the full R at the searched phase. The file's
phase-corrected read is the MINIMUM over those reads; the phase-0 read is
reported beside it. Probe = the shipped libmp3lame CBR-320 roundtrip, files
never pipes, unchanged from ml/mp3_idem_probe.py.

Populations
------------
    arms_control   8 direct lab mp3_320 arms (phase 0 by construction)
    genuine_bar   20 certified-genuine audit sources (the lawful repricing)
    wild_owner    34 owner-attested wild tracks (CD1+CD2, hash-gated corpus)
    remaster_v1   12 files of the v1 remaster arm (EQ+dynaudnorm+alimiter)

PREDICTIONS, registered before any measurement — results appended below
------------------------------------------------------------------------
    PS1  CONTROL. On the 8 direct arms the search does not manufacture
         signal: best-phase R within 0.5 dB of phase-0 R for >= 7/8 (their
         grid IS phase 0). Failure stops the campaign: the searcher is
         reading draws, not grids.
    PS2  LAWFUL REPRICING. No prediction on the lawful floor's value — it is
         a draws question and is MEASURED here. The re-cut bar is defined
         mechanically: the largest bar with 0/20 genuine best-phase reads
         below it (i.e. the genuine best-phase minimum).
    PS3  THE W4 REVISION. Under the re-cut bar, between 3 and 17 of the 34
         owner-attested wilds read below (phase-0 read was 0/34). Below 3:
         phase explains ~nothing of W4 and the mastering-destruction
         conclusion stands whole. Above 17: the destruction was mostly our
         instrument, and the layer anatomy (limiter -> fixed point) must be
         re-written. The band is registered wide because BOTH mechanisms are
         demonstrated: the grid lock is his measurement, the level/limiter
         destruction is ours (remaster arm v1 was measured at its own true
         phase if its chain preserved the grid — which PS4 decides).
    PS4  REMASTER ARM. If the v1 chain moved the grid (constant FIR/filter
         delay), the search finds best phase != 0 on >= 6/12 files and the
         arm's median best-phase R drops at least 1.0 dB below its median
         phase-0 R. If best phase stays 0 on >= 10/12, the chain preserved
         the grid and the measured destruction was physical, not phase.

Same honesty rule as every campaign: predictions commit before the run;
results are appended, never rewritten; a wrong premise is part of the result.
--------------------------------------------------------------------------------
RESULTS
(not yet run)
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mp3_idem_probe import EXCERPT_SEC, dist, mp3_idem, require_ffmpeg, roundtrip  # noqa: E402

CANONICAL = [0, 529, 47]  # trimmed decode - untrimmed decode (1105 mod 576) - decoder-delay-only
PERIOD = 576
SEARCH_SEC = 3.0

POPULATIONS = {
    "arms_control": (["C:/Users/loutr/audit_corpus/fake/mp3_320/*.flac"], 8),
    "genuine_bar": (["C:/Users/loutr/audit_corpus/authentic/*.flac"], 20),
    "wild_owner": (
        [
            "C:/Users/loutr/wild53/21-08-26/Original Hardcore The Nu Breed (2004)/CD1 Darren Styles/*.wav",
            "C:/Users/loutr/wild53/21-08-26/Original Hardcore The Nu Breed (2004)/CD2 Dougal/*.wav",
        ],
        34,
    ),
    "remaster_v1": (["C:/Users/loutr/remaster_arm/*.flac"], 12),
}


def crop(audio: np.ndarray, k: int) -> np.ndarray:
    return audio[k:] if audio.ndim == 1 else audio[k:, :]


def d1_at_phase(audio: np.ndarray, rate: int, k: int, ffmpeg: str) -> float:
    """One roundtrip at phase k on the short excerpt; d1 alone."""
    x = crop(audio, k)
    with tempfile.TemporaryDirectory() as tmp:
        b = roundtrip(x, rate, Path(tmp), "p", ffmpeg)
    d1, _ = dist(x, b, rate)
    return d1


def phase_read(audio: np.ndarray, rate: int, ffmpeg: str, step: int = 1) -> dict:
    """Canonical reads + full 576-phase d1 search + full R at the searched phase."""
    reads = {}
    for k in CANONICAL:
        r, _, _ = mp3_idem(crop(audio, k), rate, ffmpeg)
        reads[k] = r
    n_search = int(SEARCH_SEC * rate) + PERIOD * 3
    short = crop(audio, 0)[:n_search] if audio.ndim == 1 else audio[:n_search, :]
    d1s = {}
    for k in range(0, PERIOD, step):
        v = d1_at_phase(short, rate, k, ffmpeg)
        if np.isfinite(v):
            d1s[k] = v
    k_best = min(d1s, key=lambda k: d1s[k]) if d1s else 0
    if k_best not in reads:
        r, _, _ = mp3_idem(crop(audio, k_best), rate, ffmpeg)
        reads[k_best] = r
    finite = {k: v for k, v in reads.items() if np.isfinite(v)}
    best_k = min(finite, key=lambda k: finite[k]) if finite else 0
    return {
        "R_phase0": reads.get(0, float("nan")),
        "R_best": reads.get(best_k, float("nan")),
        "best_phase": best_k,
        "searched_phase": k_best,
        "searched_d1": d1s.get(k_best, float("nan")),
    }


def measure_file(path: str, ffmpeg: str, step: int) -> Optional[dict]:
    try:
        info = sf.info(path)
        data, rate = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if data.size == 0 or rate not in (44100, 48000):
        return None
    try:
        row = phase_read(data, rate, ffmpeg, step=step)
    except Exception as exc:
        print(f"  ECHEC {Path(path).name}: {exc}", flush=True)
        return None
    row["path"] = Path(path).name
    row["rate"] = rate
    return row


def selftest(ffmpeg: str) -> int:
    """Known answer first: a phase-0 transcode cropped by 137 samples must be
    found at phase 576-137 = 439, and read far closer to the fixed point there
    than at phase 0. This is Provir's grid-lock experiment, reproduced."""
    from mp3_idem_probe import RATE, _tonal_mix

    audio = _tonal_mix(20.0)
    with tempfile.TemporaryDirectory() as tmp:
        transcode = roundtrip(audio, RATE, Path(tmp), "st", ffmpeg)
    shifted = transcode[137:]
    row = phase_read(shifted, RATE, ffmpeg, step=1)
    expect = (PERIOD - 137) % PERIOD
    print(
        f"selftest: R0={row['R_phase0']:.2f} Rbest={row['R_best']:.2f} "
        f"searched={row['searched_phase']} (attendu {expect})"
    )
    ok = row["searched_phase"] == expect and row["R_best"] < row["R_phase0"] - 1.0
    print("selftest:", "OK" if ok else "ECHEC")
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--populations", nargs="*", default=list(POPULATIONS))
    parser.add_argument("--step", type=int, default=1, help="phase search step (1 = exact; the period has zero tolerance)")
    args = parser.parse_args(argv)
    ffmpeg = require_ffmpeg()
    if args.selftest:
        return selftest(ffmpeg)
    if not args.out:
        parser.error("--out est requis hors --selftest")
    out = Path(args.out)

    done = set()
    if out.exists():
        with open(out, newline="", encoding="utf-8") as fh:
            done = {(r["population"], r["path"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja mesurees", flush=True)

    fields = ["population", "path", "rate", "R_phase0", "R_best", "best_phase", "searched_phase", "searched_d1"]
    with open(out, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not done:
            writer.writeheader()
        for pop in args.populations:
            patterns, limit = POPULATIONS[pop]
            paths: List[str] = []
            for pattern in patterns:
                paths.extend(sorted(glob.glob(pattern)))
            seen = 0
            for path in dict.fromkeys(paths):
                if seen >= limit:
                    break
                if (pop, Path(path).name) in done:
                    seen += 1
                    continue
                row = measure_file(path, ffmpeg, args.step)
                if row is None:
                    continue
                row["population"] = pop
                writer.writerow(row)
                fh.flush()
                seen += 1
                print(
                    f"[{pop} {seen}/{limit}] {row['path'][:48]:48} "
                    f"R0={row['R_phase0']:.2f} Rbest={row['R_best']:.2f} "
                    f"phase={row['best_phase']}",
                    flush=True,
                )
            print(f"{pop}: {seen} mesures", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
