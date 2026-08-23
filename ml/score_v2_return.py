#!/usr/bin/env python3
"""Scoring Provir's return on fd-exchange-v2, and ours beside it — the first
evidence-column exchange, adjudicated at the mechanism.

What arrived (2026-08-23): one CSV, 590 rows, 84 columns (sha256
42d0e7a424fad5ae...), archived as ml/exchange/provir_return_v2_2026-08.csv.
Verdicts mapped as in the first exchange: clear / flagged / convicted;
442 / 107 / 41 announced. Four sentinels held on his side. The three columns
we asked for are on every row: telemetry.dead_max_run (+ dead_mean_run), the
idem read per probe at the best phase (LAME-320, LAME-128, ACM-320) with
idem.best_phase and its first-pass distance. His caveat, respected here: the
telemetry.* columns are diagnostics that reach no verdict; `flags` is the
load-bearing column.

The key: 59 sources x 10 arms (genuine, mp3_192, mp3_320, mp3_V0, aac_ff128,
aac_ff256, aac_ff320, aacmf_256, opus_256, vorbis_q8), 59 each. Our own
columns (ml/exchange_v2_columns.py) were computed before his CSV arrived and
are scored here the same way.

PREDICTIONS, registered before the key is opened on his rows
-------------------------------------------------------------
    J1  FALSE CONVICTIONS. At most 2 of the 59 genuine are convicted. His
        stated discipline is in what he convicts; this is its price on a
        set he did not build.
    J2  CLEARS. At least 30 of his 41 clears are genuine.
    J3  HIS PHASE SEARCH ON OUR KNOWN ANSWER. Our MP3 arms (mp3_192/320/V0,
        177 files) are ffmpeg decodes of our own encodes — phase 0 by
        construction. Prediction: >= 80 % of the MP3-arm files land at
        idem.best_phase 0, and < 30 % of the non-MP3 files (genuine, AAC,
        Opus, Vorbis — no MP3 grid) do. His 152-at-phase-0 would then be
        mostly our 177.
    J4  DEAD_STRUCTURE'S DOMAIN, read off the key at last. dead_max_run
        separates at least one transcode arm from the genuine at AUC >= 0.80.
        The arm(s) it reads name its domain.

Our engine is scored beside his with no prediction (it is our set; the
numbers are reported, not bet on): false convictions on the 59 genuine,
signaled (WARNING+) and convicted (FAKE_CERTAIN) per arm.

Adjudication at the mechanism, first look: where his verdict and ours
disagree, the columns both sides rest on are printed side by side —
rolloff_hz vs cutoff_hz, his idem.R_mp3_320_phase0 vs our idem_R_phase0,
dead_max_run vs our stereo_run / seam.

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
OURS_IDEM = Path("ml/exchange/fd-exchange-v2_idem_flacdetective.csv")
KEY = Path(r"C:\Users\loutr\fd-exchange-v2-2026-08-LABELS.json")
ARMS = ["genuine", "mp3_192", "mp3_320", "mp3_V0", "aac_ff128", "aac_ff256", "aac_ff320", "aacmf_256", "opus_256", "vorbis_q8"]
MP3_ARMS = {"mp3_192", "mp3_320", "mp3_V0"}


def load(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["file"]: r for r in csv.DictReader(fh)}


def auc(pos, neg) -> float:
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if not pos.size or not neg.size:
        return float("nan")
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (pos.size * neg.size))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def main() -> int:
    his, ours, ours_idem = load(HIS), load(OURS), load(OURS_IDEM)
    key = json.loads(KEY.read_text(encoding="utf-8"))["labels"]
    label = {f: key[f.replace(".flac", "")]["label"] for f in his}
    assert len(his) == len(ours) == 590

    # ---- J1 / J2 ----------------------------------------------------------
    by = defaultdict(Counter)
    for f, r in his.items():
        by[label[f]][r["verdict"]] += 1
    false_conv = by["genuine"]["convicted"]
    clears_genuine = by["genuine"]["clear"]
    clears_total = sum(c["clear"] for c in by.values())
    print("HIS verdicts per label (clear / flagged / convicted):")
    for a in ARMS:
        c = by[a]
        print(f"  {a:10} {c['clear']:3} / {c['flagged']:3} / {c['convicted']:3}")
    print(f"\nJ1 false convictions on 59 genuine (<= 2): {false_conv}  {'HELD' if false_conv <= 2 else 'FAILED'}")
    print(f"J2 genuine among his clears (>= 30 of {clears_total}): {clears_genuine}  {'HELD' if clears_genuine >= 30 else 'FAILED'}")

    # ---- J3: his phase search on our known answer ------------------------
    mp3_at0 = sum(1 for f, r in his.items() if label[f] in MP3_ARMS and r["idem.best_phase"] == "0")
    mp3_n = sum(1 for f in his if label[f] in MP3_ARMS)
    other_at0 = sum(1 for f, r in his.items() if label[f] not in MP3_ARMS and r["idem.best_phase"] == "0")
    other_n = 590 - mp3_n
    j3 = mp3_at0 / mp3_n >= 0.8 and other_at0 / other_n < 0.3
    print(f"\nJ3 phase 0 on MP3 arms {mp3_at0}/{mp3_n} = {mp3_at0 / mp3_n:.0%} (>= 80 %), on the rest "
          f"{other_at0}/{other_n} = {other_at0 / other_n:.0%} (< 30 %): {'HELD' if j3 else 'FAILED'}")
    per = Counter()
    for f, r in his.items():
        if r["idem.best_phase"] == "0":
            per[label[f]] += 1
    print("   phase-0 files per label: " + ", ".join(f"{a} {per[a]}" for a in ARMS))

    # ---- J4: dead_max_run's domain -----------------------------------------
    dmr = {a: [fnum(r["telemetry.dead_max_run"]) for f, r in his.items() if label[f] == a] for a in ARMS}
    gen = [v for v in dmr["genuine"] if np.isfinite(v)]
    print("\nJ4 dead_max_run AUC vs genuine (his column, our key):")
    best = 0.0
    for a in ARMS[1:]:
        arm = [v for v in dmr[a] if np.isfinite(v)]
        A = auc(arm, gen)
        best = max(best, A)
        print(f"  {a:10} AUC {A:.2f}   median {np.median(arm):6.1f} vs genuine {np.median(gen):6.1f}")
    print(f"J4 some arm at AUC >= 0.80: {'HELD' if best >= 0.8 else 'FAILED'} (best {best:.2f})")

    # ---- Our engine on the same set -------------------------------------
    our_by = defaultdict(Counter)
    for f, r in ours.items():
        our_by[label[f]][r["verdict"]] += 1
    print("\nOUR engine (v1.13.0, deep) per label (AUTHENTIC / WARNING / SUSPICIOUS / FAKE_CERTAIN):")
    for a in ARMS:
        c = our_by[a]
        print(f"  {a:10} {c['AUTHENTIC']:3} / {c['WARNING']:3} / {c['SUSPICIOUS']:3} / {c['FAKE_CERTAIN']:3}")
    print(f"our false convictions on 59 genuine: {our_by['genuine']['FAKE_CERTAIN']}")

    print("\nHEAD TO HEAD, transcode arms (his convicted | our FAKE_CERTAIN ; his flagged+convicted | our WARNING+):")
    for a in ARMS[1:]:
        h, o = by[a], our_by[a]
        print(f"  {a:10} conv {h['convicted']:3} | {o['FAKE_CERTAIN']:3}     signaled {h['flagged'] + h['convicted']:3} | "
              f"{o['WARNING'] + o['SUSPICIOUS'] + o['FAKE_CERTAIN']:3}")

    # ---- Adjudication at the mechanism, first look -------------------------
    print("\nMECHANISM, first look:")
    roll = [(fnum(his[f]["rolloff_hz"]), fnum(ours[f]["cutoff_hz"])) for f in his]
    d = np.array([abs(a - b) for a, b in roll if np.isfinite(a) and np.isfinite(b)])
    print(f"  |his rolloff_hz - our cutoff_hz|: median {np.median(d):.0f} Hz, within 250 Hz on {np.mean(d <= 250):.0%} of files, "
          f"> 2 kHz on {np.mean(d > 2000):.0%}")
    pairs = [(fnum(his[f]["idem.R_mp3_320_phase0"]), fnum(ours_idem[f]["idem_R_phase0"])) for f in his if f in ours_idem]
    pairs = [(a, b) for a, b in pairs if np.isfinite(a) and np.isfinite(b)]
    if pairs:
        a_, b_ = zip(*pairs)
        print(f"  his idem R_mp3_320 phase0 vs ours (same family, his route vs ffmpeg): Pearson {np.corrcoef(a_, b_)[0, 1]:.2f} on {len(pairs)} files")
    his_conv_our_auth = [f for f in his if his[f]["verdict"] == "convicted" and ours[f]["verdict"] == "AUTHENTIC"]
    our_conv_his_clear = [f for f in his if ours[f]["verdict"] == "FAKE_CERTAIN" and his[f]["verdict"] == "clear"]
    print(f"  he convicts / we clear: {len(his_conv_our_auth)} files; we convict / he clears: {len(our_conv_his_clear)} files")
    for f in his_conv_our_auth[:8]:
        print(f"    {f[-9:-5]} {label[f]:10} his rolloff {his[f]['rolloff_hz']:>8} our cutoff {ours[f]['cutoff_hz']:>8}  his flags {his[f]['flags'][:70]}")
    for f in our_conv_his_clear[:8]:
        print(f"    {f[-9:-5]} {label[f]:10} our families {ours[f]['evidence_families']:24} score {ours[f]['score']}  his flags {his[f]['flags'][:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
