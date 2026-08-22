#!/usr/bin/env python3
"""The re-mastered arm: price every family against the population the wild sells.

Why this arm exists
-------------------
The W-series (2026-08-21) measured the first lab-to-wild gap: the engine signals
68â€“100 % per arm on lab-made DIRECT transcodes and 8.8 % on owner-attested wild
320s that passed through a mastering chain (MP3 decode â†’ DJ mix, levels,
crossfades â†’ CD press â†’ rip). MP3_IDEM told us why: the chain pushes the audio
clean off the codec fixed point (wild median R 3.18 vs direct 0.89). The lab
bench had no arm for that population, so every published rate silently described
direct transcodes only. This file builds the missing arm and re-prices the
families on it.

The simulated chain, v1 (registered before any measurement)
-----------------------------------------------------------
ffmpeg, applied to the DECODED direct transcode, back to FLAC s16:

    equalizer f=60  g=+2.0 (q 1.0)   â€” bass ride, DJ-desk style
    equalizer f=8000 g=+1.5 (q 1.5)  â€” presence lift
    dynaudnorm f=250:g=15            â€” program-dependent level rides
    alimiter  limit=0.97             â€” brickwall limiter into the press
    aresample + s16 dither           â€” the CD master step

Acceptance, registered BEFORE the simulated arm is measured â€” the validator is
the wild53 signature, a KNOWN ANSWER measured on real bytes:

    A1  The shipped engine (deep) signals <= 20 % of the re-mastered arm
        (wild reads 8.8 %).
    A2  MP3_IDEM median R on the re-mastered arm lands in [2.3, 3.8]
        (wild reads 3.18; genuine 2.73; direct 0.89).
    A3  The SAME engine run signals >= 60 % of the direct arm â€” the contrast
        is the measurement; without A3 the arm proves nothing.

If A1/A2 fail on chain v1, ONE strengthened v2 is permitted and must be
described here; if v2 fails too, the honest result is "the simulator cannot
reproduce the wild signature" and the real chain contains something this file
does not model â€” reported as such, never tuned until it passes.

Results are appended below AFTER the runs; the registrations above stay.
--------------------------------------------------------------------------------
CHAIN V1 MEASURED 2026-08-21 — A2 and A3 HELD, A1 FAILED, and the failure names
the missing ingredient:

    engine signaled   direct 62 %   remastered-v1 65 %   (wild: 8.8 %)
    family        direct AUC  fire   v1 AUC  fire
    idem_R              0.98   98%     0.46    5%   <- fixed point destroyed, as wild
    mdct                0.47    0%     0.42    0%
    stereo_run          0.96   92%     0.93   86%   <- SURVIVES v1; wild kills it
    seam                0.89   72%     0.89   70%   <- SURVIVES v1; wild kills it

    A1 FAILED (65 % vs <= 20 %) · A2 HELD (idem median 3.05, wild 3.18) · A3 HELD.

So EQ + level rides + limiting reproduce the fixed-point destruction exactly and
do not touch the side-channel or temporal-variance tells — while the real chain
kills those too. The physical reading: a joint-stereo-killed side channel can
only be REFILLED by new inter-channel content, and per-bin HF variance can only
be re-agitated by broadband noise. A real console/press chain necessarily adds
a decorrelated analog noise floor; v1 adds none.

CHAIN V2 — the one permitted strengthening, described before it is measured:
v1 plus a decorrelated stereo noise floor at -72 dBFS (white, independent per
channel, seeded per file for reproducibility), added BEFORE the v1 chain. One
mechanism, physically motivated, not a fit. If v2 fails, the simulator cannot
reproduce the wild signature and that is the reported result.

CHAIN V2 MEASURED 2026-08-21 — the noise floor kills exactly what it was
predicted to kill, and the residual names the layer neither chain models:

    engine signaled   direct 62 %   v1 65 %   v2 55 %   (wild: 8.8 %)
    family        direct AUC  fire    v1 AUC  fire    v2 AUC  fire
    idem_R              0.98   98%      0.46    5%      0.42    8%
    mdct                0.47    0%      0.42    0%      0.44    0%
    stereo_run          0.96   92%      0.93   86%      0.40    0%   <- killed, as wild
    seam                0.89   72%      0.89   70%      0.60   20%   <- collapsed

    A2[v2] HELD (idem median 3.25, wild 3.18) · A1[v2] FAILED (55 % vs <= 20 %).

Per the registration, no v3. The honest result is a LAYERED characterisation of
the real mastering chain, each layer now demonstrated by the instrument it
kills: (1) level rides + limiting destroy the codec fixed point (v1, idem
0.98 -> 0.46); (2) a decorrelated analog noise floor refills the side channel
and re-agitates per-bin HF variance (v2, stereo 0.93 -> 0.40, seam 0.89 ->
0.60); (3) a third layer this file does not model — the one that MASKS THE
SPECTRAL CLIFF, since the 55 % residual signal on v2 comes from the
spectral/CNN families that the wild chain also defeats. Candidates for layer 3,
stated not measured: a stronger or shaped (pink) noise floor, crossfade content
from adjacent tracks in the DJ mix, analog saturation harmonics above the
cutoff. The wild53's 8.8 % stays the only measurement of the full stack, and
the lab arm reproduces two of its three layers with named mechanisms.

AMENDMENT 2026-08-22 — layer 1's idem row was partly instrument. The idem
fixed point is grid-locked (period 576, zero tolerance; Provir's finding,
reproduced here same-day), and this arm's chain carries a CONSTANT filter
delay: the phase search (ml/idem_phase_probe.py, PS4) finds best phase 219 on
11/12 v1 files, and the arm's median idem R drops 3.13 -> 1.99 dB once
corrected. So the "fixed point destroyed, as wild" annotation on the idem row
above OVERSTATES the chain's effect — part of that destruction was reading
the arm at the wrong grid phase. The wild half of the sentence is unchanged
and strengthened: the 34 owner-attested wilds read >= 1.89 dB at the best of
all 576 phases (0/34 below the re-cut lawful bar of 1.18). The limiter/level
layer still moves files off the fixed point — but by less than this table's
phase-0 numbers claim.

Usage::

    python ml/remaster_arm.py --build     # construct the re-mastered arm
    python ml/remaster_arm.py --measure   # engine + families on all 3 populations
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mp3_idem_probe import mp3_idem, require_ffmpeg  # noqa: E402
from edge_width_probe import auc  # noqa: E402

AUDIT = Path(r"C:\Users\loutr\audit_corpus")
OUT = Path(r"C:\Users\loutr\remaster_arm")
OUT_V2 = Path(r"C:\Users\loutr\remaster_arm_v2")
LIMIT = 40

CHAIN_V1 = (
    "equalizer=f=60:t=q:w=1:g=2,"
    "equalizer=f=8000:t=q:w=1.5:g=1.5,"
    "dynaudnorm=f=250:g=15,"
    "alimiter=limit=0.97"
)

IDEM_BAR = 1.68
SEAM_BAR = 0.60
RUN_BAR = 2.0
RATIO_REVIEW = 2.0

POPULATIONS = {
    "genuine": AUDIT / "authentic",
    "direct": AUDIT / "fake" / "mp3_320",
    "remastered": OUT,
    "remastered_v2": OUT_V2,
}


NOISE_DBFS = -72.0


def build(ffmpeg: str, v2: bool = False) -> int:
    """Build the re-mastered arm. v2 = v1 + decorrelated -72 dBFS stereo noise."""
    import hashlib
    import tempfile

    out_dir = OUT_V2 if v2 else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted((AUDIT / "fake" / "mp3_320").glob("*.flac"))[:LIMIT]
    amp = 10 ** (NOISE_DBFS / 20.0)
    made = 0
    for src in sources:
        dst = out_dir / src.name
        if dst.exists():
            made += 1
            continue
        with tempfile.TemporaryDirectory() as tmp:
            chain_input = src
            if v2:
                data, rate = sf.read(str(src), dtype="float32")
                if data.ndim == 1:
                    data = np.stack([data, data], axis=1)
                seed = int(hashlib.sha1(src.name.encode()).hexdigest()[:8], 16)
                rng = np.random.default_rng(seed)
                noise = amp * rng.standard_normal(data.shape).astype(np.float32)
                noisy = Path(tmp) / "noisy.wav"
                sf.write(str(noisy), np.clip(data + noise, -1.0, 1.0), rate, subtype="PCM_24")
                chain_input = noisy
            r = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(chain_input),
                    "-af",
                    CHAIN_V1,
                    "-c:a",
                    "flac",
                    "-sample_fmt",
                    "s16",
                    str(dst),
                ],
                capture_output=True,
                text=True,
            )
        if r.returncode == 0:
            made += 1
        else:
            print(f"  chain failed: {src.name}: {r.stderr.strip()[-200:]}")
    print(f"re-mastered arm ({'v2' if v2 else 'v1'}): " f"{made}/{len(sources)} files in {out_dir}")
    return 0


def measure(out_csv: Path) -> List[dict]:  # noqa: C901
    from flac_detective import __version__
    from flac_detective.analysis.analyzer import FLACAnalyzer
    from flac_detective.analysis.new_scoring.mdct import best_alignment_stat
    from flac_detective.analysis.new_scoring.stereo_image import side_dead_run
    from flac_detective.analysis.new_scoring.temporal import temporal_seam

    ffmpeg = require_ffmpeg()
    done: Dict[str, dict] = {}
    if out_csv.exists():
        with open(out_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done[(row["population"], row["track"])] = row
        print(f"reprise: {len(done)} deja mesures", flush=True)

    analyzer = FLACAnalyzer(deep=True)
    fieldnames = [
        "population",
        "track",
        "engine_version",
        "verdict",
        "score",
        "families",
        "idem_R",
        "mdct",
        "stereo_run",
        "seam",
    ]
    rows: List[dict] = list(done.values())
    with open(out_csv, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for population, folder in POPULATIONS.items():
            paths = sorted(folder.glob("*.flac"))[:LIMIT]
            n = 0
            for path in paths:
                if (population, path.name) in done:
                    n += 1
                    continue
                row: dict = {
                    "population": population,
                    "track": path.name,
                    "engine_version": __version__,
                }
                try:
                    result = analyzer.analyze_file(str(path))
                    row["verdict"] = result["verdict"]
                    row["score"] = result["score"]
                    row["families"] = "+".join(sorted(result.get("evidence_families") or []))
                except Exception as exc:
                    print(f"  engine failed {path.name}: {exc}", flush=True)
                    row.update({"verdict": "ERROR", "score": "", "families": ""})
                try:
                    info = sf.info(str(path))
                    data, rate = sf.read(
                        str(path), dtype="float32", frames=int(60 * info.samplerate)
                    )
                    r_db, _, _ = mp3_idem(data, int(rate), ffmpeg)
                    row["idem_R"] = f"{r_db:.3f}" if np.isfinite(r_db) else "nan"
                    mono = np.ascontiguousarray(
                        data if data.ndim == 1 else np.mean(data, axis=1), dtype=np.float32
                    )
                    mdct_stat, _, _ = best_alignment_stat(mono, int(rate), stop_at=float("inf"))
                    row["mdct"] = f"{mdct_stat:.3f}"
                    try:
                        run, _ = side_dead_run(data, int(rate))
                        row["stereo_run"] = f"{run:.2f}" if np.isfinite(run) else "nan"
                    except Exception:
                        row["stereo_run"] = "nan"
                    seam, _ = temporal_seam(mono, int(rate))
                    row["seam"] = f"{seam:.3f}" if np.isfinite(seam) else "nan"
                except Exception as exc:
                    print(f"  stats failed {path.name}: {exc}", flush=True)
                    for key in ("idem_R", "mdct", "stereo_run", "seam"):
                        row.setdefault(key, "nan")
                writer.writerow(row)
                fh.flush()
                rows.append(row)
                n += 1
                print(
                    f"  [{population} {n}/{len(paths)}] {path.name}  {row['verdict']}", flush=True
                )
            print(f"{population}: {n} mesures", flush=True)
    return rows


def _vals(rows: List[dict], population: str, key: str) -> np.ndarray:
    out = []
    for r in rows:
        if r["population"] == population:
            try:
                v = float(r[key])
                if np.isfinite(v):
                    out.append(v)
            except (TypeError, ValueError):
                pass
    return np.array(out)


def report(rows: List[dict]) -> None:
    def signaled(population: str) -> int:
        return sum(
            1
            for r in rows
            if r["population"] == population and r["verdict"] not in ("AUTHENTIC", "ERROR")
        )

    def count(population: str) -> int:
        return sum(1 for r in rows if r["population"] == population)

    print("\n" + "=" * 76)
    print("THE TWO-COLUMN TABLE â€” direct vs re-mastered (wild53 shown as reference)")
    print("=" * 76)

    arms = [p for p in ("direct", "remastered", "remastered_v2") if count(p)]
    n_d, s_d = count("direct"), signaled("direct")
    line = "\nengine signaled:"
    for population in arms:
        n_p, s_p = count(population), signaled(population)
        line += f"   {population} {s_p}/{n_p} = {100*s_p/max(n_p, 1):.0f} %"
    print(line + "   (wild53 owner tier: 8.8 %)")

    header = f"\n{'family':12}"
    for population in arms:
        header += f"{population[:10]+' AUC':>15}{'fire':>7}"
    print(header)
    bars = {
        "idem_R": ("low", IDEM_BAR),
        "mdct": ("high", RATIO_REVIEW),
        "stereo_run": ("high", RUN_BAR),
        "seam": ("high", SEAM_BAR),
    }
    for key, (direction, bar) in bars.items():
        gen = _vals(rows, "genuine", key)
        line = f"{key:12}"
        for population in arms:
            vals = _vals(rows, population, key)
            if not vals.size or not gen.size:
                line += f"{'-':>15}{'-':>7}"
                continue
            if direction == "low":
                a = auc(-vals, -gen)
                fire = int((vals <= bar).sum())
            else:
                a = auc(vals, gen)
                fire = int((vals >= bar).sum())
            line += f"{a:>15.2f}{100*fire/vals.size:>6.0f}%"
        print(line)

    a3 = s_d >= 0.60 * max(n_d, 1)
    print(
        f"\nA3 engine >=60 % on direct:  {'HELD' if a3 else 'FAILED'}"
        f" ({100*s_d/max(n_d, 1):.0f} %)"
    )
    for population in arms:
        if population == "direct":
            continue
        n_p, s_p = count(population), signaled(population)
        idem_r = _vals(rows, population, "idem_R")
        a1 = s_p <= 0.20 * max(n_p, 1)
        a2 = bool(idem_r.size) and 2.3 <= float(np.median(idem_r)) <= 3.8
        med = f"{np.median(idem_r):.2f}" if idem_r.size else "-"
        print(
            f"A1[{population}] engine <=20 %: {'HELD' if a1 else 'FAILED'}"
            f" ({100*s_p/max(n_p, 1):.0f} %)   "
            f"A2[{population}] idem median in [2.3, 3.8]: "
            f"{'HELD' if a2 else 'FAILED'} ({med})"
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--build-v2", action="store_true")
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("ml/remaster_arm.csv"))
    args = parser.parse_args(argv)

    if args.build:
        return build(require_ffmpeg())
    if args.build_v2:
        return build(require_ffmpeg(), v2=True)
    if args.measure:
        rows = measure(args.out)
        report(rows)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
