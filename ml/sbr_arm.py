#!/usr/bin/env python3
"""The blind spot with energy above the cliff: spectral band replication.

Why
---
Every cutoff-shaped rule in this engine rests on the same physical story: a lossy
encoder throws the top of the spectrum away, so a wall low in the band is
evidence of an encoder. SBR breaks that story. An SBR encoder codes the lower
half properly and **resynthesises the upper half from a handful of parameters**,
so the file arrives with energy all the way up — energy that was never in the
master.

Measured here before this file was written, on one 30 s excerpt:

    source lossless        22050 Hz
    HE-AAC (SBR)  64 kbps  20448 Hz     <- the trap
    AAC-LC ffmpeg 128 kbps 17288 Hz
    MP3 LAME      64 kbps  11274 Hz

A 64 kbps file reaching higher than an AAC-LC file at double the rate, and 9 kHz
higher than an MP3 at the same rate. Anything that reads "content up to 20 kHz"
as "not truncated" will call that file clean.

This matters beyond HE-AAC. mp3PRO is the same technology under another name, and
Provir has just acquired a copy of it after a year of not being able to find one,
so the arm is about to exist on his side whether or not it exists on ours. Better
to know now what this engine does with it.

What this measures
------------------
Paired, not pooled: every source is scored untouched *and* after each round trip,
so the genuine baseline and the transcode come from the same music and a verdict
difference cannot be a difference of material.

Arms: HE-AAC at 32/48/64 kbps via MediaFoundation (Windows ships the only SBR
encoder available on this machine — there is no libfdk_aac in this ffmpeg), plus
three non-SBR controls at neighbouring rates. Without the controls a poor result
on the SBR arms could just mean "low bitrate is hard".

Guards, because an arm that silently becomes a different arm is this project's
most expensive recurring mistake
--------------------------------------------------------------------------------
1. **Profile check.** Every SBR encode is interrogated with ffprobe and must
   declare ``HE-AAC``. MediaFoundation chooses the profile from the bitrate, so a
   rate that quietly produced AAC-LC would turn this into a second LC arm
   reporting a reassuring number about nothing.
2. **Ceiling check.** Each SBR arm's measured spectral ceiling must exceed its
   own AAC-LC control's. That is the property being tested; if it is absent the
   encode did not do the thing this file exists to examine, and the row says so
   rather than being averaged in.

Usage::

    python ml/sbr_arm.py --sources C:/Users/loutr/fd-pistes-completes \
        --n 6 --out ml/sbr_arm.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

EXCERPT_START_S = 30.0
EXCERPT_LENGTH_S = 60.0
CEILING_FLOOR_DB = -90.0

# (arm, ffmpeg encoder args, container suffix, expected ffprobe profile or None)
ARMS: Tuple[Tuple[str, List[str], str, Optional[str]], ...] = (
    ("he_aac_32k", ["-c:a", "aac_mf", "-b:a", "32k"], ".m4a", "HE-AAC"),
    ("he_aac_48k", ["-c:a", "aac_mf", "-b:a", "48k"], ".m4a", "HE-AAC"),
    ("he_aac_64k", ["-c:a", "aac_mf", "-b:a", "64k"], ".m4a", "HE-AAC"),
    ("lc_aac_32k", ["-c:a", "aac", "-b:a", "32k"], ".m4a", "LC"),
    ("lc_aac_48k", ["-c:a", "aac", "-b:a", "48k"], ".m4a", "LC"),
    ("lc_aac_64k", ["-c:a", "aac", "-b:a", "64k"], ".m4a", "LC"),
    ("lc_aac_128k", ["-c:a", "aac", "-b:a", "128k"], ".m4a", "LC"),
    ("mp3_64k", ["-c:a", "libmp3lame", "-b:a", "64k"], ".mp3", None),
)

SBR_ARMS = ("he_aac_32k", "he_aac_48k", "he_aac_64k")

# Each SBR arm is checked against a non-SBR arm AT THE SAME BITRATE. The first
# run of this file used one control for all three and the guard refused two arms
# — correctly, because comparing 32 kbps SBR with 128 kbps AAC-LC asks whether
# SBR beats four times the bitrate, which is not the claim. The claim is that at
# a GIVEN rate, SBR fills higher than not-SBR.
CEILING_CONTROLS = {
    "he_aac_32k": "lc_aac_32k",
    "he_aac_48k": "lc_aac_48k",
    "he_aac_64k": "lc_aac_64k",
}


def run(args: List[str]) -> None:
    subprocess.run(args, check=True, capture_output=True)


def excerpt(src: Path, out: Path) -> None:
    """A fixed 60 s excerpt, so every arm sees exactly the same audio."""
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{EXCERPT_START_S:g}",
            "-t",
            f"{EXCERPT_LENGTH_S:g}",
            "-i",
            str(src),
            "-c:a",
            "flac",
            str(out),
        ]
    )


def round_trip(
    source_flac: Path, encoder_args: List[str], suffix: str, work: Path, stem: str
) -> Tuple[Path, Path]:
    """Encode then decode back to FLAC. Returns (encoded, decoded)."""
    encoded = work / f"{stem}{suffix}"
    decoded = work / f"{stem}__decoded.flac"
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_flac),
            *encoder_args,
            str(encoded),
        ]
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(encoded),
            "-c:a",
            "flac",
            str(decoded),
        ]
    )
    return encoded, decoded


def declared_profile(path: Path) -> str:
    """What the container says the codec profile is, or '' if it says nothing."""
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=profile",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def spectral_ceiling(path: Path, floor_db: float = CEILING_FLOOR_DB) -> float:
    """Highest frequency still above ``floor_db`` relative to the spectral peak.

    Deliberately not the engine's own ``detect_cutoff``: checking a claim about
    the engine with the engine's own instrument only proves the instrument is
    self-consistent. This is a plain averaged periodogram and nothing else.
    """
    import numpy as np
    import soundfile as sf

    data, rate = sf.read(str(path), dtype="float64")
    mono = data.mean(axis=1) if getattr(data, "ndim", 1) > 1 else data
    size = 1 << 15
    if len(mono) < size:
        return 0.0
    window = np.hanning(size)
    accumulator = np.zeros(size // 2 + 1)
    blocks = 0
    for start in range(0, len(mono) - size, size):
        accumulator += np.abs(np.fft.rfft(mono[start : start + size] * window)) ** 2
        blocks += 1
    psd = 10 * np.log10(accumulator / max(blocks, 1) + 1e-30)
    psd -= psd.max()
    freqs = np.fft.rfftfreq(size, 1.0 / rate)
    above = np.flatnonzero(psd > floor_db)
    return float(freqs[above[-1]]) if above.size else 0.0


def score(analyzer, path: Path) -> Dict:
    try:
        result = analyzer.analyze_file(str(path))
        return {
            "verdict": result.get("verdict", "?"),
            "score": result.get("score", ""),
            "cutoff_hz": result.get("cutoff_freq", ""),
            "families": "|".join(result.get("evidence_families", []) or []),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "verdict": f"ECHEC:{type(exc).__name__}",
            "score": "",
            "cutoff_hz": "",
            "families": "",
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=Path, required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    logging.disable(logging.CRITICAL)
    from flac_detective.analysis.analyzer import FLACAnalyzer

    sources = sorted(args.sources.rglob("*.flac"))[: args.n]
    if not sources:
        raise SystemExit(f"aucune source sous {args.sources}")
    print(f"{len(sources)} sources, {len(ARMS)} bras + le controle genuine", flush=True)

    analyzer = FLACAnalyzer(sample_duration=EXCERPT_LENGTH_S, deep=True)
    rows: List[Dict] = []
    profile_failures: List[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for index, src in enumerate(sources, 1):
            clean = work / f"src{index:02d}.flac"
            excerpt(src, clean)

            measured = score(analyzer, clean)
            rows.append(
                {
                    "source": src.name,
                    "arm": "genuine",
                    "profile": "",
                    "ceiling_hz": round(spectral_ceiling(clean)),
                    **measured,
                }
            )
            print(
                f"  {index}/{len(sources)} {src.name[:48]:48s} genuine      "
                f"{measured['verdict']:13s} plafond {rows[-1]['ceiling_hz']:5d} Hz",
                flush=True,
            )

            for arm, encoder_args, suffix, expected in ARMS:
                encoded, decoded = round_trip(
                    clean, encoder_args, suffix, work, f"src{index:02d}_{arm}"
                )
                profile = declared_profile(encoded)
                if expected and expected not in profile:
                    profile_failures.append(
                        f"{src.name} / {arm}: profil '{profile}' au lieu de '{expected}'"
                    )
                measured = score(analyzer, decoded)
                ceiling = round(spectral_ceiling(decoded))
                rows.append(
                    {
                        "source": src.name,
                        "arm": arm,
                        "profile": profile,
                        "ceiling_hz": ceiling,
                        **measured,
                    }
                )
                print(
                    f"      {arm:12s} {profile:8s} {measured['verdict']:13s} "
                    f"score {str(measured['score']):>3s}  plafond {ceiling:5d} Hz  "
                    f"arete lue {measured['cutoff_hz']}",
                    flush=True,
                )
                encoded.unlink(missing_ok=True)
                decoded.unlink(missing_ok=True)
            clean.unlink(missing_ok=True)

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report(rows, profile_failures)
    print(f"ecrit {args.out}", flush=True)
    return 0


def missed(rows: List[Dict], arm: str) -> Tuple[int, int]:
    """(files read AUTHENTIC, files in the arm) — the recall hole, per arm."""
    in_arm = [r for r in rows if r["arm"] == arm]
    return sum(1 for r in in_arm if r["verdict"] == "AUTHENTIC"), len(in_arm)


def report(rows: List[Dict], profile_failures: List[str]) -> None:
    """Recall per arm, and the two guards that decide whether it can be read."""
    arms = [a for a, _, _, _ in ARMS]

    print("\n" + "=" * 78)
    print("GARDE 1 - les bras SBR sont-ils vraiment du SBR ?")
    print("=" * 78)
    if profile_failures:
        for failure in profile_failures:
            print(f"  ! {failure}")
        print("  -> ces bras ne mesurent pas ce qu'ils annoncent. Ne rien en conclure.")
    else:
        print("  tous les encodages HE-AAC declarent bien le profil HE-AAC.")

    print("\nGARDE 2 - a debit egal, le SBR remplit-il plus haut que le non-SBR ?")
    for arm in SBR_ARMS:
        control_arm = CEILING_CONTROLS[arm]
        values = [r["ceiling_hz"] for r in rows if r["arm"] == arm]
        control = [r["ceiling_hz"] for r in rows if r["arm"] == control_arm]
        mean = sum(values) / len(values) if values else 0.0
        control_mean = sum(control) / len(control) if control else 0.0
        if not values or not control:
            verdict = "INDECIDABLE - un des deux bras est vide"
        elif mean > control_mean:
            verdict = "OK"
        else:
            verdict = "NON - le bras n'a pas fait ce qu'il pretend"
        print(
            f"  {arm:12s} {mean:8.0f} Hz  contre  {control_arm:12s} {control_mean:8.0f} Hz   {verdict}"
        )

    print("\n" + "=" * 78)
    print("CE QUE LE MOTEUR EN FAIT — fichiers lus AUTHENTIC alors qu'ils sont encodes")
    print("=" * 78)
    genuine_missed, genuine_total = missed(rows, "genuine")
    print(
        f"  {'genuine (controle)':14s} {genuine_missed}/{genuine_total} lus AUTHENTIC "
        f"— doit valoir {genuine_total}/{genuine_total}"
    )
    for arm in arms:
        hole, total = missed(rows, arm)
        ceilings = [r["ceiling_hz"] for r in rows if r["arm"] == arm]
        mean = sum(ceilings) / len(ceilings) if ceilings else 0.0
        tag = "  <-- ANGLE MORT" if arm in SBR_ARMS and hole else ""
        print(f"  {arm:14s} {hole}/{total} lus AUTHENTIC   plafond moyen {mean:6.0f} Hz{tag}")

    print("\n  L'ARETE LUE CONTRE LE PLAFOND REEL (le coeur du piege)")
    for arm in arms:
        pairs = [
            (r["cutoff_hz"], r["ceiling_hz"])
            for r in rows
            if r["arm"] == arm and isinstance(r["cutoff_hz"], (int, float))
        ]
        if not pairs:
            continue
        read_mean = sum(c for c, _ in pairs) / len(pairs)
        real_mean = sum(t for _, t in pairs) / len(pairs)
        print(f"  {arm:14s} arete lue {read_mean:8.0f} Hz   plafond reel {real_mean:8.0f} Hz")


if __name__ == "__main__":
    raise SystemExit(main())
