"""Corpus probe (ml/mp3_grid_corpus_probe.py): Layer III hole-fraction peak ratio, 3 depths.

Usage: python ml/mp3_grid_corpus_probe.py out.csv label=folder|list.txt [...]
"""
import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mp3_hybrid_filterbank as H  # noqa: E402

DEPTHS = (20.0, 30.0, 40.0)


def one(job):
    path, label = job
    try:
        d, r = sf.read(str(path), dtype="float64", always_2d=True)
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "label": label, "error": str(e)}
    x = d.mean(axis=1)
    t = len(x) / r
    mid = max(0, int((t / 2 - 15) * r))
    x = x[mid : mid + 30 * r]
    curves = H.alignment_curves(x, 48, DEPTHS)
    row = {"file": path.name, "label": label, "rate": r}
    for i, dep in enumerate(DEPTHS):
        c = curves[i]
        good = c[~np.isnan(c)]
        if good.size < 10 or np.median(good) <= 0:
            row[f"pr{int(dep)}"], row[f"off{int(dep)}"] = "", ""
            continue
        row[f"pr{int(dep)}"] = round(float(np.nanmax(c) / np.median(good)), 4)
        row[f"off{int(dep)}"] = int(np.nanargmax(c))
    return row


def main():
    out = Path(sys.argv[1])
    jobs = []
    for spec in sys.argv[2:]:
        label, folder = spec.split("=", 1)
        src = Path(folder)
        if src.suffix == ".txt":
            files = [Path(x) for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            files = [p for p in sorted(src.rglob("*")) if p.suffix.lower() in (".flac", ".wav", ".aif", ".aiff")]
        jobs += [(p, label) for p in files]
    keys = ["file", "label", "rate"] + [f"{k}{int(d)}" for d in DEPTHS for k in ("pr", "off")] + ["error"]
    with ProcessPoolExecutor(3) as ex, out.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        for i, row in enumerate(ex.map(one, jobs, chunksize=2), 1):
            wr.writerow(row)
            f.flush()
            if i % 50 == 0:
                print(i, "/", len(jobs), flush=True)
    print(len(jobs), "->", out)


if __name__ == "__main__":
    main()
