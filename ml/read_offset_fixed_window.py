#!/usr/bin/env python3
"""Is the read-position defect DETERMINISTIC, or is it noise?

Why this is not ``read_position_halves.py``
-------------------------------------------
The halves probe cut each track in two and found 4 of 12 verdicts disagreeing
with themselves. That established *that* position matters. It cannot establish
*how*, because it changes two things at once: the half-length window moves AND
its length changes with the track. Length is a confound there, and the engine's
spectral path anchors its samples at fixed fractions of the file, so a shorter
file is also a differently-sampled file.

This probe holds the window length FIXED and moves only the start offset. That is
the one manipulation that isolates position, and it is the protocol this project
asked Provir to run before it had run it itself.

The two questions, kept apart on purpose
----------------------------------------
A verdict has an ADDRESS (``cutoff_freq`` — *which* frequency the engine says the
cliff sits at) and a MAGNITUDE (``score`` — *how convinced* it is). Reporting one
number that mixes them is what made the halves result hard to read. If the
address is pinned while the magnitude wanders, the engine is looking at a stable
physical feature and grading it inconsistently. If the address wanders too, the
engine is not finding the same feature at all. Those are different diseases with
different cures, so they are measured and reported separately.

Criteria, written before the measurement (project rule)
-------------------------------------------------------
1. **The control that decides whether this matters at all**: does ANY lawful file
   convict at ANY offset? If yes, moving the window manufactures false positives
   and this is a precision defect — the only kind that must stop everything. If
   no, the defect costs recall and never precision, which is the sole direction
   in which losing is acceptable.
2. **Address stable** := ``cutoff_freq`` spread over all offsets of one file
   <= ``--address-tol`` Hz (default 100 Hz, comfortably above the analysis bin
   width and below any real codec-wall difference).
3. **Magnitude stable** := every offset of one file yields the same verdict.
4. A file is **deterministic in the frame-alignment sense** if, in ``--fine``
   mode, its scores repeat with the period of the format frame rather than
   wandering — reported as the per-file score pattern, not asserted here.

Self-checks that run before any of the above
--------------------------------------------
* **Slice exactness, on every window.** The PCM written for each window is read
  back and compared sample for sample with the PCM of the source over the same
  span. If they ever differ, the slicing step is itself an intervention and every
  number below is confounded. This is checked on all N windows rather than on a
  sample of them, because it costs almost nothing and a probe that verifies its
  own instrument on one file out of twenty is a probe that has verified nothing.
* **Determinism of the instrument.** The first offset of each file is scored
  twice. Two different answers to the same question would make every other row
  meaningless — and the previous read-stability work in this repository has been
  bitten by exactly that.

Slicing is done with ``soundfile`` at exact sample offsets, deliberately NOT with
ffmpeg: the subject of the experiment is frame alignment, and a seek that lands
on the nearest container frame would quietly destroy the thing being measured.

Usage::

    python ml/read_offset_fixed_window.py \
        --positives C:/Users/loutr/fd-transcodes-complets \
        --lawful    C:/Users/loutr/fd-pistes-completes \
        --out ml/read_offset_fixed_window.csv

    python ml/read_offset_fixed_window.py ... --fine --out ml/read_offset_fine.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Kept identical to ml/score_v3_return.py by tests/test_offset_probe.py. Two
# copies of a verdict ladder that can drift apart is how a "conviction" quietly
# becomes a different thing in two reports of the same experiment.
CONVICTION = "FAKE_CERTAIN"
SIGNALED = ("FAKE_CERTAIN", "SUSPICIOUS", "WARNING")

WINDOW_S = 60.0
COARSE_OFFSETS_S: Tuple[float, ...] = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0)

# One MPEG-1 Layer III granule pair is 1152 samples. The fine sweep walks a
# single frame in eighths, which is the resolution at which an alignment effect
# has to show up if it is an alignment effect at all.
MP3_FRAME_SAMPLES = 1152
FINE_OFFSETS_SAMPLES: Tuple[int, ...] = tuple(
    range(0, MP3_FRAME_SAMPLES + 1, MP3_FRAME_SAMPLES // 8)
)

ADDRESS_TOL_HZ = 100.0


def slice_to_flac(src: Path, start_sample: int, length_samples: int, out: Path) -> None:
    """Write ``length_samples`` frames of ``src`` starting at ``start_sample``.

    Sample-exact and lossless: the PCM written is bit-identical to the PCM read.
    No resampling, no container seek, no re-encode of anything lossy.

    ``int32`` throughout rather than float: libsndfile's float scaling is not
    symmetric between read and write, so a float round-trip can shift a sample by
    one LSB. One LSB is nothing to a listener and everything to a probe whose
    whole subject is whether a bit-level alignment moved.
    """
    import soundfile as sf

    with sf.SoundFile(str(src)) as fh:
        fh.seek(start_sample)
        data = fh.read(length_samples, dtype="int32")
        rate, subtype = fh.samplerate, fh.subtype
    sf.write(str(out), data, rate, subtype=subtype, format="FLAC")


def slice_is_exact(src: Path, start_sample: int, length_samples: int, written: Path) -> bool:
    """Is ``written`` sample-for-sample the span of ``src`` it claims to be?

    The measurement this probe makes is only about the offset if the act of
    extracting the window changes nothing else. That is a claim, so it is
    checked rather than stated.
    """
    import numpy as np
    import soundfile as sf

    reference, _ = sf.read(str(src), start=start_sample, frames=length_samples, dtype="int32")
    produced, _ = sf.read(str(written), dtype="int32")
    return bool(np.array_equal(reference, produced))


def duration_samples(path: Path) -> Tuple[int, int]:
    """(frames, samplerate) of ``path``."""
    import soundfile as sf

    info = sf.info(str(path))
    return int(info.frames), int(info.samplerate)


def score(analyzer, path: Path) -> Dict:
    """Score one file, returning the three fields this probe reports on."""
    try:
        result = analyzer.analyze_file(str(path))
        return {
            "verdict": result.get("verdict", "?"),
            "score": result.get("score", ""),
            "cutoff_hz": result.get("cutoff_freq", ""),
            "families": "|".join(result.get("evidence_families", []) or []),
        }
    except Exception as exc:  # noqa: BLE001 - a failure is a result here
        return {
            "verdict": f"ECHEC:{type(exc).__name__}",
            "score": "",
            "cutoff_hz": "",
            "families": "",
        }


def collect(folder: Path, population: str, needed: int) -> List[Tuple[Path, str]]:
    """Files long enough to carry every offset plus a full window."""
    out: List[Tuple[Path, str]] = []
    short = 0
    for path in sorted(folder.rglob("*.flac")):
        try:
            frames, _ = duration_samples(path)
        except Exception:
            continue
        if frames < needed:
            short += 1
            continue
        out.append((path, population))
    if short:
        print(f"  ({short} fichiers ecartes, trop courts pour la grille)", flush=True)
    return out


def parse_shard(spec: str) -> Tuple[int, int]:
    """``"2/3"`` -> ``(2, 3)``. Anything that is not a usable shard is refused.

    A silently-misparsed shard is the worst outcome available here: the sweep
    still runs, still writes a CSV, and covers the wrong subset of files without
    anything looking wrong.
    """
    index_str, separator, count_str = spec.partition("/")
    if not separator:
        raise ValueError(f"--shard {spec!r} invalide : attendu i/n")
    try:
        index, count = int(index_str), int(count_str)
    except ValueError as exc:
        raise ValueError(f"--shard {spec!r} invalide : i et n doivent etre entiers") from exc
    if count < 1 or not 1 <= index <= count:
        raise ValueError(f"--shard {spec!r} invalide : attendu 1 <= i <= n")
    return index, count


def shard_files(files: List[Tuple[Path, str]], index: int, count: int) -> List[Tuple[Path, str]]:
    """The ``index``-th of ``count`` disjoint shards of ``files``.

    A stride rather than contiguous blocks: the file list is positives followed
    by lawful material, so a block split would hand one process nothing but
    transcodes. A shard that then died would take an entire population with it
    and leave a result that looked complete.
    """
    return files[index - 1 :: count]


def spread(values: Sequence) -> float:
    """max - min over the numeric values present, or -1.0 if none are.

    -1.0 rather than 0.0 for "nothing measurable": a spread of zero is the
    strongest possible result here, and a failed read must never be able to
    impersonate it.
    """
    nums: List[float] = []
    for value in values:
        if isinstance(value, bool) or value is None or value == "":
            continue
        try:
            nums.append(float(value))
        except (TypeError, ValueError):
            continue
    return (max(nums) - min(nums)) if nums else -1.0


def main() -> int:
    """Run the self-checks, then the offset sweep, then report the two axes."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--positives", type=Path, required=True, help="folder of known transcodes")
    ap.add_argument("--lawful", type=Path, required=True, help="folder of known-genuine tracks")
    ap.add_argument("--window", type=float, default=WINDOW_S)
    ap.add_argument(
        "--fine", action="store_true", help="sweep one MP3 frame in eighths instead of seconds"
    )
    ap.add_argument("--address-tol", type=float, default=ADDRESS_TOL_HZ)
    ap.add_argument("--limit", type=int, default=0, help="0 = every file")
    ap.add_argument(
        "--shard",
        default="1/1",
        help="i/n - take every n-th file starting at i. Splits a long sweep across "
        "several processes; the shards are disjoint and their CSVs concatenate.",
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    logging.disable(logging.CRITICAL)
    from flac_detective.analysis.analyzer import FLACAnalyzer

    analyzer = FLACAnalyzer(sample_duration=args.window, deep=True)

    probe_rate = 44100
    window_samples = int(round(args.window * probe_rate))
    if args.fine:
        offsets = list(FINE_OFFSETS_SAMPLES)
        offset_label = "samples"
    else:
        offsets = [int(round(s * probe_rate)) for s in COARSE_OFFSETS_S]
        offset_label = "samples (grille en secondes)"
    needed = max(offsets) + window_samples

    files = collect(args.positives, "positive", needed) + collect(args.lawful, "lawful", needed)
    if args.limit:
        files = files[: args.limit]
    try:
        shard_i, shard_n = parse_shard(args.shard)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if shard_n > 1:
        files = shard_files(files, shard_i, shard_n)
    if not files:
        raise SystemExit("aucun fichier assez long pour la grille demandee")

    n_pos = sum(1 for _, p in files if p == "positive")
    print(
        f"{len(files)} fichiers ({n_pos} positifs, {len(files) - n_pos} licites), "
        f"fenetre {args.window:g} s figee, {len(offsets)} offsets en {offset_label}",
        flush=True,
    )

    rows: List[Dict] = []
    exact_ok = exact_tested = 0
    determinism_ok = determinism_tested = 0

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for index, (path, population) in enumerate(files, 1):
            _, rate = duration_samples(path)
            if rate != probe_rate:
                # The offset grid is expressed in samples at 44.1 kHz. A file at
                # another rate would silently be swept over a different span of
                # time, so it is skipped and said out loud rather than folded in.
                print(
                    f"  IGNORE {path.name}: {rate} Hz, la grille est a {probe_rate} Hz", flush=True
                )
                continue

            per_file: List[Dict] = []
            for offset in offsets:
                cut = work / f"{path.stem}__off{offset}.flac"
                slice_to_flac(path, offset, window_samples, cut)

                # Self-check 1 - the window is the span it says it is.
                exact = slice_is_exact(path, offset, window_samples, cut)
                exact_tested += 1
                exact_ok += exact
                if not exact:
                    print(f"  DECOUPAGE INEXACT {path.name} offset {offset}", flush=True)

                measured = score(analyzer, cut)

                # Self-check 2 - determinism, on the first offset of each file.
                if offset == offsets[0]:
                    again = score(analyzer, cut)
                    determinism_tested += 1
                    determinism_ok += again == measured
                    if again != measured:
                        print(
                            f"  NON DETERMINISTE {path.name}: {measured} puis {again}", flush=True
                        )

                cut.unlink(missing_ok=True)
                row = {
                    "file": path.name,
                    "population": population,
                    "offset_samples": offset,
                    "offset_s": round(offset / probe_rate, 4),
                    "window_s": args.window,
                    **measured,
                    "slice_exact": "yes" if exact else "no",
                }
                rows.append(row)
                per_file.append(row)

            verdicts = {r["verdict"] for r in per_file}
            addr = spread([r["cutoff_hz"] for r in per_file])
            mag = spread([r["score"] for r in per_file])
            flag = "" if len(verdicts) == 1 else "  <-- VERDICT MOBILE"
            print(
                f"  {index}/{len(files)} {path.name[:52]:52s} {population:8s} "
                f"adresse {addr:8.1f} Hz  magnitude {mag:5.1f}  {sorted(verdicts)}{flag}",
                flush=True,
            )

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report(rows, args)
    print(
        f"\nAUTOCONTROLES  decoupage bit-exact {exact_ok}/{exact_tested}  "
        f"determinisme {determinism_ok}/{determinism_tested}",
        flush=True,
    )
    if exact_ok != exact_tested or determinism_ok != determinism_tested:
        print(
            "  AUTOCONTROLE EN ECHEC : les lignes ci-dessus ne mesurent pas ce qu'elles disent.",
            flush=True,
        )
    print(f"ecrit {args.out}", flush=True)
    return 0


def report(rows: List[Dict], args) -> None:
    """The two axes, and the control that decides whether any of it matters."""
    by_file: Dict[str, List[Dict]] = {}
    for row in rows:
        by_file.setdefault(row["file"], []).append(row)

    lawful_convictions = [
        r for r in rows if r["population"] == "lawful" and r["verdict"] == CONVICTION
    ]
    lawful_signals = [r for r in rows if r["population"] == "lawful" and r["verdict"] in SIGNALED]
    lawful_windows = sum(1 for r in rows if r["population"] == "lawful")
    positive_windows = sum(1 for r in rows if r["population"] == "positive")
    positive_convictions = sum(
        1 for r in rows if r["population"] == "positive" and r["verdict"] == CONVICTION
    )

    print("\n" + "=" * 78)
    print("LE CONTROLE QUI DECIDE - deplacer la fenetre fabrique-t-il un faux positif ?")
    print("=" * 78)
    print(
        f"  fenetres licites condamnees (FAKE_CERTAIN) : {len(lawful_convictions)}/{lawful_windows}"
    )
    print(f"  fenetres licites signalees  (tous etages)  : {len(lawful_signals)}/{lawful_windows}")
    for row in lawful_convictions:
        print(f"    ! {row['file']} a l'offset {row['offset_s']} s")
    if lawful_windows == 0:
        # A control with an empty denominator is the failure mode this project
        # has catalogued five times: a guard that never refused anything reads
        # exactly like a guard that never had anything to refuse.
        print("  -> CONTROLE NON EXECUTE : aucune fenetre licite dans ce run.")
        print("     Ne rien conclure sur la precision. Relancer avec --lawful peuple.")
    elif not lawful_convictions:
        print("  -> le defaut coute du RAPPEL, jamais de la PRECISION.")
    else:
        print("  -> defaut de PRECISION : tout s'arrete ici (critere ecrit d'avance).")

    print("\nADRESSE contre MAGNITUDE, par fichier")
    print(f"  {'fichier':54s} {'pop':8s} {'adresse Hz':>11s} {'magnitude':>10s}  verdicts")
    moved_addr = moved_mag = 0
    for name, group in by_file.items():
        addr, mag = spread([r["cutoff_hz"] for r in group]), spread([r["score"] for r in group])
        verdicts = sorted({r["verdict"] for r in group})
        moved_addr += addr > args.address_tol
        moved_mag += len(verdicts) > 1
        print(f"  {name[:54]:54s} {group[0]['population']:8s} {addr:11.1f} {mag:10.1f}  {verdicts}")

    print(
        f"\n  adresse mobile (> {args.address_tol:g} Hz) : {moved_addr}/{len(by_file)} fichiers"
        f"\n  verdict mobile                  : {moved_mag}/{len(by_file)} fichiers"
    )
    if moved_mag and not moved_addr:
        print("  -> l'adresse ne bouge pas, la magnitude si : le moteur trouve la meme")
        print("     arete et la note differemment. C'est un probleme de SEUIL, pas de lecture.")
    elif moved_addr:
        print("  -> l'adresse bouge : le moteur ne trouve pas la meme arete selon l'offset.")
    else:
        print("  -> rien ne bouge sur cette grille.")

    print(
        f"\n  rappel sur les positifs : {positive_convictions}/{positive_windows} fenetres condamnees"
    )
    at_zero = [r for r in rows if r["population"] == "positive" and r["offset_samples"] == 0]
    zero_convictions = sum(1 for r in at_zero if r["verdict"] == CONVICTION)
    print(f"  dont a l'offset zero    : {zero_convictions}/{len(at_zero)}")


if __name__ == "__main__":
    raise SystemExit(main())
