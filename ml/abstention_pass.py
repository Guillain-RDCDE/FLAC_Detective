#!/usr/bin/env python3
"""Measure how often the accusing instruments cannot run at all.

Criteria and populations registered first in
``ml/exchange/ABSTENTION_REGISTRATION_2026-09-01.md``.

The question is narrow on purpose. The engine returns ``AUTHENTIC`` both when the
instruments ran and found nothing and when they could not run — two different
statements in one word. This measures how many real files are in the second case,
and checks that deliberately unreadable inputs are.

No classifier is involved: assessability is decided by the spectrum and the
header, so this pass is cheap. Q4 is built here, before the trigger conditions
are frozen, and is the only population expected to abstain.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

CORPUS = Path(r"C:\Users\loutr\audit_corpus")
SET_A = Path(
    r"C:\Users\loutr\Dropbox\Perso\GitHub\Flac_Detective\Temp\fd-exchange-v3-setA-r2\audio"
)

# Below this the file has no content above 16 kHz at all, which is the band every
# accusing rule reads. Declared, not swept: it is the edge of the instruments'
# domain, not a tuning parameter. See the 1 September amendment.
MIN_ASSESSABLE_RATE = 32000
MIN_ASSESSABLE_SAMPLES = 17408
SILENCE_FLOOR_RMS = 1e-6

# Q4. ``mono`` is kept and expected NOT to abstain: it loses the stereo and
# temporal witnesses but the spectral family, the CNN and the MDCT statistic all
# run, so it is assessable with fewer witnesses. Including it as unreadable was
# this document's own error, caught by building the population.
UNREADABLE = (
    ("mono", ("-ac", "1")),  # assessable — the control that must NOT abstain
    ("short", ("-t", "0.2")),  # under the 17408 samples the frame witness needs
    ("rate8k", ("-ar", "8000")),  # no band for the rules to read
    ("silent", ("-af", "volume=0")),  # nothing to measure anywhere
)


def build_unreadable(source: Path, out_dir: Path) -> List[Tuple[Path, str]]:
    """Build Q4 from one authentic source; returns (path, why) pairs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    built: List[Tuple[Path, str]] = []
    for name, extra in UNREADABLE:
        dst = out_dir / f"unreadable_{name}.flac"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-map_metadata",
                "-1",
                *extra,
                "-c:a",
                "flac",
                "-sample_fmt",
                "s16",
                str(dst),
            ],
            check=True,
            capture_output=True,
        )
        built.append((dst, name))
    return built


def assessability(path: Path) -> Dict[str, object]:
    """What the engine could and could not read on this file."""
    import math

    import numpy as np
    import soundfile as sf

    from flac_detective.analysis.spectrum import analyze_spectrum

    info = sf.info(str(path))
    cutoff, _energy, _std, _floor = analyze_spectrum(path)
    cutoff_known = cutoff is not None and not math.isnan(float(cutoff)) and float(cutoff) > 0
    data, _rate = sf.read(str(path), dtype="float32", frames=int((info.samplerate or 0) * 30) or -1)
    rms = float(np.sqrt(np.mean(np.asarray(data, dtype=np.float64) ** 2))) if data.size else 0.0
    return {
        "cutoff_known": bool(cutoff_known),
        "stereo": info.channels >= 2,
        "long_enough": info.frames >= MIN_ASSESSABLE_SAMPLES,
        "rate_known": bool(info.samplerate),
        "rate_in_domain": bool(info.samplerate and info.samplerate >= MIN_ASSESSABLE_RATE),
        "has_signal": rms > SILENCE_FLOOR_RMS,
    }


def unassessable_reason(signals: Dict[str, object]) -> Optional[str]:
    """The declared trigger conditions, in the order they are reported.

    Spectral first: every other accusing rule leans on the cutoff, so its absence
    is the strongest form of "nothing could run".
    """
    if not signals["rate_known"]:
        return "sample rate unreadable"
    if not signals["rate_in_domain"]:
        return f"sampled below {MIN_ASSESSABLE_RATE} Hz — no band the rules can read"
    if not signals["has_signal"]:
        return "no measurable signal"
    if not signals["cutoff_known"]:
        return "spectrum unanalysable — no cutoff to read"
    if not signals["long_enough"]:
        return "too short for the frame-based witness"
    return None


def populations() -> List[Tuple[Path, str]]:
    """Q1 to Q3: every real file the abstention is priced against."""
    out: List[Tuple[Path, str]] = []
    for path in sorted((CORPUS / "authentic").glob("*.flac")):
        out.append((path, "Q1 authentic"))
    for arm_dir in sorted((CORPUS / "fake").iterdir()):
        if arm_dir.is_dir():
            for path in sorted(arm_dir.glob("*.flac")):
                out.append((path, "Q2 arms"))
    for path in sorted(SET_A.glob("*.flac")):
        out.append((path, "Q3 set A"))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """Run the pass and report B2 and B3. Returns a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="cap per population (0 = all)")
    args = ap.parse_args(argv)

    items = populations()
    if args.limit:
        capped: List[Tuple[Path, str]] = []
        seen: Dict[str, int] = {}
        for path, pop in items:
            if seen.get(pop, 0) >= args.limit:
                continue
            seen[pop] = seen.get(pop, 0) + 1
            capped.append((path, pop))
        items = capped

    with tempfile.TemporaryDirectory() as tmp:
        source = sorted((CORPUS / "authentic").glob("*.flac"))[0]
        items += [(p, "Q4 unreadable") for p, _ in build_unreadable(source, Path(tmp))]

        totals: Dict[str, int] = {}
        abstain: Dict[str, int] = {}
        reasons: Dict[str, int] = {}
        for index, (path, pop) in enumerate(items, 1):
            totals[pop] = totals.get(pop, 0) + 1
            try:
                signals = assessability(path)
            except Exception as exc:
                print(f"  ECHEC {path.name}: {exc}", flush=True)
                continue
            reason = unassessable_reason(signals)
            if reason:
                abstain[pop] = abstain.get(pop, 0) + 1
                reasons[reason] = reasons.get(reason, 0) + 1
                print(f"  ABSTIENT {pop} {path.name}: {reason}", flush=True)
            if index % 100 == 0:
                print(f"  {index}/{len(items)}", flush=True)

    print()
    real = 0
    real_abstain = 0
    for pop in sorted(totals):
        n, a = totals[pop], abstain.get(pop, 0)
        print(f"{pop:>16s}  {a:4d} / {n:4d} abstiennent")
        if not pop.startswith("Q4"):
            real += n
            real_abstain += a
    print(f"\nB2  materiel reel : {real_abstain}/{real} = {100.0*real_abstain/max(real, 1):.2f} %")
    print(
        f"B3  Q4 : {abstain.get('Q4 unreadable', 0)}/{totals.get('Q4 unreadable', 0)} (attendu 3/4, mono NON)"
    )
    print(f"raisons : {reasons or 'aucune'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
