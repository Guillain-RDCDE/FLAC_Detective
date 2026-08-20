#!/usr/bin/env python3
"""Does width fail because width is useless here, or because the anchor wanders?

The question, and whose it is
------------------------------
v1.11.4 shipped a deliberately narrow null: "width does not work bolted onto OUR
edge-finder", with the sentence "this says nothing about whether it works in
Provir's, where it does". Jamie Dodd corrected the premise on 2026-08-20: his
instrument is not one instrument either. His edge comes from an 8192-point FFT
(5.38 Hz/bin, p90 across 5 s chunks, whole file, ref -15 dB) and his width from a
32768-point FFT (1.35 Hz/bin, mean power, first 90 s, ref -30 dB), the width search
starts at edge - 300 Hz, and his gate admits edges with a standard deviation up to
160 Hz. Width quoted to 1.35 Hz from an anchor that wanders by 160. His fire test
(width < 600 Hz) is blunt enough that the wander "probably" does not reach it, and
he flagged the "probably" as unmeasured.

So the better-specified question, his words, "yours as much as mine": **does width
fail bolted onto ANY separately-derived edge?** The only way to answer it is an
instrument with no separate edge: find the transition and measure it on the SAME
curve, same FFT, same statistic, in one pass. That is this probe.

The finding that preceded it: our edge grid
--------------------------------------------
Answering his two verification requests exposed the same cause for both.
``detect_cutoff`` scans 250 Hz slices upward from 14,000 Hz
(``CUTOFF_SCAN_START``/``TRANCHE_SIZE``) and returns a slice boundary — every
slice-method cutoff lands on the grid **14,000 + k x 250 Hz**. Hence:

* the Musepack medians 16,000 / 17,750 / 18,750 are grid points. "Exactly 18,750"
  is our grid cell, not mpcenc's 48 kHz ``Max_Band`` constant — the 48 kHz ladder
  steps by 750 Hz and our grid by 250, so they share every third rung and
  collisions are guaranteed, not meaningful;
* the three "perfect brickwall" genuine files at 21,000 / 21,000 / 20,250 Hz sit
  on grid points too. Two files "agreeing to the Hz" means: same 250 Hz cell.

And the widths those three read — 2.69 Hz (exactly one bin), 0.0 Hz, 18.8 Hz — are
at or below the instrument's own floor (a synthetic perfect wall reads ~11 Hz under
the same smoothing). A 0.0 is producible without any wall at all: the bolted search
window opens at ``cutoff - 250``, and if the true edge sits lower than the anchor
thinks, the first searched bin is already below both levels and the width
degenerates to zero. Anchor wander manufacturing perfect walls is exactly his
incoherence thesis, so those three files are re-measured here, off-grid, at two
resolutions, before anyone adjudicates them.

The instrument
--------------
One curve per resolution: Welch magnitude (Hann, 50 % overlap) at nfft 16384
(2.69 Hz/bin at 44.1 kHz) and nfft 65536 (0.67 Hz/bin). Reference = median dB in
the 10-14 kHz band (same as the bolted version). Curve smoothed by 9 bins (same as
the width half of the bolted version). Then, with no detect_cutoff anywhere:

    edge  = highest frequency still at or above (ref - 6 dB)
    width = distance from there to the first bin at or below (ref - 30 dB)

Sentinels, never numbers: "no_edge" (nothing above ref-6 dB past 14 kHz — bass
concentration, nothing to measure), "no_wall" (the spectrum holds to the top),
"no_floor" (a rolloff that fades without reaching ref-30 dB — not a width, and not
a zero either). Taking the LAST crossing makes an interior dip that recovers not an
edge, which is what "wall" means: after it, nothing comes back.

Predictions, registered before the corpus run, in the exchange's convention
---------------------------------------------------------------------------
    P1  self-anchored width AUC stays below 0.70 on every arm at nfft 16384 —
        the 269 Hz-kernel fix already changed nothing, so the null is expected to
        be a property of the corpus, not of the bolting.
    P2  of the three brickwall genuine files, at least two read as degeneracies
        (bolted search window already below the -6 dB level at its first bin) or
        fail to reproduce as a stable width at both resolutions; none survives as
        a resolution-stable sub-25 Hz wall.
    P3  at least 90 % of bolted slice-method cutoffs sit exactly on the
        14,000 + k x 250 grid; self-anchored edges do not (beyond the ~1 % a
        2.69 Hz bin grid coincidentally allows).

Being wrong on P1 is the useful outcome: it would mean the bolting was the failure
and width earns a calibration pass. Being wrong on P2 promotes the three files to
serious adjudication candidates. Being wrong on P3 means the grid reading of
``detect_cutoff`` is itself mistaken.

Results are appended below this line AFTER the corpus run, never above it, and
the predictions above are left untouched whatever they say.
--------------------------------------------------------------------------------
(not yet run)

Usage::

    python ml/edge_width_selfanchored_probe.py --selftest   # synthetic knowns
    python ml/edge_width_selfanchored_probe.py              # corpus run
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.spectrum import (  # noqa: E402
    WIDTH_SMOOTH_BINS,
    _welch_magnitude_db,
    detect_cutoff_detailed,
)
from flac_detective.config import spectral_config  # noqa: E402

from edge_width_probe import ARMS, EXCERPT_SEC, auc  # noqa: E402

START_DROP_DB = 6.0  # same as EDGE_START_DROP_DB in spectrum.py
GRID_START = float(spectral_config.CUTOFF_SCAN_START)
GRID_STEP = float(spectral_config.TRANCHE_SIZE)

# The three genuine files that read as perfect walls under the bolted instrument
# (v1.11.4). Forced into the run and reported individually.
ADJUDICATION_CANDIDATES = [
    "C:/Users/loutr/audit_corpus/authentic/"
    "007-07-Wax-Tailor-Positively-inclined-featuring-main.flac",
    "C:/Users/loutr/wild_authentic/bt2026-08-11__01 Stand.flac",
    "C:/Users/loutr/wild_authentic/bt2026-08-11__02 Run-Around.flac",
]


def self_anchored(
    freq: np.ndarray, mag_db: np.ndarray, samplerate: int
) -> Tuple[str, float, float]:
    """(status, edge_hz, width_hz) from one curve, no separate edge-finder.

    status: "ok" | "no_edge" | "no_wall" | "no_floor". edge/width are NaN unless
    they are measurements ("no_floor" keeps its edge: the edge was found, the
    width was not).
    """
    nyquist = samplerate / 2.0
    if samplerate <= 48000:
        ref_low = float(spectral_config.REFERENCE_FREQ_LOW)
        ref_high = float(spectral_config.REFERENCE_FREQ_HIGH)
    else:
        scale = samplerate / 44100.0
        ref_low = float(spectral_config.REFERENCE_FREQ_LOW) * scale
        ref_high = float(spectral_config.REFERENCE_FREQ_HIGH) * scale

    ref_mask = (freq >= ref_low) & (freq <= ref_high)
    if not np.any(ref_mask):
        return "no_edge", float("nan"), float("nan")
    reference = float(np.median(mag_db[ref_mask]))

    above = freq > ref_high
    freq_h = freq[above]
    mag_h = mag_db[above]
    if len(mag_h) > WIDTH_SMOOTH_BINS:
        from scipy.ndimage import uniform_filter1d

        mag_h = uniform_filter1d(mag_h, size=WIDTH_SMOOTH_BINS)

    start_level = reference - START_DROP_DB
    end_level = reference - spectral_config.CUTOFF_THRESHOLD_DB

    above_start = np.flatnonzero(mag_h >= start_level)
    if above_start.size == 0:
        return "no_edge", float("nan"), float("nan")
    last_above = int(above_start[-1])
    edge = float(freq_h[last_above])
    if edge >= freq_h[-1] - 1e-6 or edge >= 0.999 * nyquist:
        return "no_wall", float("nan"), float("nan")

    below_end = np.flatnonzero(mag_h[last_above:] <= end_level)
    if below_end.size == 0:
        return "no_floor", edge, float("nan")
    width = float(freq_h[last_above + int(below_end[0])]) - edge
    return "ok", edge, max(width, 0.0)


def bolted_anchor_diagnostic(
    freq: np.ndarray, mag_db: np.ndarray, samplerate: int, cutoff: float
) -> Tuple[bool, bool]:
    """Was the bolted width search already below its levels at its first bin?

    Reproduces the search-window entry conditions of ``detect_cutoff_detailed``
    on the same curve: (anchor_missed, anchor_dead) = first searched bin already
    below ref-6 dB, and below ref-30 dB. anchor_dead means a 0-width reading was
    available without any wall being present.
    """
    if samplerate <= 48000:
        ref_low = float(spectral_config.REFERENCE_FREQ_LOW)
        ref_high = float(spectral_config.REFERENCE_FREQ_HIGH)
    else:
        scale = samplerate / 44100.0
        ref_low = float(spectral_config.REFERENCE_FREQ_LOW) * scale
        ref_high = float(spectral_config.REFERENCE_FREQ_HIGH) * scale
    ref_mask = (freq >= ref_low) & (freq <= ref_high)
    if not np.any(ref_mask):
        return False, False
    reference = float(np.median(mag_db[ref_mask]))

    above = freq > ref_low
    freq_h = freq[above]
    mag_h = mag_db[above]
    if len(mag_h) > WIDTH_SMOOTH_BINS:
        from scipy.ndimage import uniform_filter1d

        mag_h = uniform_filter1d(mag_h, size=WIDTH_SMOOTH_BINS)
    search = freq_h >= (cutoff - spectral_config.TRANCHE_SIZE)
    if not np.any(search):
        return False, False
    first = float(mag_h[search][0])
    start_level = reference - START_DROP_DB
    end_level = reference - spectral_config.CUTOFF_THRESHOLD_DB
    return first <= start_level, first <= end_level


def on_grid(cutoff: float) -> bool:
    """Is this cutoff a slice boundary of detect_cutoff's scan grid?"""
    if not np.isfinite(cutoff) or cutoff < GRID_START:
        return False
    return abs((cutoff - GRID_START) % GRID_STEP) < 1e-6


def measure(path: str) -> Optional[dict]:
    try:
        info = sf.info(path)
        data, rate = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    except Exception:
        return None
    if data.size == 0:
        return None
    mono = np.asarray(data if data.ndim == 1 else np.mean(data, axis=1), dtype=np.float64)

    row: dict = {"path": Path(path).name, "rate": rate}
    try:
        freq16, mag16 = _welch_magnitude_db(mono, rate, nfft=16384)
        if freq16 is None or mag16 is None:
            return None
        status, edge, width = self_anchored(freq16, mag16, rate)
        row.update({"sa16_status": status, "sa16_edge": edge, "sa16_width": width})

        reading = detect_cutoff_detailed(freq16, mag16, rate)
        missed, dead = (
            bolted_anchor_diagnostic(freq16, mag16, rate, reading.cutoff_hz)
            if reading.found
            else (False, False)
        )
        row.update(
            {
                "bolt_cutoff": reading.cutoff_hz,
                "bolt_found": int(reading.found),
                "bolt_width": reading.width_hz,
                "bolt_on_grid": int(on_grid(reading.cutoff_hz)),
                "anchor_missed": int(missed),
                "anchor_dead": int(dead),
            }
        )

        freq65, mag65 = _welch_magnitude_db(mono, rate, nfft=65536)
        if freq65 is not None and mag65 is not None:
            status65, edge65, width65 = self_anchored(freq65, mag65, rate)
        else:
            status65, edge65, width65 = "short", float("nan"), float("nan")
        row.update({"sa65_status": status65, "sa65_edge": edge65, "sa65_width": width65})
    except Exception:
        return None
    return row


# ---------------------------------------------------------------------------
# Self-test on synthetic knowns. The method rule this project keeps relearning:
# validate the instrument on an answer that is ALREADY KNOWN before reading what
# it says about anything unknown — and a control must not share the instrument's
# own defect (a step function survives any kernel, so ramps and dips are the
# controls that actually bite).
# ---------------------------------------------------------------------------

RATE = 44100
DUR = 30.0


def _shaped_noise(shape_db) -> np.ndarray:
    rng = np.random.default_rng(20260820)
    n = int(RATE * DUR)
    noise = rng.standard_normal(n)
    spec = np.fft.rfft(noise)
    freq = np.fft.rfftfreq(n, 1 / RATE)
    gain = 10 ** (np.asarray([shape_db(f) for f in freq], dtype=np.float64) / 20.0)
    return np.fft.irfft(spec * gain, n)


def selftest() -> int:
    failures = []

    def check(name, cond, detail):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}  ({detail})", flush=True)
        if not cond:
            failures.append(name)

    print("1. brickwall at 20,137 Hz (off-grid)", flush=True)
    wall = _shaped_noise(lambda f: 0.0 if f < 20137 else -120.0)
    freq16, mag16 = _welch_magnitude_db(wall, RATE, nfft=16384)
    st, e, w = self_anchored(freq16, mag16, RATE)
    check("status ok", st == "ok", st)
    check("edge within 30 Hz of truth", abs(e - 20137) <= 30, f"{e:.1f} Hz")
    check("edge NOT on the 250 Hz grid", not on_grid(e), f"{e:.1f} Hz")
    check("width at floor (<= 30 Hz)", w <= 30, f"{w:.1f} Hz")
    freq65, mag65 = _welch_magnitude_db(wall, RATE, nfft=65536)
    st65, e65, w65 = self_anchored(freq65, mag65, RATE)
    check("finer floor at 65536 (<= 8 Hz)", st65 == "ok" and w65 <= 8, f"{w65:.1f} Hz")
    from flac_detective.analysis.spectrum import detect_cutoff

    bolted = detect_cutoff(freq16, mag16, RATE)
    check("bolted cutoff IS on the grid", on_grid(bolted), f"{bolted:.1f} Hz")

    print("2. linear ramp 20,000 -> 20,400 Hz, 0 to -40 dB (true -6/-30 span = 240 Hz)")
    def ramp_db(f):
        if f < 20000:
            return 0.0
        if f > 20400:
            return -120.0
        return -40.0 * (f - 20000) / 400.0

    ramp = _shaped_noise(ramp_db)
    freq16, mag16 = _welch_magnitude_db(ramp, RATE, nfft=16384)
    st, e, w = self_anchored(freq16, mag16, RATE)
    check("ramp width 190-290 Hz at 16384", st == "ok" and 190 <= w <= 290, f"{st} {w:.1f} Hz")
    freq65, mag65 = _welch_magnitude_db(ramp, RATE, nfft=65536)
    st65, e65, w65 = self_anchored(freq65, mag65, RATE)
    check(
        "resolution-stable (|w16-w65| <= 30 Hz)",
        st65 == "ok" and abs(w - w65) <= 30,
        f"{w:.1f} vs {w65:.1f} Hz",
    )

    print("3. full-band noise")
    full = _shaped_noise(lambda f: 0.0)
    freq16, mag16 = _welch_magnitude_db(full, RATE, nfft=16384)
    st, e, w = self_anchored(freq16, mag16, RATE)
    check("sentinel no_wall", st == "no_wall", st)

    print("4. interior dip (18-19 kHz at -50 dB) recovering before a wall at 21 kHz")
    def dip_db(f):
        if 18000 <= f <= 19000:
            return -50.0
        return 0.0 if f < 21000 else -120.0

    dip = _shaped_noise(dip_db)
    freq16, mag16 = _welch_magnitude_db(dip, RATE, nfft=16384)
    st, e, w = self_anchored(freq16, mag16, RATE)
    check("edge at the wall, not the dip", st == "ok" and abs(e - 21000) <= 50, f"{e:.1f} Hz")

    print(f"\nselftest: {'OK' if not failures else 'FAILED: ' + ', '.join(failures)}")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# Corpus run
# ---------------------------------------------------------------------------


def collect(limit_genuine: int, limit_arm: int, out_path: Path) -> List[dict]:
    done = set()
    rows: List[dict] = []
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            for old in csv.DictReader(fh):
                done.add((old["arm"], old["path"]))
                rows.append(old)
        print(f"reprise: {len(rows)} lignes deja mesurees", flush=True)

    fieldnames = [
        "arm", "path", "rate",
        "sa16_status", "sa16_edge", "sa16_width",
        "sa65_status", "sa65_edge", "sa65_width",
        "bolt_cutoff", "bolt_found", "bolt_width",
        "bolt_on_grid", "anchor_missed", "anchor_dead",
    ]
    mode = "a" if done else "w"
    with open(out_path, mode, newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for arm, patterns in ARMS.items():
            limit = limit_genuine if arm == "genuine" else limit_arm
            paths: List[str] = []
            if arm == "genuine":
                paths.extend(ADJUDICATION_CANDIDATES)
            for pattern in patterns:
                found = sorted(glob.glob(pattern, recursive="**" in pattern))
                paths.extend(found[: limit // len(patterns) + 1])
            seen = 0
            for path in dict.fromkeys(paths):  # dedup, keep order
                if seen >= limit:
                    break
                if (arm, Path(path).name) in done:
                    seen += 1
                    continue
                row = measure(path)
                if row is None:
                    continue
                row["arm"] = arm
                writer.writerow(row)
                fh.flush()
                rows.append(row)
                seen += 1
            print(f"{arm}: {seen} mesures", flush=True)
    return rows


def _f(row: dict, key: str) -> float:
    try:
        return float(row[key])
    except (ValueError, TypeError):
        return float("nan")


def report(rows: List[dict]) -> None:
    arms = list(ARMS)

    print("\n" + "=" * 78)
    print("P3. LA GRILLE : les cutoffs boulonnes sont-ils des bords de tranche ?")
    print("=" * 78)
    slice_rows = [
        r for r in rows
        if int(r["bolt_found"]) and float(_f(r, "bolt_cutoff")) < 0.95 * _f(r, "rate") / 2
    ]
    grid_hits = sum(int(r["bolt_on_grid"]) for r in slice_rows)
    sa_grid = [r for r in rows if r["sa16_status"] == "ok" and on_grid(_f(r, "sa16_edge"))]
    sa_ok = [r for r in rows if r["sa16_status"] == "ok"]
    print(f"boulonnes (methode tranches) sur grille : {grid_hits}/{len(slice_rows)}"
          f" = {100 * grid_hits / max(len(slice_rows), 1):.1f} %")
    print(f"auto-ancres sur grille : {len(sa_grid)}/{len(sa_ok)}"
          f" = {100 * len(sa_grid) / max(len(sa_ok), 1):.1f} %")

    print("\n" + "=" * 78)
    print("SENTINELLES auto-ancrees par bras (nfft 16384)")
    print("=" * 78)
    print(f"\n{'arm':12}{'n':>5}{'ok':>6}{'no_wall':>9}{'no_floor':>10}{'no_edge':>9}")
    for arm in arms:
        rowset = [r for r in rows if r["arm"] == arm]
        if not rowset:
            continue
        counts = {s: sum(1 for r in rowset if r["sa16_status"] == s)
                  for s in ("ok", "no_wall", "no_floor", "no_edge")}
        print(f"{arm:12}{len(rowset):>5}{counts['ok']:>6}{counts['no_wall']:>9}"
              f"{counts['no_floor']:>10}{counts['no_edge']:>9}")

    print("\n" + "=" * 78)
    print("P1. LARGEUR AUTO-ANCREE : separe-t-elle ? (parmi status ok)")
    print("=" * 78)
    widths16 = {}
    widths65 = {}
    for arm in arms:
        w16 = np.array([_f(r, "sa16_width") for r in rows
                        if r["arm"] == arm and r["sa16_status"] == "ok"])
        w65 = np.array([_f(r, "sa65_width") for r in rows
                        if r["arm"] == arm and r["sa65_status"] == "ok"])
        widths16[arm] = w16[np.isfinite(w16)]
        widths65[arm] = w65[np.isfinite(w65)]
    gen16 = widths16.get("genuine", np.array([]))
    print(f"\n{'arm':12}{'n16':>5}{'med16':>8}{'AUC16':>7}{'n65':>7}{'med65':>8}{'AUC65':>7}")
    for arm in arms:
        w16, w65 = widths16[arm], widths65[arm]
        a16 = auc(-w16, -gen16) if arm != "genuine" and w16.size and gen16.size else float("nan")
        a65 = (auc(-w65, -widths65["genuine"])
               if arm != "genuine" and w65.size and widths65["genuine"].size else float("nan"))
        med16 = np.median(w16) if w16.size else float("nan")
        med65 = np.median(w65) if w65.size else float("nan")
        print(f"{arm:12}{w16.size:>5}{med16:>8.0f}{a16:>7.2f}{w65.size:>7}{med65:>8.0f}{a65:>7.2f}")

    if gen16.size:
        print("\nconjonction tarifee, barre = p5 des authentiques "
              f"= {np.percentile(gen16, 5):.0f} Hz")
        bar = float(np.percentile(gen16, 5))
        for arm in arms:
            if arm == "genuine" or not widths16[arm].size:
                continue
            fires = int((widths16[arm] <= bar).sum())
            total = sum(1 for r in rows if r["arm"] == arm)
            print(f"    {arm:12} {fires:3d}/{widths16[arm].size:3d} des ok"
                  f"   = {100 * fires / total:5.1f} % de l'arme entiere ({total})")

    print("\n" + "=" * 78)
    print("P2. LES TROIS CANDIDATS A ADJUDICATION, re-mesures hors grille")
    print("=" * 78)
    names = {Path(p).name for p in ADJUDICATION_CANDIDATES}
    for r in rows:
        if r["path"] in names and r["arm"] == "genuine":
            print(f"\n  {r['path']}")
            print(f"    boulonne     : cutoff {_f(r, 'bolt_cutoff'):.0f} Hz"
                  f" (grille: {'oui' if int(r['bolt_on_grid']) else 'non'})"
                  f", largeur {_f(r, 'bolt_width'):.1f} Hz")
            print(f"    fenetre      : deja sous -6 dB au 1er bin :"
                  f" {'OUI' if int(r['anchor_missed']) else 'non'} ;"
                  f" deja sous -30 dB : {'OUI' if int(r['anchor_dead']) else 'non'}")
            print(f"    auto  16384  : {r['sa16_status']}"
                  f", bord {_f(r, 'sa16_edge'):.0f} Hz, largeur {_f(r, 'sa16_width'):.1f} Hz")
            print(f"    auto  65536  : {r['sa65_status']}"
                  f", bord {_f(r, 'sa65_edge'):.0f} Hz, largeur {_f(r, 'sa65_width'):.1f} Hz")

    print("\n" + "=" * 78)
    print("DEGENERESCENCES boulonnees dans tout le corpus")
    print("=" * 78)
    print(f"\n{'arm':12}{'bords':>7}{'fenetre sous -6':>17}{'fenetre sous -30':>18}")
    for arm in arms:
        rowset = [r for r in rows if r["arm"] == arm and int(r["bolt_found"])]
        if not rowset:
            continue
        missed = sum(int(r["anchor_missed"]) for r in rowset)
        dead = sum(int(r["anchor_dead"]) for r in rowset)
        print(f"{arm:12}{len(rowset):>7}{missed:>17}{dead:>18}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="self-anchored width probe")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--genuine", type=int, default=120)
    parser.add_argument("--arm", type=int, default=40)
    parser.add_argument("--out", type=Path, default=Path("ml/edge_width_selfanchored.csv"))
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    rows = collect(args.genuine, args.arm, args.out)
    print(f"\n{len(rows)} lignes -> {args.out}", flush=True)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
