#!/usr/bin/env python3
"""Which LAME BUILD made this? — Provir's encoder collection, executed at last.

Predictions E1-E4 registered first, before this ran, in
``ml/exchange/ERA_ATTRIBUTION_REGISTRATION_2026-08-31.md``.

Layer one asked which codec family; this asks which build. The binaries are
Provir's, from his second delivery (2026-08-22), archived on receipt and never
executed here until now — and verified byte-for-byte against his own
``SHA256SUMS.txt`` by ``--verify`` before anything is encoded: 5 of 5 exact.

The instrument: six genuine excerpts, each encoded at CBR 320 by each of five
builds and decoded back, then every resulting file read under all five builds as
probes. R at the best of the canonical phases {0, 529, 47} — never phase 0
alone, the fixed point being grid-locked with period 576. The decoder is held
constant (ffmpeg) so the only variable across probes is the encoder.

Usage::

    python ml/era_attribution_probe.py --verify
    python ml/era_attribution_probe.py --out ml/era_attribution_probe.csv
    python ml/era_attribution_probe.py --score ml/era_attribution_probe.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))

from idem_phase_probe import CANONICAL, crop  # noqa: E402
from mp3_idem_probe import dist  # noqa: E402

COLLECTION = Path(r"C:\Users\loutr\provir_encoders_r2\Encoders")
AUTHENTIC = Path(r"C:\Users\loutr\audit_corpus\authentic")

BUILDS: Tuple[str, ...] = ("lame3.90.3", "lame3.92", "lame3.96.1", "lame3.98.4", "lame3.100")
EARLY = ("lame3.90.3", "lame3.92", "lame3.96.1")  # the era grouping for E3
SIBLINGS = ("lame3.90.3", "lame3.92")  # one codebase generation apart; see E2

N_SOURCES = 6
EXCERPT_SEC = 20.0
FIELDS = ["file", "made_by", "attributed", "min_R"] + [f"R_{b}" for b in BUILDS]


def build_exe(name: str) -> Path:
    return COLLECTION / "LAME" / name / "lame.exe"


def verify() -> int:
    """Every binary this script will run, checked against HIS manifest."""
    sums: Dict[str, str] = {}
    for line in (
        (COLLECTION / "SHA256SUMS.txt").read_text(encoding="utf-8", errors="replace").splitlines()
    ):
        parts = line.split("  ", 1)
        if len(parts) == 2:
            sums[parts[1].strip().replace("\\", "/")] = parts[0]
    ok = True
    for name in BUILDS:
        rel = f"LAME/{name}/lame.exe"
        path = COLLECTION / rel
        if not path.exists():
            print(f"  ABSENT {rel}")
            ok = False
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        want = sums.get(rel)
        if want is None:
            print(f"  NOT IN MANIFEST {rel}")
            ok = False
        elif want != digest:
            print(f"  DIVERGENT {rel}: manifest {want[:16]} != {digest[:16]}")
            ok = False
        else:
            print(f"  OK {name:12s} {digest[:16]}…")
    print("verify: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed ({proc.returncode}): {proc.stderr[-200:]}")


def roundtrip(audio: np.ndarray, rate: int, work: Path, tag: str, build: str) -> np.ndarray:
    """decode(encode(audio)) with ONE build as the encoder, ffmpeg as the decoder.

    Files rather than pipes, as everywhere in this project: a seekable output
    lets the encoder finalise its header, and without that the decoder does not
    recover the encoder delay and R vanishes. The decoder is deliberately the
    same for every build — the experiment is about encoders.
    """
    src = work / f"{tag}_src.wav"
    enc = work / f"{tag}.mp3"
    dec = work / f"{tag}_dec.wav"
    sf.write(str(src), audio, rate, subtype="PCM_16")
    _run([str(build_exe(build)), "-b", "320", "--quiet", str(src), str(enc)])
    _run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(enc),
            "-ar",
            str(rate),
            "-c:a",
            "pcm_s16le",
            str(dec),
        ]
    )
    out, _rate = sf.read(str(dec), dtype="float32")
    return out


def idem_R(audio: np.ndarray, rate: int, build: str) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        b = roundtrip(audio, rate, work, "p1", build)
        c = roundtrip(b, rate, work, "p2", build)
    d1, _ = dist(audio, b, rate)
    d2, _ = dist(b, c, rate)
    if not np.isfinite(d1) or not np.isfinite(d2) or d2 <= 0:
        return float("nan")
    return float(20.0 * np.log10(d1 / d2))


def read_all_probes(path: Path) -> Dict[str, float]:
    audio, rate = sf.read(str(path), dtype="float32")
    audio = audio[: int(EXCERPT_SEC * rate)]
    out: Dict[str, float] = {}
    for build in BUILDS:
        reads = []
        for k in CANONICAL:
            try:
                reads.append(idem_R(crop(audio, k), int(rate), build))
            except Exception:
                reads.append(float("nan"))
        finite = [r for r in reads if np.isfinite(r)]
        out[f"R_{build}"] = min(finite) if finite else float("nan")
    return out


def run(out_path: Path) -> int:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not on PATH")
    if verify() != 0:
        raise SystemExit("binaries do not match his manifest — nothing is executed")

    sources = sorted(AUTHENTIC.glob("*.flac"))[:N_SOURCES]
    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {(r["file"], r["made_by"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for index, src in enumerate(sources, 1):
                audio, rate = sf.read(str(src), dtype="float32")
                audio = audio[: int(EXCERPT_SEC * rate)]
                # The genuine master itself, as E4's control.
                if (src.name, "genuine") not in done:
                    reads = read_all_probes(src)
                    finite = {k: v for k, v in reads.items() if np.isfinite(v)}
                    best = min(finite, key=lambda k: finite[k]) if finite else "R_none"
                    writer.writerow(
                        {
                            "file": src.name,
                            "made_by": "genuine",
                            "attributed": best.removeprefix("R_"),
                            "min_R": f"{finite.get(best, float('nan')):.4f}",
                            **{k: f"{v:.4f}" for k, v in reads.items()},
                        }
                    )
                    fh.flush()
                for build in BUILDS:
                    if (src.name, build) in done:
                        continue
                    made = work / f"{src.stem[:20]}_{build}.flac"
                    decoded = roundtrip(audio, int(rate), work, f"mk_{build}", build)
                    sf.write(str(made), decoded, int(rate), subtype="PCM_16")
                    reads = read_all_probes(made)
                    finite = {k: v for k, v in reads.items() if np.isfinite(v)}
                    best = min(finite, key=lambda k: finite[k]) if finite else "R_none"
                    writer.writerow(
                        {
                            "file": src.name,
                            "made_by": build,
                            "attributed": best.removeprefix("R_"),
                            "min_R": f"{finite.get(best, float('nan')):.4f}",
                            **{k: f"{v:.4f}" for k, v in reads.items()},
                        }
                    )
                    fh.flush()
                    print(
                        f"  {index}/{len(sources)} {build} -> {best.removeprefix('R_')}", flush=True
                    )
    print(f"ecrit {out_path}")
    return 0


def score(csv_path: Path) -> int:  # noqa: C901
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    encoded = [r for r in rows if r["made_by"] != "genuine"]
    genuine = [r for r in rows if r["made_by"] == "genuine"]
    if not encoded:
        print("csv vide")
        return 1
    held: Dict[str, bool] = {}

    hits = sum(1 for r in encoded if r["attributed"] == r["made_by"])
    held["E1"] = hits >= 20
    print(
        f"E1 build exact: {hits}/{len(encoded)} (borne 20, hasard 6) "
        f"{'TENU' if held['E1'] else 'ECHEC'}"
    )

    sib = [r for r in encoded if r["made_by"] in SIBLINGS]
    pair_hits = sum(1 for r in sib if r["attributed"] in SIBLINGS)
    member_hits = sum(1 for r in sib if r["attributed"] == r["made_by"])
    held["E2"] = pair_hits >= 10 and member_hits <= 9
    print(
        f"E2 paire 3.90.3/3.92 inseparable: paire {pair_hits}/{len(sib)} (borne >=10), "
        f"membre {member_hits}/{len(sib)} (borne <=9) {'TENU' if held['E2'] else 'ECHEC'}"
    )

    def era(name: str) -> str:
        return "early" if name in EARLY else "late"

    era_hits = sum(1 for r in encoded if era(r["attributed"]) == era(r["made_by"]))
    held["E3"] = era_hits >= 24
    print(
        f"E3 ere correcte: {era_hits}/{len(encoded)} (borne 24) "
        f"{'TENU' if held['E3'] else 'ECHEC'}"
    )

    self_pairs = [
        float(r[f"R_{r['made_by']}"]) for r in encoded if np.isfinite(float(r[f"R_{r['made_by']}"]))
    ]
    worst_encoded = max(self_pairs) if self_pairs else float("nan")
    below = [
        r for r in genuine if np.isfinite(float(r["min_R"])) and float(r["min_R"]) < worst_encoded
    ]
    held["E4"] = not below
    print(
        f"E4 masters au-dessus du pire auto-appariement ({worst_encoded:.3f}): "
        f"{len(below)}/{len(genuine)} en dessous (borne 0) {'TENU' if held['E4'] else 'ECHEC'}"
    )

    print("\nmatrice (lignes = build reel, colonnes = attribue):")
    print(f"{'made_by':12s} " + " ".join(f"{b.replace('lame', ''):>8s}" for b in BUILDS))
    for made in ("genuine",) + BUILDS:
        sub = [r for r in rows if r["made_by"] == made]
        if not sub:
            continue
        counts = {b: sum(1 for r in sub if r["attributed"] == b) for b in BUILDS}
        print(f"{made:12s} " + " ".join(f"{counts[b]:8d}" for b in BUILDS))

    failed = [k for k, v in held.items() if not v]
    print("\n" + ("TOUT TENU" if not failed else "ECHECS: " + ", ".join(failed)))
    return 0 if not failed else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--score", type=Path)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args(argv)
    if args.verify:
        return verify()
    if args.score:
        return score(args.score)
    if not args.out:
        ap.error("--out, --score ou --verify")
    return run(args.out)


if __name__ == "__main__":
    sys.exit(main())
