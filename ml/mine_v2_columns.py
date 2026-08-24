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
RESULTS
(not yet run)
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
