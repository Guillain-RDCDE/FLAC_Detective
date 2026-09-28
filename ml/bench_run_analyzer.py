"""Bench runner (ml/bench_run_analyzer.py): FLACAnalyzer.analyze_file on folders or file lists.

The runner behind MP3_GRID_REGISTRATION_2026-09-27.md: the engine the CLI wraps,
fed from list files so a sample of a large library needs no copy.

Usage: python bench_run.py <src dir> <out.jsonl> label=folder|list.txt [...]
Resumable: files already in out.jsonl are skipped. torch live, default mode, 30 s.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

SRC = sys.argv[1]
_AN = None


def init():
    global _AN
    sys.path.insert(0, SRC)
    import logging

    logging.disable(logging.CRITICAL)
    from flac_detective.analysis.analyzer import FLACAnalyzer

    _AN = FLACAnalyzer(sample_duration=30.0, deep=False)


def one(job):
    path, label = job
    try:
        r = _AN.analyze_file(str(path))
        return {"path": str(path), "label": label, "verdict": r["verdict"], "score": r["score"],
                "cutoff": r["cutoff_freq"], "families": sorted(r.get("evidence_families") or []),
                "breakdown": r.get("score_breakdown", {}), "reason": r.get("reason", "")}
    except Exception as e:  # noqa: BLE001
        return {"path": str(path), "label": label, "verdict": "ERROR", "error": str(e)}


def main():
    out = Path(sys.argv[2])
    done = set()
    if out.exists():
        done = {json.loads(line)["path"] for line in out.read_text(encoding="utf-8").splitlines() if line}
    jobs = []
    for spec in sys.argv[3:]:
        label, src = spec.split("=", 1)
        p = Path(src)
        if p.suffix == ".txt":
            files = [Path(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            files = [f for f in sorted(p.rglob("*")) if f.suffix.lower() in (".flac", ".wav", ".aif", ".aiff")]
        jobs += [(f, label) for f in files if str(f) not in done]
    print(len(jobs), "to run", flush=True)
    with ProcessPoolExecutor(2, initializer=init) as ex, out.open("a", encoding="utf-8") as fh:
        for i, row in enumerate(ex.map(one, jobs, chunksize=1), 1):
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            if i % 100 == 0:
                print(i, "/", len(jobs), flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
