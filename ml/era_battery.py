#!/usr/bin/env python3
"""The era-paired idem battery — the generation axis on the wild 34, registered.

Why this exists (2026-08-22)
-----------------------------
Two findings left the wild idem question with one axis unspent. The phase
search (ml/idem_phase_probe.py) retired the instrument objection: at the best
of all 576 phases the 34 owner-attested wilds still read >= 1.89 dB from the
3.100 fixed point, 0/34 below the re-cut lawful bar. But that probe is
libmp3lame 3.100 through ffmpeg's Lavc route, and Provir's era bench says the
tell is VERSION-LOCKED (a 3.100-paired probe reaches its own generation and
the adjacent release only) and ROUTE-LOCKED (libmp3lame through ffmpeg is not
lame.exe of the same version). The 2004 discs were encoded by neither. We now
hold his period binaries (exhibit key lame3.92 = arm-1, verified), and he has
offered to mirror this registration on his DJ-mix discs with the same binaries.

The probes (his period builds, never rebuilds — "the version locks; the
compiler moves the read")
---------------------------------------------------------------------------
    lame3.90.3   2002-2003, the "recommended" build of its day
    lame3.92     2002, arm-1 exhibit key (sha cb2cdfde7b170d90)
    lame3.93.1   2003, period build (lame3.93.1r)
    lame3.96.1   2004-07, the year of the discs
    lame3.97     2006, period build (his genuine dip on the 3.100 V0 probe)
    lame3.98.4   2010
    lame3.100    2017, lame.exe — SAME generation as our shipped probe,
                 different route: this rung isolates the route axis.

Each probe read = two sequential roundtrips through that lame.exe at CBR 320
(files never pipes; output judged by size + decodability, never exit code —
his hurdle rule), R = 20 log10(d1/d2) with the shipped dist(), taken as the
MINIMUM over the canonical phases {0, 529, 47}. Under the 3.92 probe the 34
wilds additionally get the full 576-phase search. R is PROBE-RELATIVE (the
E-series lesson): every bar is cut on the probe's own lawful reads, and raw R
is never compared across probes.

Populations: 34 owner-attested wilds (CD1+CD2), 20 certified-genuine audit
sources (the per-probe lawful repricing), 8 direct lab mp3_320 arms
(libmp3lame 3.100 via ffmpeg — the route/generation lock control).

PREDICTIONS, registered before measurement — results appended below
--------------------------------------------------------------------
    EB1  BARS. Each probe's lawful bar = the minimum of its 20 genuine
         reads. No prediction on the values; they are measured (the draws
         rule). Reported per probe.
    EB2  LOCK CONTROL. The 8 Lavc-3.100 lab arms read ABOVE the lawful bar
         of every era probe 3.90.3-3.98.4 for >= 7/8 files each — the era
         probes do not see modern-route arms (version lock + route lock,
         mirrored). Under the lame.exe-3.100 probe the arms read BELOW its
         bar for >= 6/8 (same generation; if the route alone breaks the
         read, that is the finding).
    EB3  THE WILD QUESTION. Under the best-matching era probe at the best
         phase, at least 2 of the 34 wilds read below that probe's lawful
         bar. Below 2: era pairing recovers nothing either, and the wild
         sits off every fixed point we can build — the mastering layers
         stand entire. At or above 2: the generation axis was real, and
         the count is the recovered fraction.
    EB4  THE RUNG (graded only if EB3 holds). Among recovered wilds, the
         best-reading probe clusters on one rung or two adjacent rungs for
         >= 60 % of them — the disc's encoder generation, read off.

Results appended below after the run.
--------------------------------------------------------------------------------
RESULTS (2026-08-23; 434 reads, ml/era_battery_results.csv local — personal
library titles in the genuine/arm rows)

    probe        lawful bar  arms>bar  arms<bar  wild<bar
    lame3.90.3         1.21      8/8       0/8      20/34
    lame3.92           8.99      4/8       4/8       0/34
    lame3.93.1         9.03      8/8       0/8       0/34
    lame3.96.1         4.97      7/8       1/8       0/34
    lame3.97           1.74      6/8       2/8       4/34
    lame3.98.4         0.85      7/8       0/8       0/34
    lame3.100          1.02      4/8       4/8       0/34

    EB1  MEASURED  bars as above; R is probe-relative exactly as the
                   E-series said (3.92/3.93.1 lawful minima near 9 dB,
                   3.98.4 at 0.85) — no raw R was compared across probes.
    EB2  FAILED both halves. Era probes are NOT uniformly blind to the
                   Lavc-3.100 arms: 3.92 reads 4/8 below its bar, 3.97 2/8,
                   3.96.1 1/8 (3.90.3, 3.93.1, 3.98.4 are blind as
                   predicted). And lame.exe-3.100 sees only 4/8 of the
                   same-generation arms below its bar (>= 6 registered):
                   the route alone moves half of them out of reach. The
                   version/route lock is real but graded, not binary —
                   his "generation + adjacent only" with soft edges.
    EB3  HELD — and it is the answer to W4. 23/34 wilds read below some
                   era probe's lawful bar at the best canonical phase;
                   under lame3.90.3 alone, 20/34, clustered AT the fixed
                   point (wild best reads: -0.55 -0.51 -0.30 ... 0.82 —
                   twenty files between -0.55 and 0.82 where the probe's
                   genuine minimum is 1.21, median 2.86, and the modern
                   lab arms read 1.63..5.92 like genuine). The same 34
                   files read 0/34 under the 3.100 probe at the best of
                   all 576 phases (PS3). The fixed point was never
                   destroyed by the mastering chain: the probe was two
                   steps away — generation AND route — and the wilds sat
                   at THEIR encoder's fixed point the whole time.
    EB4  HELD      20 of 23 recovered wilds best on lame3.90.3, 3 on
                   lame3.97 (100 % on the top two rungs): the discs'
                   encoder generation is LAME 3.90.x — the 2002-2004
                   "--alt-preset" era build, read off the audio.

    Phase note: the wilds' best canonical phases under 3.90.3 split 529 x14
    / 0 x10 / 47 x10; the 14 at 529 are untrimmed decodes by his rule. The
    full 576 search ran under 3.92 only (as registered); the 14 wilds still
    above 3.90.3's bar (1.09..5.12) were not searched under 3.90.3 and are
    the obvious next registration. The cross-probe phase-identity check
    (0/34) compares canonical-phase argmins between probes whose reads
    differ by near-ties and says nothing about his one-grid claim; a real
    test needs the full search under two probes on the same file.

WHAT THIS REVERSES. The L-series, the remaster arm and PS3 all read the wild
idem through a 3.100-via-ffmpeg probe and concluded the mastering chain had
moved the wilds off the fixed point. It had not. The remaster arm's layer 1
("limiter -> fixed point") remains a real effect on OUR arm (PS4 measured it
at the right phase: 1.99 median vs arms ~1.0), but it was never the
explanation of W4. W4's explanation, now measured: version lock + route lock,
his finding, whole. Dated amendments go where the old sentences live
(ml/idem_phase_probe.py, ml/remaster_arm.py, the W preregistration).
"""

from __future__ import annotations

import argparse
import csv
import glob
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from idem_phase_probe import CANONICAL, PERIOD, crop  # noqa: E402
from mp3_idem_probe import dist, require_ffmpeg  # noqa: E402

LAME_ROOT = Path(r"C:\Users\loutr\provir_encoders_r2\Encoders\LAME")
PROBES: Dict[str, Path] = {
    "lame3.90.3": LAME_ROOT / "lame3.90.3" / "lame.exe",
    "lame3.92": LAME_ROOT / "lame3.92" / "lame.exe",
    "lame3.93.1": LAME_ROOT / "lame3.93.1r" / "lame.exe",
    "lame3.96.1": LAME_ROOT / "lame3.96.1" / "lame.exe",
    # The period 3.97 binary will not launch on this Windows (WinError 216);
    # his 2026 MinGW rebuild agrees with it to the decimal on his bench, so
    # that rebuild stands in — the one rung where the rule "never a rebuild"
    # is bent, and it is bent on his measurement, not ours.
    "lame3.97": LAME_ROOT / "lame3.97_mingw64" / "lame.exe",
    "lame3.98.4": LAME_ROOT / "lame3.98.4" / "lame.exe",
    "lame3.100": LAME_ROOT / "lame3.100" / "lame.exe",
}
FULL_SEARCH_PROBE = "lame3.92"
RATE = 44100
EXCERPT_SEC = 30.0
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
}


def _find(exe: Path) -> Path:
    if exe.exists():
        return exe
    hits = list(exe.parent.rglob("lame*.exe"))
    if not hits:
        raise SystemExit(f"no lame exe under {exe.parent}")
    return hits[0]


def lame_roundtrip(audio: np.ndarray, exe: Path, ffmpeg: str) -> Optional[np.ndarray]:
    """decode(lame.exe -b 320 (audio)), files never pipes, judged by size + decode."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        src, enc, dec = work / "in.wav", work / "out.mp3", work / "dec.wav"
        sf.write(str(src), audio, RATE, subtype="PCM_16")
        try:
            subprocess.run(
                [str(exe), "-b", "320", str(src), str(enc)],
                capture_output=True,
                timeout=300,
                cwd=str(work),
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        if not enc.exists() or enc.stat().st_size < 4096:
            return None
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(enc), str(dec)],
            capture_output=True,
        )
        if r.returncode != 0 or not dec.exists():
            return None
        out, rate = sf.read(str(dec), dtype="float32")
    return out if rate == RATE else None


def paired_idem(audio: np.ndarray, exe: Path, ffmpeg: str) -> float:
    b = lame_roundtrip(audio, exe, ffmpeg)
    if b is None:
        return float("nan")
    c = lame_roundtrip(b, exe, ffmpeg)
    if c is None:
        return float("nan")
    d1, _ = dist(audio, b, RATE)
    d2, _ = dist(b, c, RATE)
    if not np.isfinite(d1) or not np.isfinite(d2) or d2 <= 0:
        return float("nan")
    return float(20.0 * np.log10(d1 / d2))


def d1_only(audio: np.ndarray, exe: Path, ffmpeg: str) -> float:
    b = lame_roundtrip(audio, exe, ffmpeg)
    if b is None:
        return float("nan")
    d1, _ = dist(audio, b, RATE)
    return d1


def read_probe(audio: np.ndarray, exe: Path, ffmpeg: str, full: bool) -> dict:
    reads = {k: paired_idem(crop(audio, k), exe, ffmpeg) for k in CANONICAL}
    searched = ""
    if full:
        n = int(SEARCH_SEC * RATE) + PERIOD * 3
        short = audio[:n] if audio.ndim == 1 else audio[:n, :]
        d1s = {}
        for k in range(PERIOD):
            v = d1_only(crop(short, k), exe, ffmpeg)
            if np.isfinite(v):
                d1s[k] = v
        if d1s:
            kb = min(d1s, key=lambda k: d1s[k])
            searched = kb
            if kb not in reads:
                reads[kb] = paired_idem(crop(audio, kb), exe, ffmpeg)
    finite = {k: v for k, v in reads.items() if np.isfinite(v)}
    best = min(finite, key=lambda k: finite[k]) if finite else None
    return {
        "R_phase0": reads.get(0, float("nan")),
        "R_best": finite[best] if best is not None else float("nan"),
        "best_phase": best if best is not None else "",
        "searched_phase": searched,
    }


def load(path: str) -> Optional[np.ndarray]:
    try:
        info = sf.info(path)
        if info.samplerate != RATE:
            return None
        data, _ = sf.read(path, dtype="float32", frames=int(EXCERPT_SEC * RATE))
        return data if data.size else None
    except Exception:
        return None


def selftest(ffmpeg: str) -> int:
    """Known answer: a lame3.92 transcode must read far closer to the 3.92
    probe's fixed point than the fresh source does (E1-prime, re-run)."""
    from mp3_idem_probe import _tonal_mix

    exe = _find(PROBES["lame3.92"])
    fresh = _tonal_mix(20.0)
    transcode = lame_roundtrip(fresh, exe, ffmpeg)
    if transcode is None:
        print("selftest: lame3.92 roundtrip failed")
        return 1
    r_fresh = paired_idem(fresh, exe, ffmpeg)
    r_t = paired_idem(transcode, exe, ffmpeg)
    print(f"selftest: fresh {r_fresh:.2f}  lame3.92-transcode {r_t:.2f}")
    ok = np.isfinite(r_fresh) and np.isfinite(r_t) and r_fresh - r_t >= 3.0
    print("selftest:", "OK" if ok else "ECHEC")
    return 0 if ok else 1


def evaluate(out: Path) -> int:
    """EB1-EB4 from the results CSV; every bar is the probe's own lawful minimum."""
    from collections import Counter, defaultdict

    rows = list(csv.DictReader(open(out, newline="", encoding="utf-8")))
    reads = defaultdict(dict)  # (pop, path) -> probe -> R_best
    phases = defaultdict(dict)
    for r in rows:
        if r["R_best"] != "nan":
            reads[(r["population"], r["path"])][r["probe"]] = float(r["R_best"])
            phases[(r["population"], r["path"])][r["probe"]] = r["best_phase"]
    probes = list(PROBES)
    bars = {}
    print(f"{'probe':12}{'lawful bar':>11}{'arms>bar':>10}{'arms<bar':>10}{'wild<bar':>10}")
    wild_below = defaultdict(set)
    for p in probes:
        gen = [v[p] for (pop, _), v in reads.items() if pop == "genuine_bar" and p in v]
        if not gen:
            continue
        bar = min(gen)
        bars[p] = bar
        arms = [v[p] for (pop, _), v in reads.items() if pop == "arms_control" and p in v]
        wild = {path: v[p] for (pop, path), v in reads.items() if pop == "wild_owner" and p in v}
        above = sum(a > bar for a in arms)
        below = sum(a < bar for a in arms)
        wb = {path for path, v in wild.items() if v < bar}
        wild_below[p] = wb
        print(
            f"{p:12}{bar:>11.2f}{above:>7}/{len(arms):<2}{below:>7}/{len(arms):<2}{len(wb):>7}/{len(wild):<2}"
        )

    era = [p for p in probes if p != "lame3.100" and p in bars]
    eb2_era = all(
        sum(v[p] > bars[p] for (pop, _), v in reads.items() if pop == "arms_control" and p in v)
        >= 7
        for p in era
    )
    arms100 = [
        v["lame3.100"]
        for (pop, _), v in reads.items()
        if pop == "arms_control" and "lame3.100" in v
    ]
    eb2_100 = sum(a < bars.get("lame3.100", float("inf")) for a in arms100) >= 6
    print(
        f"\nEB2 era probes blind to Lavc-3.100 arms (>=7/8 above bar, every era rung): {'HELD' if eb2_era else 'FAILED'}"
    )
    print(
        f"EB2 lame.exe-3.100 probe sees them (>=6/8 below its bar): {'HELD' if eb2_100 else 'FAILED'}"
    )

    recovered = set().union(*wild_below.values()) if wild_below else set()
    print(
        f"\nEB3 wilds below SOME probe's bar at best phase: {len(recovered)}/34 (bar >= 2): "
        f"{'HELD' if len(recovered) >= 2 else 'FAILED'}"
    )
    for path in sorted(recovered):
        v = reads[("wild_owner", path)]
        best_p = min((p for p in v if p in bars), key=lambda p: v[p] - bars[p])
        print(f"   {path[:44]:44} best rung {best_p:11} R={v[best_p]:.2f} (bar {bars[best_p]:.2f})")
    if len(recovered) >= 2:
        rungs = Counter()
        for path in recovered:
            v = reads[("wild_owner", path)]
            rungs[min((p for p in v if p in bars), key=lambda p: v[p] - bars[p])] += 1
        top = rungs.most_common(2)
        share = sum(c for _, c in top) / len(recovered)
        print(
            f"EB4 rung clustering (top two rungs {top} = {share:.0%}, bar >= 60 %): "
            f"{'HELD' if share >= 0.6 else 'FAILED'}"
        )

    # His one-phase claim, checked in passing: does the best canonical phase
    # agree across probes on the same file?
    agree = 0
    n = 0
    for key, ph in phases.items():
        if key[0] != "wild_owner" or len(ph) < 2:
            continue
        n += 1
        agree += len(set(ph.values())) == 1
    print(f"\nbest canonical phase identical across all probes on the same wild file: {agree}/{n}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--probes", nargs="*", default=list(PROBES))
    parser.add_argument("--populations", nargs="*", default=list(POPULATIONS))
    args = parser.parse_args(argv)
    ffmpeg = require_ffmpeg()
    if args.selftest:
        return selftest(ffmpeg)
    if not args.out:
        parser.error("--out requis")
    out = Path(args.out)
    if args.evaluate:
        return evaluate(out)
    exes = {name: _find(PROBES[name]) for name in args.probes}

    done = set()
    if out.exists():
        with open(out, newline="", encoding="utf-8") as fh:
            done = {(r["population"], r["path"], r["probe"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lectures", flush=True)
    fields = ["population", "path", "probe", "R_phase0", "R_best", "best_phase", "searched_phase"]
    with open(out, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not done:
            writer.writeheader()
        for pop in args.populations:
            patterns, limit = POPULATIONS[pop]
            paths: List[str] = []
            for pattern in patterns:
                paths.extend(sorted(glob.glob(pattern)))
            paths = list(dict.fromkeys(paths))[:limit]
            for path in paths:
                name = Path(path).name
                audio = None
                for probe, exe in exes.items():
                    if (pop, name, probe) in done:
                        continue
                    if audio is None:
                        audio = load(path)
                        if audio is None:
                            break
                    full = probe == FULL_SEARCH_PROBE and pop == "wild_owner"
                    row = read_probe(audio, exe, ffmpeg, full)
                    row.update({"population": pop, "path": name, "probe": probe})
                    row["R_phase0"] = (
                        f"{row['R_phase0']:.2f}" if np.isfinite(row["R_phase0"]) else "nan"
                    )
                    row["R_best"] = f"{row['R_best']:.2f}" if np.isfinite(row["R_best"]) else "nan"
                    writer.writerow(row)
                    fh.flush()
                    print(
                        f"[{pop}] {name[:40]:40} {probe:11} R0={row['R_phase0']:>6} Rbest={row['R_best']:>6} ph={row['best_phase']}",
                        flush=True,
                    )
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
