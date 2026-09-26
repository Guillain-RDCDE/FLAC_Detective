"""Rule 12 window-count probe: does the CNN swing less with more windows?

For every file, the shipped inference (``infer_file_probability``) at 3 windows
(the shipped count), 5 and 7, and Rule 12's score mapping applied to each
(0 under p = 0.5, linear to +30 at 0.95, abstain under the rolloff gate; the
WARNING floor is left out because it depends on the other rules). Offline.

Usage::

    python ml/cnn_windows_probe.py out.csv label=folder [label=folder ...]
"""

from __future__ import annotations

import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

COUNTS = (3, 5, 7)


def score(p: float) -> int:
    """Rule 12's mapping from calibrated probability to points (no floor)."""
    if p < 0.5:
        return 0
    if p >= 0.95:
        return 30
    return int(round((p - 0.5) / 0.45 * 30))


def probe(job):
    path, label = job
    from flac_detective.analysis.new_scoring.rules.ml_classifier import infer_file_probability

    row = {"file": path.name, "path": str(path), "label": label}
    for n in COUNTS:
        res = infer_file_probability(path, n_windows=n)
        if res is None:
            row[f"p{n}"], row[f"s{n}"] = "", ""
            continue
        row[f"p{n}"] = round(res["p_cal"], 4)
        row[f"s{n}"] = 0 if res["abstained"] else score(res["p_cal"])
    return row


def main() -> int:
    out = Path(sys.argv[1])
    jobs = []
    for spec in sys.argv[2:]:
        label, folder = spec.split("=", 1)
        jobs += [(p, label) for p in sorted(Path(folder).rglob("*.flac"))]
    keys = ["file", "path", "label"] + [f"{k}{n}" for n in COUNTS for k in ("p", "s")]
    with ProcessPoolExecutor(3) as ex, out.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        for i, row in enumerate(ex.map(probe, jobs, chunksize=2), 1):
            wr.writerow(row)
            if i % 100 == 0:
                print(i, "/", len(jobs), flush=True)
    print(len(jobs), "rows ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
