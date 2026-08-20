#!/usr/bin/env python3
"""Build and measure a Musepack arm — the axis this project claimed and never earned.

Why this file exists
--------------------
In the first exchange with Jamie Dodd of Provir, FLAC Detective was described as
having a Musepack axis. It did not. What it had was ``6/64`` on a Musepack arm,
which is the CNN's WARNING floor and not evidence of anything: a detector that
flagged nothing at all would post a similar number on any arm where the floor is
non-zero. Claiming an axis from a floor is the same error as quoting a headline
rate that averages two incomparable populations — it reads as a measurement and
is not one.

That claim has been outstanding since 2026-08-13. It is measured here.

Why it took this long, and why it is a CI job
---------------------------------------------
``mpcenc`` is not in winget, not in scoop, and not an ffmpeg encoder — ffmpeg
decodes Musepack SV7 and SV8 but encodes neither. Getting it on Windows means
downloading a third-party binary and running it, which is a poor way to settle a
measurement question.

It is a Debian package. ``musepack-tools`` provides ``mpcenc`` and ``mpcdec`` on
the Ubuntu runner this repository already uses, which makes this the same move as
the CoreAudio arm: the encoder we could not run locally is a job on a free runner,
installed from a distribution archive rather than fetched from a download page.

What is actually being asked
----------------------------
Musepack is not another MDCT codec. It is a **subband** codec — MPEG-1 Layer 2's
32-band polyphase filterbank with a psychoacoustic model rewritten on top. That
matters more than the bitrate does:

* Rule 13 reads MDCT quantisation alignment. Musepack has no MDCT. The honest
  prediction is that Rule 13 reads approximately nothing, and if it reads a lot,
  the rule is responding to something other than what its docstring claims.
* Rule 15 reads dead runs in the side channel. Musepack does use mid/side, so the
  stereo family has a mechanism here — this is where an axis could plausibly live.
* Rule 2 reads the cutoff. Musepack's standard profiles do lowpass, so the
  spectral family should read *something*, and the interesting question is whether
  it reads enough to convict without help.

Predictions, registered here before the job is run, in the exchange's convention:

    P1  Rule 13 (mdct)     AUC below 0.65 on every profile   — no MDCT to align
    P2  Rule 15 (stereo)   AUC above 0.75 on --standard      — mid/side is used
    P3  the spectral cutoff separates on --radio/--telephone and not on --insane

Being wrong on P1 would be the most useful outcome available: it would mean Rule
13 has a second mechanism nobody has named.

CORRECTION 2026-08-21 — the mechanism we gave for P3 was wrong
---------------------------------------------------------------
P3 failed on measurement: the cutoff DOES separate on ``--insane``, at AUC 0.90.
The failure was real and the number is ours. The **explanation** attached to it was
not: this file, and the v1.11.3 release notes, said Musepack "still lowpasses at
18,750 Hz even at its top preset". It does not lowpass at ``--insane`` at all.

Jamie Dodd built ``mpcenc`` from source to check (the upstream CMake build has been
broken under MSVC since 2011 — four defects, one referencing a source file with no
``.c`` extension, so that path can never have been run). ``--insane``'s bandwidth cap
is the full band: 22.1 kHz at 44.1 kHz, 24.0 kHz at 48 kHz, per the encoder's own
report, with three synthetic probes measuring the decoded edge at 22,050.0 Hz.

Where 18,750 comes from is exact, and it is a **48 kHz** number. ``mpcenc.c:1282``
computes bandwidth as ``(Max_Band+1) * (SampleFreq/32/2000)`` kHz — 32 subbands, so
the step is sample-rate dependent:

    48,000 Hz -> 0.750000 kHz/band, Max_Band=24 -> 18,750.00   exact
    44,100 Hz -> 0.689063 kHz/band, Max_Band=26 -> 18,604.69

Verified here against our own data: our sources are 44.1 kHz (the genuine baseline
tops at 22,050 Hz), and at 44.1 kHz a bandwidth of 18,750 Hz would require
``Max_Band+1 = 27.211`` — not an integer, so not a band boundary. Our figure cannot
be a Musepack cap.

His profile ladder at 44.1 kHz is thumb 13.1 / radio 15.8 / standard 20.0 /
extreme 22.1 / insane 22.1 kHz. Our measured medians were radio 16,000 (matching
his cap), standard 17,750 and insane 18,750 — both **below** their caps. So the
separation at ``--insane`` is the encoder zeroing low-level HF content, which is a
real observable, and not a bandwidth limit, which is what we claimed.

His own caveat, volunteered: his probes were synthetic and broadband, and real music
with little HF produces a lower measured edge with no codec lowpass at all. So the
correct statement is "the 18,750 cap does not exist at ``--insane``", not "you
mismeasured".

And a defect of ours that this exposed: 1 file of 24 reads 22,050 Hz at EVERY
profile, including ``--radio`` where a 15.8 kHz cap certainly applies. That reading
is ``detect_cutoff`` failing and returning Nyquist, which it does for "full
spectrum", "bass concentration" and "found nothing" alike. It entered our medians as
if it were a measurement. ``detect_cutoff_detailed`` now separates the sentinel from
the reading; see its ``EdgeReading`` docstring.

Paired, not pooled: every source is measured as-is and after a Musepack round
trip, so the genuine baseline and the transcode are the same music. Same
discipline as the CoreAudio arm.

Usage::

    python ml/musepack_arm.py --src wild_authentic --out ml/musepack_arm.csv
"""

from __future__ import annotations

import argparse
import csv
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from flac_detective.analysis.new_scoring.mdct import best_alignment_stat  # noqa: E402
from flac_detective.analysis.new_scoring.stereo_image import side_dead_run  # noqa: E402
from flac_detective.analysis.spectrum import (  # noqa: E402
    _welch_magnitude_db,
    detect_cutoff,
)

# Musepack quality presets, by name rather than by bitrate — mpcenc is inherently
# VBR and its presets are the interface people actually use. Approximate rates:
#   --telephone ~ 60k, --radio ~ 130k, --standard ~ 180k, --insane ~ 240k
# `--standard` is the one that matters: it is Musepack's transparency claim, and a
# transcode nobody can hear is the only kind worth detecting.
DEFAULT_PROFILES = ("radio", "standard", "insane")

EXCERPT_SEC = 30.0


def require_mpcenc() -> Tuple[str, str]:
    """Return ``(mpcenc, mpcdec)``, or explain precisely why this cannot run here."""
    enc = shutil.which("mpcenc")
    dec = shutil.which("mpcdec")
    if enc and dec:
        return enc, dec
    raise SystemExit(
        f"mpcenc/mpcdec not found (platform={platform.system()}). Musepack has no "
        "ffmpeg encoder and no Windows package manager entry; it ships as the Debian "
        "package `musepack-tools`. Run this on the ubuntu job in "
        ".github/workflows/musepack-arm.yml, which is free for this repository, "
        "rather than fetching a binary from a download page."
    )


def read_excerpt(path: Path, seconds: float = EXCERPT_SEC) -> Tuple[np.ndarray, int]:
    """Read the first ``seconds`` of ``path`` as float32."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(seconds * info.samplerate))
    return data, int(rate)


def _run(cmd: List[str]) -> None:
    """Run ``cmd``, raising with the tool's own message on failure."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({proc.returncode}): {proc.stderr.strip()[:300]}")


def musepack_roundtrip(src_wav: Path, work: Path, profile: str,
                       mpcenc: str, mpcdec: str) -> Path:
    """Encode ``src_wav`` to Musepack at ``profile`` and decode it straight back."""
    encoded = work / f"enc_{profile}.mpc"
    decoded = work / f"dec_{profile}.wav"
    # --overwrite because the work dir is reused per source; mpcenc otherwise
    # prompts, and a prompt in CI is a hang rather than a failure.
    _run([mpcenc, f"--{profile}", "--overwrite", str(src_wav), str(encoded)])
    _run([mpcdec, str(encoded), str(decoded)])
    return decoded


def statistics(path: Path) -> Tuple[float, float, float]:
    """``(mdct_stat, stereo_dead_run, cutoff_hz)`` for one file.

    ``stop_at`` is disabled for the MDCT statistic on purpose: the shipped pipeline
    short-circuits once a reading is good enough to act on, but a calibration wants
    the true value.
    """
    data, rate = read_excerpt(path)
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    mono = np.ascontiguousarray(mono, dtype=np.float32)

    mdct_stat, _, _ = best_alignment_stat(mono, rate, stop_at=float("inf"))

    try:
        run, _ratio = side_dead_run(data, rate)
    except Exception:
        run = float("nan")

    try:
        freq, mag = _welch_magnitude_db(mono.astype(np.float64), rate)
        cutoff = float(detect_cutoff(freq, mag, rate))
    except Exception:
        cutoff = float("nan")

    return float(mdct_stat), float(run), cutoff


def auc(fake: np.ndarray, genuine: np.ndarray) -> float:
    """Mann-Whitney AUC: P(a random fake scores above a random genuine)."""
    fake = fake[np.isfinite(fake)]
    genuine = genuine[np.isfinite(genuine)]
    if not len(fake) or not len(genuine):
        return float("nan")
    values = np.concatenate([fake, genuine])
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(order), dtype=np.float64)
    ranks[order] = np.arange(1, len(order) + 1)
    # Average ranks over ties, or a codec that sits exactly on the null reads high.
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    rank_sum = ranks[: len(fake)].sum()
    return float((rank_sum - len(fake) * (len(fake) + 1) / 2) / (len(fake) * len(genuine)))


def main(argv: Optional[List[str]] = None) -> int:
    """Build the arm and report what each family reads on it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True, help="directory of genuine FLACs")
    parser.add_argument("--out", type=Path, default=Path("ml/musepack_arm.csv"))
    parser.add_argument("--limit", type=int, default=0, help="cap sources (0 = all)")
    parser.add_argument("--profiles", nargs="+", default=list(DEFAULT_PROFILES))
    args = parser.parse_args(argv)

    mpcenc, mpcdec = require_mpcenc()
    sources = sorted(args.src.glob("**/*.flac"))
    if args.limit:
        sources = sources[: args.limit]
    if not sources:
        raise SystemExit(f"no FLAC files under {args.src}")

    print(f"mpcenc: {mpcenc}\nmpcdec: {mpcdec}\nsources: {len(sources)}", flush=True)

    rows: List[dict] = []
    for index, source in enumerate(sources, 1):
        try:
            data, rate = read_excerpt(source)
        except Exception as exc:
            print(f"  [{index}/{len(sources)}] {source.name}: unreadable ({exc})", flush=True)
            continue
        # Musepack is a 44.1/48 kHz consumer codec; hi-res sources would measure the
        # resampler rather than the encoder.
        if rate not in (44100, 48000):
            print(f"  [{index}/{len(sources)}] {source.name}: skip ({rate} Hz)", flush=True)
            continue

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            src_wav = work / "src.wav"
            sf.write(str(src_wav), data, rate, subtype="PCM_16")

            try:
                base_mdct, base_run, base_cut = statistics(src_wav)
            except Exception as exc:
                print(f"  [{index}/{len(sources)}] {source.name}: baseline failed ({exc})",
                      flush=True)
                continue
            rows.append({"source": source.name, "arm": "genuine", "profile": "-",
                         "mdct": base_mdct, "stereo_run": base_run, "cutoff": base_cut})

            for profile in args.profiles:
                try:
                    decoded = musepack_roundtrip(src_wav, work, profile, mpcenc, mpcdec)
                    mdct_stat, run, cut = statistics(decoded)
                except Exception as exc:
                    print(f"      {profile}: failed ({exc})", flush=True)
                    continue
                rows.append({"source": source.name, "arm": "musepack", "profile": profile,
                             "mdct": mdct_stat, "stereo_run": run, "cutoff": cut})

        print(f"  [{index}/{len(sources)}] {source.name}  "
              f"baseline mdct={base_mdct:.2f} run={base_run:.1f} cut={base_cut:.0f}",
              flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["source", "arm", "profile", "mdct", "stereo_run", "cutoff"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} rows -> {args.out}", flush=True)

    report(rows, args.profiles)
    return 0


def report(rows: List[dict], profiles: List[str]) -> None:
    """What each family reads, against the paired genuine baseline."""
    print("\n" + "=" * 70)
    print("MUSEPACK — what each family reads")
    print("=" * 70)

    genuine = [r for r in rows if r["arm"] == "genuine"]
    if not genuine:
        print("no genuine baseline measured — nothing can be said.")
        return

    g_mdct = np.array([r["mdct"] for r in genuine], dtype=float)
    g_run = np.array([r["stereo_run"] for r in genuine], dtype=float)
    g_cut = np.array([r["cutoff"] for r in genuine], dtype=float)

    print(f"\ngenuine baseline (n={len(genuine)}): "
          f"mdct median {np.nanmedian(g_mdct):.2f} · "
          f"stereo run median {np.nanmedian(g_run):.1f} · "
          f"cutoff median {np.nanmedian(g_cut):.0f} Hz")

    print(f"\n{'profile':12}{'n':>4}{'mdct AUC':>11}{'stereo AUC':>12}"
          f"{'cutoff AUC':>12}{'cutoff med':>12}")
    for profile in profiles:
        arm = [r for r in rows if r["profile"] == profile]
        if not arm:
            continue
        a_mdct = np.array([r["mdct"] for r in arm], dtype=float)
        a_run = np.array([r["stereo_run"] for r in arm], dtype=float)
        a_cut = np.array([r["cutoff"] for r in arm], dtype=float)
        # Cutoff runs the other way: a transcode's cutoff is LOWER than genuine, so
        # the discriminating direction is the negated statistic.
        print(f"{profile:12}{len(arm):>4}{auc(a_mdct, g_mdct):>11.2f}"
              f"{auc(a_run, g_run):>12.2f}{auc(-a_cut, -g_cut):>12.2f}"
              f"{np.nanmedian(a_cut):>12.0f}")

    print("\nRegistered predictions (see module docstring):")
    print("  P1 mdct   AUC < 0.65 everywhere   — Musepack has no MDCT to align")
    print("  P2 stereo AUC > 0.75 on standard  — Musepack does use mid/side")
    print("  P3 cutoff separates on radio, not on insane")
    print("\nBeing wrong on P1 is the useful outcome: it would mean Rule 13 responds")
    print("to something its docstring does not name.")
    print("\nP3 FAILED and its first explanation was wrong too. --insane does NOT cap")
    print("the bandwidth (the cap is the full band); 18,750 Hz is a 48 kHz constant,")
    print("and at 44.1 kHz it is not a band boundary at all. The separation is the")
    print("encoder zeroing low-level HF, not a lowpass. See the module docstring.")
    print("\nAny arm median here still mixes in detect_cutoff's Nyquist-on-failure")
    print("return. Use detect_cutoff_detailed for a sentinel that says so.")


if __name__ == "__main__":
    raise SystemExit(main())
