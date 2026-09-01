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
RESULTS (2026-08-23, key as frozen; documentary adjudication after)

    J1  FAILED on the frozen key: 3 of 59 genuine convicted (bound 2).
        HELD after adjudication: one of the three (0197) is a taper-
        documented MP2 chain — his conviction was right and the key was
        wrong; one (0469) is an H1n recording of unstated format, both
        labs' side-channel instruments reading it lossy — unverifiable;
        the third (0306) is an analog FM line-in capture and stays
        genuine. HIS false convictions on 56 verified genuine: 1.
    J2  HELD    33 of his 41 clears are genuine; the 8 others are 6 aac_ff320
                and 2 mp3_V0 at full-band cutoffs (the two arms that leave
                no wall).
    J3  HELD    his best phase lands on 0 for 150/177 of our MP3 arms
                (85 %) and 2/413 of everything else (0 %). His phase
                search, validated on a construction he could not see.
    J4  HELD    dead_max_run's domain, read off the key: AUC 0.92 on
                mp3_192 / aac_ff128 / aacmf_256, 0.91 on mp3_320 / mp3_V0 /
                vorbis_q8, 0.86 on opus_256, 0.75 / 0.70 on aac_ff256 /
                aac_ff320 (genuine median 10, transcode medians 30-265).
                It reads every codec family including Opus, and weakens
                only where ffmpeg's AAC leaves the side channel alone at
                high rate — the mirror of our R15, measured at last.

    OUR ENGINE (v1.13.0, deep) on the same key: 2 genuine FAKE_CERTAIN on
    the frozen key — 0362 (recipe2004-08-21.sbd: SBD, named taper, no
    lineage, 17.5 kHz wall: Rule 1 + CNN on the same feature = a TRUE false
    conviction, our first since v1.10) and 0386 (rcpm2000-05-05: 'unknown >
    CDR', his dead_max_run 334 and our two witnesses agree: unverifiable).
    After adjudication: 1 false conviction each, on 56 verified genuine —
    his on an FM capture, ours on a walled soundboard. Genuine signaled:
    his 23/56, ours 6/56. Transcode convictions: his 104 (aacmf 40, opus 24,
    mp3_320 20, mp3_192 14, 2 each aac_ff256/320/vorbis, 0 aac_ff128/V0),
    ours 223 (vorbis 40, mp3_192 33, aac_ff256 33, aac_ff128 32, aacmf 25,
    aac_ff320 21, mp3_320 17, opus 13, V0 9). He convicts 25 files we clear
    (mp3_320, opus, aacmf — HF_SEAM / DEAD_STRUCTURE routes); we convict 0
    he clears.

    MECHANISM, first look: his rolloff_hz and our cutoff_hz are DIFFERENT
    OBSERVABLES (median 12.5 kHz apart, never within a cell) — his is a
    spectral-rolloff statistic, ours the wall; the adjudication column for
    the wall is his telemetry.hf_cutoff / brickwall, to be paired next. His
    idem R_mp3_320 at phase 0 vs ours: Pearson 0.72 on 580 files, same
    family through two routes.

    THE KEY'S OWN LESSON: the v2 genuine tier carried one documented MP2
    chain and two unverifiable provenances among 59 — the fetcher selected
    on licence and collection, never on the taper's source line. The v3
    freezer reads source/lineage for codec names (MP2, MP3, MD, MZ-, ATRAC,
    AAC) before a file can be labelled genuine.
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
ARMS = [
    "genuine",
    "mp3_192",
    "mp3_320",
    "mp3_V0",
    "aac_ff128",
    "aac_ff256",
    "aac_ff320",
    "aacmf_256",
    "opus_256",
    "vorbis_q8",
]
MP3_ARMS = {"mp3_192", "mp3_320", "mp3_V0"}

# Documentary adjudication of the "genuine" rows either engine convicted,
# read off the archive.org item metadata on 2026-08-23 (the MiniDisc method;
# the engine's verdict never becomes the label). Applied AFTER the registered
# J-series is scored on the key as frozen.
ADJUDICATIONS = {
    "fd-exchange-v2-2026-08-0197": (
        "fake",
        "uploader_admission",
        "TenD2005-07-16.flac16: taper's source line 'Sony PC100 > AVI > MP2 > WAV > FLAC' - MPEG-1 Layer II, lossy",
    ),
    "fd-exchange-v2-2026-08-0386": (
        "unverifiable",
        "lineage_unknown",
        "rcpm2000-05-05.flac16: 'source: unknown > CDR', taper unknown - no lossless provenance to stand on",
    ),
    "fd-exchange-v2-2026-08-0469": (
        "unverifiable",
        "device_ambiguous",
        "SweatyAlreadyStringBand2026-08-16: 'Zoom H1n' records WAV or MP3, format unstated",
    ),
    # 0306 (dknowles2008-07-13.fm: analog FM line-in capture) and 0362
    # (recipe2004-08-21.sbd: SBD, named taper) stay genuine - no documented
    # codec; each is one engine's true false conviction.
}


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
    print(
        f"\nJ1 false convictions on 59 genuine (<= 2): {false_conv}  {'HELD' if false_conv <= 2 else 'FAILED'}"
    )
    print(
        f"J2 genuine among his clears (>= 30 of {clears_total}): {clears_genuine}  {'HELD' if clears_genuine >= 30 else 'FAILED'}"
    )

    # ---- J3: his phase search on our known answer ------------------------
    mp3_at0 = sum(1 for f, r in his.items() if label[f] in MP3_ARMS and r["idem.best_phase"] == "0")
    mp3_n = sum(1 for f in his if label[f] in MP3_ARMS)
    other_at0 = sum(
        1 for f, r in his.items() if label[f] not in MP3_ARMS and r["idem.best_phase"] == "0"
    )
    other_n = 590 - mp3_n
    j3 = mp3_at0 / mp3_n >= 0.8 and other_at0 / other_n < 0.3
    print(
        f"\nJ3 phase 0 on MP3 arms {mp3_at0}/{mp3_n} = {mp3_at0 / mp3_n:.0%} (>= 80 %), on the rest "
        f"{other_at0}/{other_n} = {other_at0 / other_n:.0%} (< 30 %): {'HELD' if j3 else 'FAILED'}"
    )
    per = Counter()
    for f, r in his.items():
        if r["idem.best_phase"] == "0":
            per[label[f]] += 1
    print("   phase-0 files per label: " + ", ".join(f"{a} {per[a]}" for a in ARMS))

    # ---- J4: dead_max_run's domain -----------------------------------------
    dmr = {
        a: [fnum(r["telemetry.dead_max_run"]) for f, r in his.items() if label[f] == a]
        for a in ARMS
    }
    gen = [v for v in dmr["genuine"] if np.isfinite(v)]
    print("\nJ4 dead_max_run AUC vs genuine (his column, our key):")
    best = 0.0
    for a in ARMS[1:]:
        arm = [v for v in dmr[a] if np.isfinite(v)]
        A = auc(arm, gen)
        best = max(best, A)
        print(
            f"  {a:10} AUC {A:.2f}   median {np.median(arm):6.1f} vs genuine {np.median(gen):6.1f}"
        )
    print(f"J4 some arm at AUC >= 0.80: {'HELD' if best >= 0.8 else 'FAILED'} (best {best:.2f})")

    # ---- Our engine on the same set -------------------------------------
    our_by = defaultdict(Counter)
    for f, r in ours.items():
        our_by[label[f]][r["verdict"]] += 1
    print(
        "\nOUR engine (v1.13.0, deep) per label (AUTHENTIC / WARNING / SUSPICIOUS / FAKE_CERTAIN):"
    )
    for a in ARMS:
        c = our_by[a]
        print(
            f"  {a:10} {c['AUTHENTIC']:3} / {c['WARNING']:3} / {c['SUSPICIOUS']:3} / {c['FAKE_CERTAIN']:3}"
        )
    print(f"our false convictions on 59 genuine: {our_by['genuine']['FAKE_CERTAIN']}")

    print(
        "\nHEAD TO HEAD, transcode arms (his convicted | our FAKE_CERTAIN ; his flagged+convicted | our WARNING+):"
    )
    for a in ARMS[1:]:
        h, o = by[a], our_by[a]
        print(
            f"  {a:10} conv {h['convicted']:3} | {o['FAKE_CERTAIN']:3}     signaled {h['flagged'] + h['convicted']:3} | "
            f"{o['WARNING'] + o['SUSPICIOUS'] + o['FAKE_CERTAIN']:3}"
        )

    # ---- Adjudication at the mechanism, first look -------------------------
    print("\nMECHANISM, first look:")
    roll = [(fnum(his[f]["rolloff_hz"]), fnum(ours[f]["cutoff_hz"])) for f in his]
    d = np.array([abs(a - b) for a, b in roll if np.isfinite(a) and np.isfinite(b)])
    print(
        f"  |his rolloff_hz - our cutoff_hz|: median {np.median(d):.0f} Hz, within 250 Hz on {np.mean(d <= 250):.0%} of files, "
        f"> 2 kHz on {np.mean(d > 2000):.0%}"
    )
    pairs = [
        (fnum(his[f]["idem.R_mp3_320_phase0"]), fnum(ours_idem[f]["idem_R_phase0"]))
        for f in his
        if f in ours_idem
    ]
    pairs = [(a, b) for a, b in pairs if np.isfinite(a) and np.isfinite(b)]
    if pairs:
        a_, b_ = zip(*pairs)
        print(
            f"  his idem R_mp3_320 phase0 vs ours (same family, his route vs ffmpeg): Pearson {np.corrcoef(a_, b_)[0, 1]:.2f} on {len(pairs)} files"
        )
    # ---- After documentary adjudication --------------------------------------
    print("\nAFTER ADJUDICATION (genuine rows re-read from archive.org metadata):")
    corrected = dict(label)
    for fid, (lab, basis, note) in ADJUDICATIONS.items():
        corrected[fid + ".flac"] = lab
        print(f"  {fid[-4:]} -> {lab:12} [{basis}] {note[:90]}")
    gen_files = [f for f in his if corrected[f] == "genuine"]
    his_fc = [f for f in gen_files if his[f]["verdict"] == "convicted"]
    our_fc = [f for f in gen_files if ours[f]["verdict"] == "FAKE_CERTAIN"]
    print(f"  verified genuine: {len(gen_files)}")
    print(f"  HIS false convictions: {len(his_fc)}/{len(gen_files)} {[f[-9:-5] for f in his_fc]}")
    print(f"  OUR false convictions: {len(our_fc)}/{len(gen_files)} {[f[-9:-5] for f in our_fc]}")
    print(
        f"  HIS genuine signaled (flagged+convicted): {sum(his[f]['verdict'] != 'clear' for f in gen_files)}/{len(gen_files)}"
    )
    print(
        f"  OUR genuine signaled (WARNING+): {sum(ours[f]['verdict'] != 'AUTHENTIC' for f in gen_files)}/{len(gen_files)}"
    )

    his_conv_our_auth = [
        f for f in his if his[f]["verdict"] == "convicted" and ours[f]["verdict"] == "AUTHENTIC"
    ]
    our_conv_his_clear = [
        f for f in his if ours[f]["verdict"] == "FAKE_CERTAIN" and his[f]["verdict"] == "clear"
    ]
    print(
        f"  he convicts / we clear: {len(his_conv_our_auth)} files; we convict / he clears: {len(our_conv_his_clear)} files"
    )
    for f in his_conv_our_auth[:8]:
        print(
            f"    {f[-9:-5]} {label[f]:10} his rolloff {his[f]['rolloff_hz']:>8} our cutoff {ours[f]['cutoff_hz']:>8}  his flags {his[f]['flags'][:70]}"
        )
    for f in our_conv_his_clear[:8]:
        print(
            f"    {f[-9:-5]} {label[f]:10} our families {ours[f]['evidence_families']:24} score {ours[f]['score']}  his flags {his[f]['flags'][:50]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
