#!/usr/bin/env python3
"""Is there alignment structure in MP3 at MP3's own geometry? A feasibility probe.

Why this exists
---------------
Rule 13 finds MDCT quantisation holes at AAC/Vorbis geometry — a 2048-sample
window, 1024-sample hop — and reads MP3 at the null. The documented justification
for not pursuing MP3 was "the cutoff rules already convict there".

The paired-discrimination measurement (ml/paired_discrimination.py) showed that
justification is false at high bitrate. On `mp3_V0`, 29 of 80 transcodes score
*identically* to the genuine file they came from, and on `mp3_320`, 22 of 80. Not
mis-ranked — tied, almost always at zero and zero. The engine has nothing to say
about either file. So the cutoff rules do not convict there, and the reason Rule 13
does not either may simply be that it is looking on the wrong grid.

Unlike Opus, there is no physical barrier. Opus is out of reach because CELT
transforms at 48 kHz whatever you feed it, so a 44.1 kHz source is resampled in and
back out and the sample-exact alignment is destroyed. **MP3 does not resample.** The
alignment survives; it just lives at a different period. MPEG-1 Layer III quantises
in a hybrid domain — a 32-band polyphase filterbank followed by an 18-point MDCT —
with a granule of 576 samples and a frame of 1152, not 2048.

What this probe answers, and what it deliberately cannot
-------------------------------------------------------
Implementing the full hybrid analysis filterbank is a substantial piece of work, and
it should not be started on a hunch. This asks the cheaper question first: scanning
with a *plain* MDCT at MP3's period, is there any alignment preference at all on MP3
transcodes?

A positive answer justifies building the real filterbank. A negative answer is
genuinely ambiguous — it could mean "no structure" or "right period, wrong basis",
because the polyphase bank means MP3's coefficients are not a plain MDCT of the
waveform. So the probe carries a **synthetic positive control**: audio with holes
imposed on a known grid. If the control fires at its own period and not at others,
the machinery demonstrably detects grid structure when structure is there, and a
null on real MP3 is at least a null about *this* basis rather than about the probe.

Usage::

    python ml/mp3_geometry_probe.py --control          # de-risk the probe itself
    python ml/mp3_geometry_probe.py --corpus C:/Users/loutr/audit_corpus --limit 40
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import soundfile as sf
from scipy.ndimage import median_filter

# Geometries under test. (name, window_len, hop, window_kind).
#
# MP3's granule is 576 samples and its frame is 1152. MPEG-1 Layer III's MDCT stage
# uses a SINE window (standard block type 0), so that is the right analysis window
# for those two rows.
#
# The aac_2048 row is the real-data control, and it must use KBD. The first version
# of this probe used a sine window everywhere and duly read ffmpeg AAC at AUC 0.52
# where the shipped rule reads 0.99 — which is the exact trap Jamie Dodd cost me a
# day on in the first place: with a sine analysis window, ffmpeg AAC reads at the
# floor. The synthetic control did not catch it, because holes imposed with a sine
# window are of course found with a sine window. A probe needs a control on REAL
# material of known answer, not only on material it made itself.
GEOMETRIES: Tuple[Tuple[str, int, int, str], ...] = (
    ("mp3_frame_1152", 1152, 576, "sine"),
    ("mp3_granule_576", 576, 288, "sine"),
    ("aac_2048", 2048, 1024, "kbd"),
)

# The control's acceptance bar: if ffmpeg AAC does not separate at its own geometry,
# nothing this probe says about MP3 is interpretable.
CONTROL_ARM = "aac_ff256"
CONTROL_GEOMETRY = "aac_2048"
CONTROL_MIN_AUC = 0.90

BAND_HZ: Tuple[float, float] = (2000.0, 16000.0)
HOLE_DEPTH_DB = 40.0
MIN_BASELINE_HOLE_FRACTION = 0.001
EXCERPT_SEC = 30.0


def sine_window(length: int) -> np.ndarray:
    """Sine window — MPEG Layer III's block type 0, and Princen-Bradley compliant."""
    n = np.arange(length)
    return np.sin(np.pi / length * (n + 0.5)).astype(np.float32)


def kbd_window(length: int, alpha: float = 4.0) -> np.ndarray:
    """Kaiser-Bessel-derived — ffmpeg's AAC long-block window."""
    half = length // 2
    kaiser = np.kaiser(half + 1, np.pi * alpha)
    cumulative = np.cumsum(kaiser)
    rising = np.sqrt(cumulative[:half] / cumulative[-1])
    return np.concatenate([rising, rising[::-1]]).astype(np.float32)


def make_window(kind: str, length: int) -> np.ndarray:
    """Window by name, so each geometry is analysed with the window it was made with."""
    return kbd_window(length) if kind == "kbd" else sine_window(length)


def mdct_matrix(window_len: int, sample_rate: int, band: Tuple[float, float]) -> np.ndarray:
    """MDCT basis for one geometry, restricted to the analysis band."""
    half = window_len // 2
    lo = max(1, int(band[0] / (sample_rate / 2) * half))
    hi = min(half, int(band[1] / (sample_rate / 2) * half))
    n = np.arange(window_len)[:, None]
    k = np.arange(lo, hi)[None, :]
    return np.cos(np.pi / half * (n + 0.5 + half / 2) * (k + 0.5)).astype(np.float32)


def full_mdct_matrix(window_len: int) -> np.ndarray:
    """Unrestricted MDCT basis — needed to synthesise the control, not to measure."""
    half = window_len // 2
    n = np.arange(window_len)[:, None]
    k = np.arange(half)[None, :]
    return np.cos(np.pi / half * (n + 0.5 + half / 2) * (k + 0.5)).astype(np.float32)


def alignment_curve(
    x: np.ndarray,
    sample_rate: int,
    window_len: int,
    hop: int,
    window_kind: str = "sine",
    offsets: Optional[Sequence[int]] = None,
    n_frames: int = 24,
    ref_size: int = 33,
) -> np.ndarray:
    """Hole fraction per frame alignment, at an arbitrary geometry.

    A parameterised twin of ``new_scoring.mdct.alignment_curve``, which hardcodes
    the shipped 2048/1024 geometry in module constants. Deliberately a copy rather
    than a refactor of the shipped path: this is exploratory, and the statistic that
    convicts people should not be destabilised by a probe.
    """
    basis = mdct_matrix(window_len, sample_rate, BAND_HZ)
    window = make_window(window_kind, window_len)
    offs = np.asarray(list(range(hop) if offsets is None else offsets), dtype=np.int64)
    usable = len(x) - window_len - int(offs.max())
    if usable <= 0:
        return np.full(offs.size, np.nan)

    stride = max(hop, (usable // max(1, n_frames)) // hop * hop)
    tap = np.arange(window_len)
    thr = 10 ** (-HOLE_DEPTH_DB / 20.0)
    hole_count = np.zeros(offs.size)
    used = np.zeros(offs.size)

    for frame in range(n_frames):
        starts = offs + frame * stride
        if int(starts.max()) + window_len > len(x):
            break
        blocks = x[starts[:, None] + tap[None, :]] * window[None, :]
        spec = np.abs(blocks @ basis)
        ref = median_filter(spec, size=(1, ref_size), mode="nearest")
        energetic = ref.mean(axis=1) > 1e-7
        hole_count += np.where(energetic, (spec < ref * thr).mean(axis=1), 0.0)
        used += energetic

    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(used > 0, hole_count / used, np.nan)


def peak_ratio(
    x: np.ndarray,
    sample_rate: int,
    window_len: int,
    hop: int,
    window_kind: str = "sine",
    n_frames: int = 24,
) -> Tuple[float, int]:
    """Hole density at the best alignment over the median across alignments."""
    curve = alignment_curve(x, sample_rate, window_len, hop, window_kind, n_frames=n_frames)
    finite = curve[np.isfinite(curve)]
    if finite.size < 8:
        return float("nan"), -1
    baseline = float(np.median(finite))
    if baseline < MIN_BASELINE_HOLE_FRACTION:
        # A ratio of two near-zero numbers lands anywhere; abstain as the shipped
        # rule does rather than report noise.
        return float("nan"), -1
    best = int(np.nanargmax(curve))
    return float(curve[best] / baseline), best


# ============================ the positive control ============================


def impose_holes(
    x: np.ndarray,
    window_len: int,
    hop: int,
    fraction: float = 0.35,
    window_kind: str = "sine",
) -> np.ndarray:
    """Zero the quietest coefficients on a KNOWN grid, then resynthesise.

    This is what a quantiser does, reduced to its essential: coefficients set to
    exactly zero while their neighbours survive, on a fixed frame grid. If the probe
    cannot find *this*, it cannot find anything, and any null it reports on real MP3
    would say more about the probe than about MP3.
    """
    half = window_len // 2
    basis = full_mdct_matrix(window_len)
    # Princen-Bradley holds for the sine window; KBD(alpha=4) also satisfies it, so
    # overlap-add reconstructs in both cases and the control isolates the zeroing.
    window = make_window(window_kind, window_len)
    out = np.zeros(len(x), dtype=np.float64)

    for start in range(0, len(x) - window_len, hop):
        block = x[start : start + window_len] * window
        coeffs = block @ basis
        if fraction > 0:
            cut = np.quantile(np.abs(coeffs), fraction)
            coeffs = np.where(np.abs(coeffs) <= cut, 0.0, coeffs)
        # IMDCT + overlap-add; the sine window satisfies Princen-Bradley, so with
        # fraction=0 this reconstructs the input and the control is exercising only
        # the zeroing.
        out[start : start + window_len] += (coeffs @ basis.T) * window * (2.0 / half)
    return out.astype(np.float32)


def run_control(sample_rate: int = 44100, seconds: float = 20.0) -> int:
    """Prove the probe detects grid structure, and only at the right grid."""
    rng = np.random.default_rng(20260818)
    n = int(sample_rate * seconds)
    t = np.arange(n) / sample_rate
    # Pink-ish noise plus tones: broadband enough to fill the analysis band, so the
    # baseline hole fraction is meaningful rather than a near-zero denominator.
    noise = np.cumsum(rng.normal(0, 1, n))
    noise = (noise - noise.mean()) / (np.abs(noise).max() + 1e-9)
    tonal = sum(0.1 * np.sin(2 * np.pi * f * t) for f in (440, 1310, 3300, 7900))
    clean = (0.6 * noise + 0.4 * tonal).astype(np.float32)

    print("SYNTHETIC POSITIVE CONTROL")
    print("  holes imposed on a known grid; the probe should fire at THAT grid only\n")
    print(f"  {'imposed grid':>16} | " + " | ".join(f"{g[0]:>16}" for g in GEOMETRIES))

    ok = True
    for name, win, hop, kind in GEOMETRIES:
        holed = impose_holes(clean, win, hop, window_kind=kind)
        readings: List[float] = []
        for _gname, gwin, ghop, gkind in GEOMETRIES:
            ratio, _ = peak_ratio(holed, sample_rate, gwin, ghop, gkind)
            readings.append(ratio)
        print(f"  {name:>16} | " + " | ".join(f"{r:>16.2f}" for r in readings))
        matched = readings[[g[0] for g in GEOMETRIES].index(name)]
        others = [r for i, r in enumerate(readings) if GEOMETRIES[i][0] != name]
        if not (np.isfinite(matched) and matched > 2.0 and matched > max(others) * 1.3):
            ok = False

    baseline, _ = peak_ratio(clean, sample_rate, *GEOMETRIES[0][1:4])
    print(f"\n  un-holed control at {GEOMETRIES[0][0]}: {baseline:.2f}  (should sit near 1)")
    print("\n  VERDICT:", "probe detects grid structure, geometry-specific ✓" if ok
          else "PROBE FAILS ITS OWN CONTROL — a null on real MP3 would be meaningless ✗")
    return 0 if ok else 1


# ============================== the real measurement ==========================


def read_excerpt(path: Path) -> Tuple[np.ndarray, int]:
    """Mono excerpt, float32."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(EXCERPT_SEC * info.samplerate))
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    return np.ascontiguousarray(mono, dtype=np.float32), int(rate)


def run_corpus(corpus: Path, out: Path, limit: int, arms: List[str], n_frames: int) -> int:
    """Measure every geometry on the arms that matter."""
    groups: Dict[str, List[Path]] = {
        "genuine": sorted((corpus / "authentic").glob("*.flac"))[:limit]
    }
    for arm in arms:
        directory = corpus / "fake" / arm
        if directory.is_dir():
            groups[arm] = sorted(directory.glob("*.flac"))[:limit]

    rows: List[dict] = []
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["arm", "file", "geometry", "ratio", "offset"])
        writer.writeheader()
        for arm, paths in groups.items():
            for index, path in enumerate(paths, 1):
                try:
                    audio, rate = read_excerpt(path)
                except Exception as exc:
                    print(f"  skip {path.name}: {exc}", flush=True)
                    continue
                for gname, win, hop, kind in GEOMETRIES:
                    ratio, offset = peak_ratio(audio, rate, win, hop, kind, n_frames)
                    row = {"arm": arm, "file": path.name, "geometry": gname,
                           "ratio": f"{ratio:.4f}", "offset": offset}
                    writer.writerow(row)
                    rows.append({**row, "ratio": ratio})
                fh.flush()
                if index % 5 == 0:
                    print(f"  {arm} [{index}/{len(paths)}]", flush=True)
    report(rows)
    return 0


def auc(fake: np.ndarray, genuine: np.ndarray) -> float:
    """Mann-Whitney AUC with tied ranks averaged."""
    fake, genuine = fake[np.isfinite(fake)], genuine[np.isfinite(genuine)]
    if not fake.size or not genuine.size:
        return float("nan")
    values = np.concatenate([fake, genuine])
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(1, values.size + 1)
    for value in np.unique(values):
        tied = values == value
        if tied.sum() > 1:
            ranks[tied] = ranks[tied].mean()
    return float(
        (ranks[: fake.size].sum() - fake.size * (fake.size + 1) / 2) / (fake.size * genuine.size)
    )


def report(rows: List[dict]) -> None:
    """Per-geometry separation, arm by arm."""
    geometries = [g[0] for g in GEOMETRIES]
    arms = sorted({r["arm"] for r in rows} - {"genuine"})

    def values(arm: str, geometry: str) -> np.ndarray:
        return np.array(
            [r["ratio"] for r in rows if r["arm"] == arm and r["geometry"] == geometry],
            dtype=np.float64,
        )

    print("\n" + "=" * 74)
    print("MP3 GEOMETRY PROBE — median peak ratio (AUC vs genuine, same geometry)")
    print("=" * 74)
    header = f"{'arm':14}" + "".join(f"{g:>20}" for g in geometries)
    print(header)
    for arm in ["genuine"] + arms:
        cells = []
        for geometry in geometries:
            v = values(arm, geometry)
            v = v[np.isfinite(v)]
            if not v.size:
                cells.append(f"{'—':>20}")
                continue
            if arm == "genuine":
                cells.append(f"{np.median(v):>20.3f}")
            else:
                a = auc(v, values("genuine", geometry))
                cells.append(f"{np.median(v):>13.3f} ({a:.2f})")
        print(f"{arm:14}" + "".join(cells))
    print(
        "\nRead: an MP3 arm separating at mp3_frame_1152 or mp3_granule_576 but not at\n"
        "aac_2048 is the result that justifies building the real hybrid filterbank.\n"
        "Everything at the null across all three geometries means the plain-MDCT basis\n"
        "cannot see it, and the polyphase bank would have to be implemented to know\n"
        "whether that is MP3's fault or the basis's."
    )

    # ===== REAL-DATA CONTROL =====
    #
    # The synthetic control proves the machinery finds holes on a grid. It cannot
    # prove the WINDOW is right, because holes imposed with a given window are of
    # course found with that window. The first version of this probe passed its
    # synthetic control and still read ffmpeg AAC at AUC 0.52, because it analysed
    # with a sine window where ffmpeg uses KBD — the statistic reads at the floor.
    # So the interpretable-or-not decision is made here, on material of known answer.
    control = values(CONTROL_ARM, CONTROL_GEOMETRY)
    if control.size:
        control_auc = auc(control, values("genuine", CONTROL_GEOMETRY))
        verdict = "OK" if control_auc >= CONTROL_MIN_AUC else "FAILED"
        print(
            f"\nreal-data control — {CONTROL_ARM} at {CONTROL_GEOMETRY}: "
            f"AUC {control_auc:.2f} (documented 0.99, bar {CONTROL_MIN_AUC}) -> {verdict}"
        )
        if control_auc < CONTROL_MIN_AUC:
            print(
                "  The probe cannot reproduce a result this project already knows, so "
                "nothing above is interpretable. Check the window per geometry before "
                "reading a single MP3 number."
            )
    else:
        print(f"\nreal-data control absent: include {CONTROL_ARM} in --arms.")


# ============================ the bitrate gradient ============================


def run_gradient(corpus: Path, limit: int, n_frames: int) -> int:
    """Does the basis see MP3 zeros when there are MANY of them?

    The corpus probe read mp3_320 and mp3_V0 at the null and mp3_192 slightly above
    it, and that gradient was the whole remaining question. If pushing the bitrate
    down keeps raising the reading, the basis CAN see MP3 quantisation and the
    high-bitrate null is a quantity problem — a filterbank would not rescue it. If
    even brutal quantisation stays at the null, the basis is blind to MP3's hybrid
    domain and only the real filterbank could get in.

    Encodes each source across the full bitrate range with libmp3lame, so the answer
    comes from one material set rather than from comparing separate corpus arms.
    """
    import subprocess
    import tempfile

    rates = ["64k", "96k", "128k", "192k", "320k"]
    sources = sorted((corpus / "authentic").glob("*.flac"))[:limit]
    window_len, hop, kind = 1152, 576, "sine"

    genuine: List[float] = []
    by_rate: Dict[str, List[float]] = {r: [] for r in rates}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for index, src in enumerate(sources, 1):
            audio, rate_hz = read_excerpt(src)
            ratio, _ = peak_ratio(audio, rate_hz, window_len, hop, kind, n_frames)
            genuine.append(ratio)
            wav = tmp / "src.wav"
            sf.write(str(wav), audio, rate_hz, subtype="PCM_16")
            for bitrate in rates:
                encoded, decoded = tmp / f"a_{bitrate}.mp3", tmp / f"b_{bitrate}.wav"
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                     "-c:a", "libmp3lame", "-b:a", bitrate, str(encoded)], check=True)
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(encoded),
                     "-c:a", "pcm_s16le", str(decoded)], check=True)
                back, back_rate = sf.read(str(decoded), dtype="float32")
                mono = back if back.ndim == 1 else np.mean(back, axis=1)
                value, _ = peak_ratio(
                    np.ascontiguousarray(mono, dtype=np.float32),
                    back_rate, window_len, hop, kind, n_frames)
                by_rate[bitrate].append(value)
            print(f"  [{index}/{len(sources)}]", flush=True)

    reference = np.array(genuine)
    print(
        f"\ngenuine at mp3_frame_1152: median {np.nanmedian(reference):.3f} "
        f"(n={reference.size})\n"
    )
    print(f"{'bitrate':>8} {'median':>9} {'AUC':>7}")
    for bitrate in rates:
        values = np.array(by_rate[bitrate])
        print(f"{bitrate:>8} {np.nanmedian(values):>9.3f} {auc(values, reference):>7.2f}")
    print(
        "\nA flat, null column across every bitrate means the plain-MDCT basis "
        "cannot see MP3 quantisation at all — not that there is too little of it."
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Run the control, the corpus measurement, or both."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", action="store_true", help="run the synthetic control only")
    parser.add_argument("--gradient", action="store_true", help="bitrate-gradient test")
    parser.add_argument("--corpus", type=Path, default=Path(r"C:/Users/loutr/audit_corpus"))
    parser.add_argument("--out", type=Path, default=Path("ml/mp3_geometry_probe.csv"))
    parser.add_argument("--limit", type=int, default=40)
    # 12 is plenty for a comparative probe: every arm pays the same sampling
    # noise, and the shipped rule triages on 3 frames before refining.
    parser.add_argument("--frames", type=int, default=12)
    parser.add_argument(
        "--arms", nargs="+", default=["mp3_320", "mp3_V0", "mp3_192", "aac_ff256"]
    )
    args = parser.parse_args(argv)

    if args.control:
        return run_control()
    if args.gradient:
        return run_gradient(args.corpus, args.limit, args.frames)
    status = run_control()
    if status != 0:
        print("\nAborting: the probe failed its own control, so corpus numbers would "
              "not be interpretable.")
        return status
    return run_corpus(args.corpus, args.out, args.limit, args.arms, args.frames)


if __name__ == "__main__":
    raise SystemExit(main())
