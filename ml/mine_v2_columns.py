#!/usr/bin/env python3
"""Mining Provir's 84 columns against the v2 key — the route question at x20.

The data: his return on fd-exchange-v2 (ml/exchange/provir_return_v2_2026-08.csv,
590 rows, received 2026-08-23) carries per-file idem reads for three probes at
the searched best phase (LAME-320, LAME-128, ACM-320), the best-phase value,
and a telemetry block. We hold the key. Everything here is analysis of data in
hand; his caveat stands (telemetry reaches no verdict on his side — here it is
read as measurements, which is what he shipped it for).

Bars, as everywhere: a probe's lawful bar is the MINIMUM of its reads on the
56 VERIFIED genuine (the three adjudicated rows excluded); raw R never
compared across probes.

PREDICTIONS, registered before these columns are read against the key
----------------------------------------------------------------------
    M1  ROUTE, replicated at n=59. Our mp3_320 arms are libmp3lame 3.100
        through ffmpeg (Lavc route). Our own era battery read the route lock
        as graded: lame.exe-3.100 saw 4 of 8 Lavc arms. Prediction: the
        fraction of our 59 mp3_320 arms below his LAME-320 probe's lawful
        bar lies in [20 %, 80 %] — the graded lock. Below 20 %: the route
        lock is near-total on his bench. Above 80 %: his probe reaches the
        Lavc route almost fully and the route axis is thinner than our
        8-file cell suggested. All three outcomes are informative; the band
        is the bet.
    M2  FAMILY LOCK on a set he did not build: each non-MP3 arm (aac_ff*,
        aacmf_256, opus_256, vorbis_q8) reads below that same bar on at
        most 10 % of its 59 files — an MP3-family probe does not pull
        other codecs to its fixed point.

    M3-M5 are EXPLORATORY, declared so before reading: (M3) what the
    full-576 search adds over phase 0, per label, from his own columns —
    the number that decides whether we adopt his one-search design; (M4)
    AAC_LATTICE's domain on our AAC arms (flag rate per arm); (M5) his
    stereo axes (hf_stereo_corr, ms_cond, mid_stereo_corr) and
    lsb_entropy / bit_effective, read per label and paired with our R15/R14
    where the pairing is defined. No bars are bet on those; the numbers are
    reported as found.

Results appended below after the run.
--------------------------------------------------------------------------------
RESULTS (2026-08-24)

    M1  HELD at the top of the band: 45/59 = 76 % of our Lavc mp3_320 arms
        read below his LAME-320 probe's lawful bar (1.053; genuine median
        2.366). His LAME-320 instrument reaches the Lavc route far better
        than our lame.exe-3.100 rung did (4/8) — the route axis is
        instrument-dependent, not a wall. AND the probe is RATE-locked:
        mp3_192 2/59, mp3_V0 2/59 under the same bar — a 320-paired probe
        reads 320 encodes, full stop. His LAME-128 probe reads ~nothing of
        ours (max 1/59 anywhere — even mp3_192 sits between its rate and
        320's).
    M2  HELD  worst non-MP3 arm under his LAME-320 bar: aac_ff128 at 5 %.
        The family lock, clean, on 354 files he did not build.
        AND the ACM-320 columns measure his own disambiguator caveat
        wider than he stated it: his ACM probe pulls our mp3_192 (34/59),
        mp3_V0 (15/59) and even aac_ff128 (18/59) toward its fixed point —
        the pull covers low-rate AAC, not only "~128k MP3 of any make".
    M3  (exploratory) The phase search adds ~nothing on THIS set (median
        gain 0.000-0.05 per label) — as construction predicts: our MP3
        arms are at phase 0 and the rest have no MP3 grid; the search's
        value lives in the wild, not here. |bestphase - full_bestphase|
        medians are large on genuine (2.6) and aac_ff256/320 (2.1): the
        two columns are different statistics, and interpreting them needs
        his README (requested, not yet received).
    M4  (exploratory) AAC_LATTICE's domain, read off the key: aacmf_256
        51/59 (86 %), aac_ff320 20/59, aac_ff256 16/59, aac_ff128 6/59,
        ~0 elsewhere, 1/56 genuine. Strongest exactly where his dead run
        is weakest (high-rate ffmpeg AAC read at 0.70-0.75 by
        dead_max_run) — his families complement each other the way ours
        do, measured on one key.
    M5  (exploratory) His correlation-based stereo axes read NOTHING on
        this set (hf_stereo_corr / mid_stereo_corr AUC 0.35-0.50 vs our
        stereo_run 0.70-0.97): his working side-channel instrument is the
        dead run, not the correlations. MS_CONDITIONAL's domain, finally
        read: AUC 0.86-0.97 on mp3_192 and the whole AAC family, 0.5 on
        mp3_320/opus/vorbis. lsb_entropy / bit_effective: flat (0.48-0.52)
        on an all-16-bit set, as expected for hi-res axes.
    Bonus: best phases on the 413 non-MP3 files scatter (top count 6) —
    pure draws, the negative control of J3's 150/177.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HIS = Path("ml/exchange/provir_return_v2_2026-08.csv")
OURS = Path("ml/exchange/fd-exchange-v2_columns_flacdetective.csv")
KEY = Path(r"C:\Users\loutr\fd-exchange-v2-2026-08-LABELS.json")
EXCLUDED = {"fd-exchange-v2-2026-08-0197.flac", "fd-exchange-v2-2026-08-0386.flac", "fd-exchange-v2-2026-08-0469.flac"}
ARMS = ["mp3_192", "mp3_320", "mp3_V0", "aac_ff128", "aac_ff256", "aac_ff320", "aacmf_256", "opus_256", "vorbis_q8"]


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def auc(pos, neg):
    pos = np.array([v for v in pos if np.isfinite(v)])
    neg = np.array([v for v in neg if np.isfinite(v)])
    if not pos.size or not neg.size:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (pos.size * neg.size))


def main() -> int:
    his = {r["file"]: r for r in csv.DictReader(open(HIS, newline="", encoding="utf-8"))}
    ours = {r["file"]: r for r in csv.DictReader(open(OURS, newline="", encoding="utf-8"))}
    key = json.loads(KEY.read_text(encoding="utf-8"))["labels"]
    lab = {x: key[x[:-5]]["label"] for x in his}
    genuine = [x for x in his if lab[x] == "genuine" and x not in EXCLUDED]

    probes = {
        "LAME-320": "idem.R_mp3_320_bestphase",
        "LAME-128": "idem.R_mp3_128_bestphase",
        "ACM-320": "idem.R_fhgacm_320_bestphase",
    }
    bars = {}
    print("lawful bars (min over 56 verified genuine), per HIS probe:")
    for name, col in probes.items():
        vals = [f(his[x][col]) for x in genuine]
        vals = [v for v in vals if np.isfinite(v)]
        bars[name] = min(vals)
        print(f"  {name:9} bar {bars[name]:6.3f}  (n={len(vals)}, median {np.median(vals):.3f})")

    print("\nfraction of each arm below each probe's bar (his reads, our key):")
    below = defaultdict(dict)
    print(f"  {'arm':10}" + "".join(f"{p:>10}" for p in probes))
    for arm in ARMS:
        files = [x for x in his if lab[x] == arm]
        row = ""
        for name, col in probes.items():
            n_below = sum(1 for x in files if np.isfinite(f(his[x][col])) and f(his[x][col]) < bars[name])
            below[arm][name] = n_below
            row += f"{n_below:>7}/59"
        print(f"  {arm:10}" + row)

    m1_frac = below["mp3_320"]["LAME-320"] / 59
    m1 = 0.2 <= m1_frac <= 0.8
    print(f"\nM1 mp3_320 (Lavc) below his LAME-320 bar: {below['mp3_320']['LAME-320']}/59 = {m1_frac:.0%} "
          f"(band [20 %, 80 %]): {'HELD' if m1 else 'FAILED'}")
    non_mp3 = ["aac_ff128", "aac_ff256", "aac_ff320", "aacmf_256", "opus_256", "vorbis_q8"]
    worst = max((below[a]["LAME-320"] / 59, a) for a in non_mp3)
    m2 = worst[0] <= 0.10
    print(f"M2 non-MP3 arms below his LAME-320 bar (each <= 10 %): worst {worst[1]} at {worst[0]:.0%}: "
          f"{'HELD' if m2 else 'FAILED'}")

    # M3: what the search added over phase 0 (his LAME-320 columns)
    print("\nM3 (exploratory) phase search gain, R_mp3_320_phase0 - R_mp3_320_bestphase, median per label:")
    for arm in ["genuine"] + ARMS:
        files = [x for x in his if lab[x] == arm and x not in EXCLUDED]
        gain = [f(his[x]["idem.R_mp3_320_phase0"]) - f(his[x]["idem.R_mp3_320_bestphase"]) for x in files]
        gain = [g for g in gain if np.isfinite(g)]
        full = [f(his[x]["idem.R_mp3_320_full_bestphase"]) for x in files]
        quick = [f(his[x]["idem.R_mp3_320_bestphase"]) for x in files]
        both = [(q, fl) for q, fl in zip(quick, full) if np.isfinite(q) and np.isfinite(fl)]
        dfull = [abs(q - fl) for q, fl in both]
        print(f"  {arm:10} median gain {np.median(gain):6.3f}  max {max(gain):6.3f}   "
              f"|bestphase - full_bestphase| median {np.median(dfull) if dfull else float('nan'):.3f}")

    # M4: AAC_LATTICE flag rate per arm
    print("\nM4 (exploratory) AAC_LATTICE flag rate per arm (his flags column):")
    for arm in ["genuine"] + ARMS:
        files = [x for x in his if lab[x] == arm and x not in EXCLUDED]
        n = sum(1 for x in files if "AAC_LATTICE" in his[x]["flags"])
        print(f"  {arm:10} {n:3}/{len(files)}")

    # M5: stereo axes + bit depth, AUC vs genuine, paired with ours
    print("\nM5 (exploratory) his stereo/bit axes, AUC arm-vs-genuine (negated where lower = more suspect):")
    axes = [
        ("telemetry.hf_stereo_corr", -1), ("telemetry.mid_stereo_corr", -1), ("telemetry.ms_cond", +1),
        ("telemetry.lsb_entropy", -1), ("telemetry.bit_effective", -1),
    ]
    hdr = f"  {'arm':10}" + "".join(f"{c.split('.')[-1][:14]:>16}" for c, _ in axes) + f"{'our stereo_run':>16}"
    print(hdr)
    for arm in ARMS:
        files = [x for x in his if lab[x] == arm]
        row = f"  {arm:10}"
        for col, sign in axes:
            a = auc([sign * f(his[x][col]) for x in files], [sign * f(his[x][col]) for x in genuine])
            row += f"{a:>16.2f}"
        a_ours = auc([f(ours[x]["stereo_run"]) for x in files], [f(ours[x]["stereo_run"]) for x in genuine])
        row += f"{a_ours:>16.2f}"
        print(row)

    # bonus: his best_phase clusters outside phase 0 (the constant-delay diagnostic on our arms)
    print("\nbest_phase distribution on non-MP3 arms (top 5):")
    c = Counter(his[x]["idem.best_phase"] for x in his if lab[x] not in {"mp3_192", "mp3_320", "mp3_V0"})
    print(" ", c.most_common(5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
