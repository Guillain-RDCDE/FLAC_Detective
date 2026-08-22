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
RESULTS
(not yet run)
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
    "lame3.97": LAME_ROOT / "lame3.97" / "lame.exe",
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
            subprocess.run([str(exe), "-b", "320", str(src), str(enc)],
                           capture_output=True, timeout=300, cwd=str(work))
        except subprocess.TimeoutExpired:
            return None
        if not enc.exists() or enc.stat().st_size < 4096:
            return None
        r = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(enc), str(dec)], capture_output=True)
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


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
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
                    row["R_phase0"] = f"{row['R_phase0']:.2f}" if np.isfinite(row["R_phase0"]) else "nan"
                    row["R_best"] = f"{row['R_best']:.2f}" if np.isfinite(row["R_best"]) else "nan"
                    writer.writerow(row)
                    fh.flush()
                    print(f"[{pop}] {name[:40]:40} {probe:11} R0={row['R_phase0']:>6} Rbest={row['R_best']:>6} ph={row['best_phase']}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
