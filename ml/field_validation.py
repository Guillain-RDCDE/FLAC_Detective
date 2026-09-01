"""Field validation of FLAC Detective on the real D:\\FLAC library (one-off).

Validates the v0.16 multi-format work against real data, not synthetic fixtures:

  1. Routing on REAL .m4a/.ape: ALAC/APE -> analysable, AAC -> reject (no extension
     trust). Uses the package's own probe_codec / is_analysable_lossless.
  2. Real ALAC + APE files actually analysed end-to-end -> verdict distribution.
  3. False-positive rate: a random sample of certified-authentic FLACs -> how many
     come out non-AUTHENTIC (lower is better).
  4. MP3->ALAC fakes built from real FLACs -> must be flagged (no hole opened).

Run from the repo root with the project venv (point FLAC_LIBRARY at your music):
    FLAC_LIBRARY=D:/FLAC python ml/field_validation.py
    python ml/field_validation.py /path/to/library
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from flac_detective.analysis.analyzer import FLACAnalyzer
from flac_detective.analysis.audio_formats import is_analysable_lossless, probe_codec

# Library to validate against: CLI arg > FLAC_LIBRARY env > a sensible default.
LIBRARY = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FLAC_LIBRARY", "D:/FLAC"))
M4A_APE_LIST = Path(tempfile.gettempdir()) / "m4a_ape_list.txt"
SAMPLE_DURATION = 20.0  # seconds analysed per file (speed/quality trade-off)
FLAC_SAMPLE_N = 120
FAKE_N = 3
SEED = 1234


def _hr(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}", flush=True)


def load_m4a_ape() -> list[Path]:
    if M4A_APE_LIST.exists():
        paths = [
            Path(p) for p in M4A_APE_LIST.read_text(encoding="utf-8").splitlines() if p.strip()
        ]
        # The list was written with MSYS /d/... paths; map back to D:\.
        fixed = []
        for p in paths:
            s = str(p)
            if s.startswith("/d/"):
                s = "D:/" + s[3:]
            fixed.append(Path(s))
        return [p for p in fixed if p.exists()]
    return sorted(LIBRARY.rglob("*.m4a")) + sorted(LIBRARY.rglob("*.ape"))


def part1_routing(files: list[Path]) -> dict[str, list[Path]]:
    """Probe every real .m4a/.ape and check routing matches the codec."""
    _hr("PART 1 — Routing on real .m4a/.ape (probe the real codec, never the ext)")
    by_codec: dict[str, list[Path]] = {}
    mismatches = []
    for f in files:
        codec = probe_codec(f) or "UNREADABLE"
        by_codec.setdefault(codec, []).append(f)
        analysable = is_analysable_lossless(f)
        # Expectation: lossless codecs analysable, lossy (aac) not.
        lossless_codec = codec in {"alac", "ape"}
        if analysable != lossless_codec:
            mismatches.append((f, codec, analysable))

    for codec, fs in sorted(by_codec.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(fs):3d}  codec={codec:12s} -> analysable={is_analysable_lossless(fs[0])}")
    if mismatches:
        print(f"\n  [WARN] {len(mismatches)} ROUTING MISMATCHES:")
        for f, codec, a in mismatches[:20]:
            print(f"     codec={codec} analysable={a}  {f.name}")
    else:
        print("\n  [OK] No routing mismatch - every AAC rejected, every ALAC/APE analysable.")
    return by_codec


def _analyze(files: list[Path], label: str) -> list[tuple[Path, dict]]:
    analyzer = FLACAnalyzer(sample_duration=SAMPLE_DURATION)
    results = []
    for i, f in enumerate(files, 1):
        try:
            r = analyzer.analyze_file(f)
        except Exception as e:  # noqa: BLE001 - validation must never abort mid-run
            r = {"verdict": "CRASH", "score": -1, "reason": repr(e)}
        results.append((f, r))
        print(
            f"  [{i:3d}/{len(files)}] {r.get('verdict','?'):13s} "
            f"score={r.get('score','?'):>4} {f.name[:60]}",
            flush=True,
        )
    dist = Counter(r["verdict"] for _, r in results)
    print(f"\n  {label} verdict distribution: {dict(dist)}")
    return results


def part2_real_lossless(by_codec: dict[str, list[Path]]) -> None:
    _hr("PART 2 — Real ALAC + APE analysed end-to-end")
    lossless = by_codec.get("alac", []) + by_codec.get("ape", [])
    if not lossless:
        print("  (no ALAC/APE found)")
        return
    results = _analyze(lossless, "ALAC+APE")
    flagged = [(f, r) for f, r in results if r["verdict"] in {"SUSPICIOUS", "FAKE_CERTAIN"}]
    if flagged:
        print(
            f"\n  {len(flagged)} flagged (inspect — real lossless rips, likely vintage/band-limited):"
        )
        for f, r in flagged:
            print(f"     {r['verdict']} score={r['score']}  {f.name}")
            print(f"        reason: {r.get('reason','')[:160]}")


def part3_flac_fp(n: int) -> None:
    _hr(f"PART 3 — False-positive rate on {n} random certified FLACs")
    print("  Enumerating FLACs (sampling, not full scan)...", flush=True)
    rng = random.Random(SEED)
    # Reservoir sample to avoid materialising all 72k paths.
    reservoir: list[Path] = []
    for i, p in enumerate(LIBRARY.rglob("*.flac")):
        if len(reservoir) < n:
            reservoir.append(p)
        else:
            j = rng.randint(0, i)
            if j < n:
                reservoir[j] = p
    print(f"  Sampled {len(reservoir)} FLACs. Analysing...", flush=True)
    results = _analyze(reservoir, "FLAC")
    non_auth = [(f, r) for f, r in results if r["verdict"] not in {"AUTHENTIC", "ERROR", "CRASH"}]
    errors = [(f, r) for f, r in results if r["verdict"] in {"ERROR", "CRASH"}]
    total_ok = len(results) - len(errors)
    fp_rate = 100.0 * len(non_auth) / total_ok if total_ok else 0.0
    print(f"\n  Non-AUTHENTIC: {len(non_auth)}/{total_ok}  (apparent FP rate {fp_rate:.1f}%)")
    print(f"  Errors/crashes: {len(errors)}")
    for f, r in non_auth[:30]:
        print(f"     {r['verdict']} score={r['score']}  {f.name[:70]}")


def part4_fakes(n: int) -> None:
    _hr(f"PART 4 — {n} MP3->ALAC fakes from real FLACs (must be flagged)")
    rng = random.Random(SEED + 1)
    candidates: list[Path] = []
    for i, p in enumerate(LIBRARY.rglob("*.flac")):
        if len(candidates) < n:
            candidates.append(p)
        else:
            j = rng.randint(0, i)
            if j < n:
                candidates[j] = p
        if i > 5000:  # don't traverse the whole tree just to pick a few
            break
    tmpdir = Path(tempfile.mkdtemp(prefix="fake_alac_"))
    fakes = []
    for src in candidates:
        mp3 = tmpdir / (src.stem + ".mp3")
        fake = tmpdir / (src.stem + ".fake.m4a")
        # FLAC -> MP3 128k (introduces the cliff) -> ALAC (lossless wrap of the fake).
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-b:a", "128k", str(mp3)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(mp3),
                "-vn",
                "-c:a",
                "alac",
                str(fake),
            ],
            check=True,
            capture_output=True,
        )
        fakes.append(fake)
        print(f"  built fake: {fake.name}", flush=True)
    results = _analyze(fakes, "FAKE(MP3->ALAC)")
    caught = [r for _, r in results if r["verdict"] in {"SUSPICIOUS", "FAKE_CERTAIN", "WARNING"}]
    print(f"\n  Caught (WARNING+): {len(caught)}/{len(results)}  — expected all flagged.")


def main() -> int:
    print(f"Library: {LIBRARY}  |  sample_duration={SAMPLE_DURATION}s  |  seed={SEED}")
    files = load_m4a_ape()
    print(f"Real .m4a/.ape files found: {len(files)}")
    by_codec = part1_routing(files)
    part2_real_lossless(by_codec)
    part3_flac_fp(FLAC_SAMPLE_N)
    part4_fakes(FAKE_N)
    _hr("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
