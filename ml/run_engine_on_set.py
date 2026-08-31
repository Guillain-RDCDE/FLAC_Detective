#!/usr/bin/env python3
"""Run the engine over a frozen exchange set and write one verdict file.

Written for set A and deliberately generic, because the same script has to run
on Provir's set B the moment his manifest arrives — and writing it then, against
his files, is exactly how an analysis drifts toward the answer.

Two things it does that a bare loop would not:

**It verifies the manifest at READ time.** Not at copy time. The v2 transport
lesson is binding: Dropbox's files-on-demand dehydrated 590 files to
reparse-point placeholders after upload, and two of them read back wrong bytes
at the same size. So every file is hashed against ``MANIFEST.sha256`` before it
is analysed, and a mismatch aborts the pass rather than scoring a placeholder.

**It stamps the engine into the output.** Version and commit SHA on every row,
because the v3 protocol's commitment covers both: "we fixed that between the run
and the key" has to be a checkable claim rather than a conversation.

Usage::

    python ml/run_engine_on_set.py --set C:/…/fd-exchange-v3-setA --out ml/verdicts_setA.csv
    python ml/score_v3_return.py --verdicts ml/verdicts_setA.csv --key …-LABELS.json --half A
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

FIELDS = [
    "file",
    "verdict",
    "score",
    "confidence",
    "hires_verdict",
    "evidence_families",
    "engine_version",
    "engine_sha",
]


def engine_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def verify_manifest(set_dir: Path) -> List[Path]:
    """Every file checked against the manifest AT READ TIME. Aborts on any mismatch."""
    manifest = set_dir / "MANIFEST.sha256"
    if not manifest.exists():
        raise SystemExit(
            f"no MANIFEST.sha256 under {set_dir} — refusing to score an unverified set"
        )
    files: List[Path] = []
    bad: List[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        digest, rel = parts[0], parts[1]
        size = int(parts[2]) if len(parts) > 2 else None
        path = set_dir / rel
        if not path.exists():
            bad.append(f"{rel}: absent")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            bad.append(f"{rel}: digest")
        elif size is not None and len(data) != size:
            bad.append(f"{rel}: size")
        else:
            files.append(path)
    if bad:
        raise SystemExit(f"{len(bad)} files do not match the manifest: {bad[:5]} — nothing scored")
    print(f"manifeste verifie a la lecture: {len(files)} fichiers, 0 divergent", flush=True)
    return files


def run(set_dir: Path, out_path: Path, deep: bool) -> int:
    from flac_detective.__version__ import __version__
    from flac_detective.analysis.analyzer import FLACAnalyzer

    files = verify_manifest(set_dir)
    sha = engine_sha()
    print(f"moteur {__version__} @ {sha[:12]}", flush=True)

    done = set()
    if out_path.exists():
        with open(out_path, newline="", encoding="utf-8") as fh:
            done = {r["file"] for r in csv.DictReader(fh)}
        print(f"reprise: {len(done)} deja scores", flush=True)

    analyzer = FLACAnalyzer(deep=deep)
    new = not out_path.exists()
    with open(out_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        for index, path in enumerate(files, 1):
            if path.name in done:
                continue
            try:
                result = analyzer.analyze_file(str(path))
            except Exception as exc:
                print(f"  ECHEC {path.name}: {exc}", flush=True)
                continue
            writer.writerow(
                {
                    "file": path.name,
                    "verdict": result.get("verdict", ""),
                    "score": result.get("score", ""),
                    "confidence": result.get("confidence", ""),
                    "hires_verdict": result.get("hires_verdict", ""),
                    "evidence_families": "+".join(result.get("evidence_families") or []),
                    "engine_version": __version__,
                    "engine_sha": sha,
                }
            )
            fh.flush()
            if index % 25 == 0:
                print(f"  {index}/{len(files)}", flush=True)
    print(f"ecrit {out_path}", flush=True)
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"SHA-256 du fichier de verdicts (a publier avant que les clefs bougent): {digest}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set", dest="set_dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--no-deep", action="store_true", help="skip the CNN fast-path bypass")
    args = ap.parse_args(argv)
    return run(args.set_dir, args.out, deep=not args.no_deep)


if __name__ == "__main__":
    sys.exit(main())
