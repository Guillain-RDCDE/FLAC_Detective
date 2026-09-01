#!/usr/bin/env python3
"""G1-bis: the repaired gates priced on the certified LIBRARY — the 24-bit control.

Why this exists, declared before it runs
-----------------------------------------
G1 priced the repairs on the 16-bit audit+wild genuine corpora. Gate C bypasses
the container-bitrate check for any container at PCM level — which includes
**24-bit FLAC** (a lossless 24-bit file easily exceeds 0.90 x rate x 32/1000).
The audit corpora contain no 24-bit material; the certified library does. So
the repairs get a second safety population: the 797 library files of the Rule
13 recertification draw (path_hash join proven 877/877 by
ml/recert_admission_pass.py).

    G1-bis  At most 6 library files newly receive +50 under the new gates
            (the G1 rate, scaled: 2/258 ~ 6/797), and every such file must
            already carry residual_floor_db <= -55 dB by construction of the
            320 branch. Registered BEFORE the measurement pass runs. If it
            fails, the campaign stops again and reports — same rule as G1.

Results are appended below after the run.
--------------------------------------------------------------------------------
(not yet run)
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from r1_gates_repricing import new_r1_plus50, old_r1_plus50  # noqa: E402
from recert_admission_pass import build_hash_map  # noqa: E402

from flac_detective.analysis.spectrum import analyze_spectrum  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("ml/r1_gates_library.csv"))
    args = parser.parse_args(argv)

    recert = list(csv.DictReader(open("ml/recert_880.csv", newline="", encoding="utf-8")))
    mapping = build_hash_map()
    library = [
        mapping[r["path_hash"]]
        for r in recert
        if r["source"] == "library" and r["path_hash"] in mapping
    ]
    print(f"{len(library)} library files", flush=True)

    done = {}
    if args.out.exists():
        with open(args.out, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done[row["track"]] = row
        print(f"reprise: {len(done)}", flush=True)

    fieldnames = [
        "track",
        "sample_rate",
        "cutoff",
        "energy_ratio",
        "cutoff_std",
        "residual_floor_db",
        "container_kbps",
    ]
    rows: List[dict] = list(done.values())
    with open(args.out, "a" if done else "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not done:
            writer.writeheader()
        for index, raw in enumerate(library, 1):
            path = Path(raw)
            key = path.name
            if key in done:
                continue
            try:
                info = sf.info(str(path))
                seconds = info.frames / info.samplerate
                kbps = path.stat().st_size * 8.0 / seconds / 1000.0
                cutoff, energy, std, resid = analyze_spectrum(path)
            except Exception:
                continue
            row = {
                "track": key,
                "sample_rate": int(info.samplerate),
                "cutoff": f"{cutoff:.1f}",
                "energy_ratio": f"{energy:.3e}",
                "cutoff_std": f"{std:.1f}",
                "residual_floor_db": f"{resid:.1f}" if np.isfinite(resid) else "nan",
                "container_kbps": f"{kbps:.0f}",
            }
            writer.writerow(row)
            fh.flush()
            rows.append(row)
            if index % 50 == 0:
                print(f"  {index}/{len(library)}", flush=True)

    for r in rows:
        r.setdefault("population", "library")
    old = sum(1 for r in rows if old_r1_plus50(r))
    new = sum(1 for r in rows if new_r1_plus50(r))
    newly = [r["track"][:60] for r in rows if new_r1_plus50(r) and not old_r1_plus50(r)]
    print(f"\nlibrary n={len(rows)}  old +50: {old}  new +50: {new}")
    print(f"G1-bis  newly +50 (<=6): {'HELD' if len(newly) <= 6 else 'FAILED'} " f"({len(newly)})")
    for track in newly[:10]:
        print(f"   {track}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
