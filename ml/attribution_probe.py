#!/usr/bin/env python3
"""Which encoder family made this transcode? — the bank-of-probes instrument.

Predictions A1-A5 registered first, before this ran, in
``ml/exchange/ATTRIBUTION_REGISTRATION_2026-08-30.md``.

Every tool in this space answers *is this a transcode?*. This asks **by what?**
The idea is Provir's family lock (his bench, adopted 2026-08-22): a LAME file
drops under the LAME probe at its true phase while Fraunhofer arms stay high at
every phase. A probe is therefore a probe **of one family**, and a bank of them
is an attribution instrument: the file belongs to whichever probe it falls
furthest under.

Five probes, one per family available in this ffmpeg::

    mp3       libmp3lame -b:a 320k
    aac       ffmpeg native aac -b:a 256k
    vorbis    libvorbis -q:a 8
    opus      libopus -b:a 256k
    mp2       libtwolame -b:a 256k        (MPEG-1 Layer II, the v2 blind spot)

Each read is the same two-round-trip R the MP3 probe already computes
(``20*log10(d1/d2)``), taken at the best of the canonical phases {0, 529, 47} —
never at phase 0 alone, because the fixed point is grid-locked with period 576
and zero tolerance.

Usage::

    python ml/attribution_probe.py --out ml/attribution_probe.csv --n 12
    python ml/attribution_probe.py --score ml/attribution_probe.csv
"""

from __future__ import annotations

import argparse
import csv
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

CORPUS = Path(r"C:\Users\loutr\audit_corpus")

# 20 seconds of each 60-second excerpt. Five probes at three phases is thirty
# encoder round-trips per file, and the smoke test measured ~25 s of that on a
# 20-second window: the full excerpt would put this run past four hours for no
# extra separation (the first smoke read mp3 at -0.49 against 2.5-14.4 for every
# other family, a margin that does not need more audio). Stated here rather than
# discovered later, because a duration is an instrument setting like any other.
EXCERPT_SEC = 20.0

# (family, encoder, container, args). The container matters: an encoder writing
# into a seekable file finalises its header, which is what lets the decoder
# recover the encoder delay. The MP3 probe learned that the hard way.
PROBES: Tuple[Tuple[str, str, str, Tuple[str, ...]], ...] = (
    ("mp3", "libmp3lame", "mp3", ("-b:a", "320k")),
    ("aac", "aac", "m4a", ("-b:a", "256k")),
    ("vorbis", "libvorbis", "ogg", ("-q:a", "8")),
    ("opus", "libopus", "opus", ("-b:a", "256k")),
    ("mp2", "libtwolame", "mp2", ("-b:a", "256k")),
)

# The populations, and which family each one SHOULD be attributed to.
POPULATIONS: Tuple[Tuple[str, str], ...] = (
    ("authentic", ""),  # no family: a master has no filterbank to match
    ("fake/mp3_320", "mp3"),
    ("fake/aac_ff256", "aac"),
    ("fake/aacmf_256", "aac"),  # different encoder, same codec — A3
    ("fake/opus_256", "opus"),
    ("fake/vorbis_q8", "vorbis"),
)

FIELDS = ["file", "population", "expected", "attributed", "spread"] + [
    f"R_{name}" for name, _, _, _ in PROBES
]


def require_ffmpeg() -> str:
    """ffmpeg carrying every probe encoder, or a precise refusal."""
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg not found on PATH")
    out = subprocess.run([exe, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    missing = [enc for _, enc, _, _ in PROBES if enc not in out]
    if missing:
        raise SystemExit(f"this ffmpeg lacks the probe encoders: {missing}")
    return exe


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed ({proc.returncode}): {proc.stderr[-200:]}")


def roundtrip(
    audio: np.ndarray, rate: int, work: Path, tag: str, ffmpeg: str, probe: Tuple
) -> np.ndarray:
    """decode(encode(audio)) through one family, via FILES on disk.

    Files rather than pipes for the same reason the MP3 probe uses them: a
    seekable output lets the encoder finalise its header, and without that the
    decoder does not recover the encoder delay and R vanishes.

    The decode forces the SOURCE rate back — Opus works at 48 kHz whatever it is
    fed, and a probe that returned a resampled signal would be measuring the
    resampler.
    """
    _name, encoder, ext, args = probe
    src = work / f"{tag}_src.wav"
    enc = work / f"{tag}.{ext}"
    dec = work / f"{tag}_dec.wav"
    sf.write(str(src), audio, rate, subtype="PCM_16")
    _run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-c:a",
            encoder,
            *args,
            str(enc),
        ]
    )
    _run(
        [
            ffmpeg,
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


def idem_R(audio: np.ndarray, rate: int, ffmpeg: str, probe: Tuple) -> float:
    """The two-round-trip ratio under one family's probe. NaN is an abstention."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        b = roundtrip(audio, rate, work, "p1", ffmpeg, probe)
        c = roundtrip(b, rate, work, "p2", ffmpeg, probe)
    d1, _ = dist(audio, b, rate)
    d2, _ = dist(b, c, rate)
    if not np.isfinite(d1) or not np.isfinite(d2) or d2 <= 0:
        return float("nan")
    return float(20.0 * np.log10(d1 / d2))


def read_file(path: Path, ffmpeg: str) -> Dict[str, float]:
    """R under every probe, each at its own best canonical phase."""
    audio, rate = sf.read(str(path), dtype="float32")
    audio = audio[: int(EXCERPT_SEC * rate)]
    out: Dict[str, float] = {}
    for probe in PROBES:
        name = probe[0]
        reads = []
        for k in CANONICAL:
            try:
                reads.append(idem_R(crop(audio, k), int(rate), ffmpeg, probe))
            except Exception:
                reads.append(float("nan"))
        finite = [r for r in reads if np.isfinite(r)]
        out[f"R_{name}"] = min(finite) if finite else float("nan")
    return out


def run(out_path: Path, n_sources: int) -> int:
    ffmpeg = require_ffmpeg()
    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {(r["file"], r["population"]) for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} lignes deja faites", flush=True)

    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for population, expected in POPULATIONS:
            files = sorted((CORPUS / population).glob("*.flac"))[:n_sources]
            for index, path in enumerate(files, 1):
                if (path.name, population) in done:
                    continue
                reads = read_file(path, ffmpeg)
                finite = {k: v for k, v in reads.items() if np.isfinite(v)}
                if finite:
                    best = min(finite, key=lambda k: finite[k])
                    ordered = sorted(finite.values())
                    spread = ordered[1] - ordered[0] if len(ordered) > 1 else float("nan")
                else:
                    best, spread = "R_none", float("nan")
                writer.writerow(
                    {
                        "file": path.name,
                        "population": population,
                        "expected": expected,
                        "attributed": best.removeprefix("R_"),
                        "spread": f"{spread:.4f}",
                        **{k: f"{v:.4f}" for k, v in reads.items()},
                    }
                )
                fh.flush()
                print(
                    f"  {population} {index}/{len(files)} -> {best.removeprefix('R_')}", flush=True
                )
    print(f"ecrit {out_path}")
    return 0


def score(csv_path: Path) -> int:
    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    if not rows:
        print("csv vide")
        return 1
    lossy = [r for r in rows if r["expected"]]
    genuine = [r for r in rows if not r["expected"]]
    held: Dict[str, bool] = {}

    def hit_rate(population: str) -> Tuple[int, int]:
        sub = [r for r in rows if r["population"] == population]
        return sum(1 for r in sub if r["attributed"] == r["expected"]), len(sub)

    hits, total = hit_rate("fake/mp3_320")
    held["A1"] = hits >= 9
    print(
        f"A1 auto-appariement MP3: {hits}/{total} (borne 9/12) {'TENU' if held['A1'] else 'ECHEC'}"
    )

    ok = sum(1 for r in lossy if r["attributed"] == r["expected"])
    rate = ok / len(lossy) if lossy else 0.0
    held["A2"] = rate >= 0.60
    print(
        f"A2 toutes familles: {ok}/{len(lossy)} = {rate:.0%} (borne 60%, hasard 20%) "
        f"{'TENU' if held['A2'] else 'ECHEC'}"
    )

    h_ff, n_ff = hit_rate("fake/aac_ff256")
    h_mf, n_mf = hit_rate("fake/aacmf_256")
    r_ff = h_ff / n_ff if n_ff else float("nan")
    r_mf = h_mf / n_mf if n_mf else float("nan")
    held["A3"] = abs(r_ff - r_mf) <= 0.20
    print(
        f"A3 codec et non encodeur: aac_ff {r_ff:.0%} vs aacmf {r_mf:.0%} "
        f"(ecart {abs(r_ff - r_mf):.0%}, borne 20 pts) {'TENU' if held['A3'] else 'ECHEC'}"
    )

    def spreads(rs) -> List[float]:
        return [float(r["spread"]) for r in rs if r["spread"] not in ("", "nan")]

    g_tight = sum(1 for s in spreads(genuine) if s < 0.5)
    l_wide = sum(1 for s in spreads(lossy) if s >= 0.5)
    held["A4"] = g_tight >= 8 and l_wide > len(spreads(lossy)) / 2
    print(
        f"A4 abstention des masters: {g_tight}/{len(spreads(genuine))} genuine avec un ecart "
        f"< 0.5 (borne 8), et {l_wide}/{len(spreads(lossy))} lossy au-dessus "
        f"{'TENU' if held['A4'] else 'ECHEC'}"
    )

    mp2_wrong = sum(1 for r in lossy if r["attributed"] == "mp2")
    held["A5"] = mp2_wrong <= 2
    print(
        f"A5 pas de Layer II par accident: {mp2_wrong}/{len(lossy)} (borne 2) "
        f"{'TENU' if held['A5'] else 'ECHEC'}"
    )

    print("\nmatrice attribution (lignes = verite, colonnes = attribue):")
    families = [p[0] for p in PROBES]
    print(f"{'population':18s} " + " ".join(f"{f:>7s}" for f in families))
    for population, _expected in POPULATIONS:
        sub = [r for r in rows if r["population"] == population]
        if not sub:
            continue
        counts = {f: sum(1 for r in sub if r["attributed"] == f) for f in families}
        print(f"{population:18s} " + " ".join(f"{counts[f]:7d}" for f in families))

    print(
        "\n"
        + (
            "TOUT TENU"
            if all(held.values())
            else "ECHECS: " + ", ".join(k for k, v in held.items() if not v)
        )
    )
    return 0 if all(held.values()) else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--score", type=Path)
    args = ap.parse_args(argv)
    if args.score:
        return score(args.score)
    if not args.out:
        ap.error("--out ou --score")
    return run(args.out, args.n)


if __name__ == "__main__":
    sys.exit(main())
