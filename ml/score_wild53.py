#!/usr/bin/env python3
"""Score the Nu Breed 53 against the W-series, registered before the bytes landed.

Protocol, exactly as pre-registered (``ml/exchange/PREREGISTERED_2026-08-20.md``,
AMENDMENT 3, committed 2026-08-21 BEFORE download):

1. Hash-verify every file against Provir's regenerated ledger (sha256 per row)
   — refuse to score anything on a corpus that does not verify 53/53.
2. Run the shipped engine (v1.11.4; the working tree is engine-identical to the
   tag — the diff since is docstrings, comments and one unused constant) with
   ``deep=True``, the CNN available.
3. Measure the MP3_IDEM instrument (``ml/mp3_idem_probe.py``) on every file.
4. Score W1–W5 with Wilson bounds, CD3 reported separately everywhere (W5).

This is NOT a blind test and is not scored as one: his labels and his engine's
verdicts were known before our engine ran. What the discipline buys is that the
W-series numbers were committed before the first byte arrived.

Output ``ml/wild53_scores.csv`` is committable: the track titles are a public
commercial release and already sit in the archived ledger.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mp3_idem_probe import mp3_idem, require_ffmpeg  # noqa: E402

ROOT = Path(r"C:\Users\loutr\wild53\21-08-26")
LEDGER = ROOT / "wild53_feature_ledger.csv"
ALBUM = ROOT / "Original Hardcore The Nu Breed (2004)"
DISC_DIRS = {
    "CD1 Darren Styles": "CD1 Darren Styles",
    "CD2 Dougal": "CD2 Dougal",
    "CD3 Dougal and Styles": "CD3 Bonus (Mixed by Styles and Dougal)",
}
IDEM_BAR = 1.68  # our genuine p5, from ml/mp3_idem_probe.py's corpus run

MP3_IDEM_SEC = 60.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wilson(k: int, n: int) -> Tuple[float, float]:
    """95 % Wilson interval, the exchange's convention for every clean line."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = 1.96
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def pct(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f} % (Wilson [{100 * lo:.1f}, {100 * hi:.1f}] %)"


def verify(rows: List[dict]) -> None:
    """53/53 or refuse."""
    bad = 0
    for r in rows:
        path = ALBUM / DISC_DIRS[r["disc"]] / r["track"]
        if not path.exists() or sha256(path) != r["sha256"].strip():
            print(f"  HASH FAIL {r['track']}")
            bad += 1
    if bad:
        raise SystemExit(f"{bad} files fail verification — nothing is scored.")
    print("hash verification: 53/53 OK", flush=True)


def collect(rows: List[dict], out_path: Path) -> List[dict]:
    from flac_detective import __version__
    from flac_detective.analysis.analyzer import FLACAnalyzer

    ffmpeg = require_ffmpeg()
    done: Dict[str, dict] = {}
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done[row["track"]] = row
        print(f"reprise: {len(done)} deja scores", flush=True)

    analyzer = FLACAnalyzer(deep=True)
    fieldnames = [
        "disc",
        "track",
        "basis",
        "sha12",
        "engine_version",
        "verdict",
        "score",
        "families",
        "idem_R",
    ]
    out: List[dict] = list(done.values())
    with open(out_path, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for index, r in enumerate(rows, 1):
            if r["track"] in done:
                continue
            path = ALBUM / DISC_DIRS[r["disc"]] / r["track"]
            try:
                result = analyzer.analyze_file(str(path))
                verdict = result["verdict"]
                score = result["score"]
                families = "+".join(sorted(result.get("evidence_families") or []))
            except Exception as exc:
                print(f"  [{index}/53] {r['track']}: engine failed ({exc})", flush=True)
                verdict, score, families = "ERROR", "", ""
            try:
                info = sf.info(str(path))
                data, rate = sf.read(
                    str(path), dtype="float32", frames=int(MP3_IDEM_SEC * info.samplerate)
                )
                idem_r, _, _ = mp3_idem(data, int(rate), ffmpeg)
            except Exception as exc:
                print(f"  [{index}/53] {r['track']}: idem failed ({exc})", flush=True)
                idem_r = float("nan")
            row = {
                "disc": r["disc"],
                "track": r["track"],
                "basis": r["basis"],
                "sha12": r["sha256"][:12],
                "engine_version": __version__,
                "verdict": verdict,
                "score": score,
                "families": families,
                "idem_R": f"{idem_r:.3f}" if np.isfinite(idem_r) else "nan",
            }
            writer.writerow(row)
            fh.flush()
            out.append(row)
            print(f"  [{index}/53] {r['track']}  {verdict}  R={row['idem_R']}", flush=True)
    return out


def report(scored: List[dict]) -> None:
    owner = [r for r in scored if r["basis"] == "owner-knowledge"]
    eye = [r for r in scored if r["basis"] == "eye"]

    def signaled(rows: List[dict]) -> int:
        return sum(1 for r in rows if r["verdict"] not in ("AUTHENTIC", "ERROR"))

    def convicted(rows: List[dict]) -> int:
        return sum(1 for r in rows if r["verdict"] == "FAKE_CERTAIN")

    print("\n" + "=" * 74)
    print("W-SERIES — registered 2026-08-21 before download, scored on bytes")
    print("=" * 74)

    k1 = convicted(scored)
    print(
        f"\nW1  zero FAKE_CERTAIN across all 53:      "
        f"{'HELD' if k1 == 0 else 'FAILED -> AUDIT'}   ({pct(k1, len(scored))})"
    )

    s_owner, s_eye = signaled(owner), signaled(eye)
    w2 = (s_owner / max(len(owner), 1)) > (s_eye / max(len(eye), 1))
    print(f"W2  owner-knowledge signals above eye:    {'HELD' if w2 else 'FAILED'}")
    print(f"      owner-knowledge  {pct(s_owner, len(owner))}")
    print(f"      eye              {pct(s_eye, len(eye))}")

    w3 = s_owner >= 0.40 * len(owner)
    print(
        f"W3  >= 40 % of CD1+CD2 signaled:          {'HELD' if w3 else 'FAILED'}"
        f"   ({pct(s_owner, len(owner))})"
    )

    idem_owner = [float(r["idem_R"]) for r in owner if r["idem_R"] != "nan"]
    k4 = sum(1 for v in idem_owner if v <= IDEM_BAR)
    w4 = k4 >= 0.50 * len(owner)
    print(
        f"W4  MP3_IDEM R<={IDEM_BAR} on >= 50 % of CD1+CD2: {'HELD' if w4 else 'FAILED'}"
        f"   ({pct(k4, len(owner))}, median R "
        f"{np.median(idem_owner):.2f})"
        if idem_owner
        else "W4  no idem readings"
    )
    idem_eye = [float(r["idem_R"]) for r in eye if r["idem_R"] != "nan"]
    if idem_eye:
        k4e = sum(1 for v in idem_eye if v <= IDEM_BAR)
        print(
            f"      (eye tier, reported separately:     {pct(k4e, len(eye))}, "
            f"median R {np.median(idem_eye):.2f})"
        )

    print("W5  CD3 separated everywhere above:       HELD by construction of this report")

    print("\nVerdict mix (owner-knowledge | eye):")
    for verdict in ("AUTHENTIC", "WARNING", "SUSPICIOUS", "FAKE_CERTAIN", "ERROR"):
        a = sum(1 for r in owner if r["verdict"] == verdict)
        b = sum(1 for r in eye if r["verdict"] == verdict)
        if a or b:
            print(f"  {verdict:14} {a:3} | {b}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("ml/wild53_scores.csv"))
    args = parser.parse_args(argv)

    rows = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))
    if len(rows) != 53:
        raise SystemExit(f"expected 53 ledger rows, found {len(rows)}")
    verify(rows)
    scored = collect(rows, args.out)
    report(scored)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
