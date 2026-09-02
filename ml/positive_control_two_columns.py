"""Positive control for the two-engine column pair reported on an exchange set.

The v1.13.4 and v1.13.6 columns on Provir's set B came out identical on all 280
rows. A null like that is a real result — the band-limited independence guard
changed nothing on a corpus neither party built — but it is also exactly what a
broken harness produces when both passes silently load the same engine. The
version string does not settle it: ``__version__`` comes from whichever module
actually loaded, and this project's virtual environment carries an editable
install pointing at the repository, so a mis-set ``PYTHONPATH`` yields two
passes over the same code that still print two different numbers.

So the null is only reportable next to a control that must NOT be null. This
script runs the four band-limited files that the registered v1.13.5 measurement
(``independence_guard_{s0,s1,s2}.csv`` against their ``_after_`` counterparts)
says have to move from FAKE_CERTAIN to SUSPICIOUS. Point it at each tree in
turn: if today's chain still separates them, the null on the exchange set is a
measurement. If it does not, the null is an artefact and nothing else in the
pass can be believed either.

The four names are hard-coded on purpose. They were read off the registered
before/after pair, and letting this script re-derive them would let a later
change to that pair quietly redefine its own control.

Note on reading those CSVs: ``file`` is NOT unique in them — a filename recurs
in every arm — so the join key is ``(file, population)``. Joining on the name
alone compares one arm against another and reports sixty-odd changes where
there are four.

Usage::

    python ml/positive_control_two_columns.py <tree_root> <out.json>

with ``<tree_root>`` the repository or the v1.13.4 worktree. Run it with no
``PYTHONPATH`` set: the script puts the tree's own ``src`` first.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

# Parked sources, band-limited on the fly with the declared filter.
PARKED = (
    Path(r"C:\Users\loutr\fd-v3-setA\corpus\_unused"),
    Path(r"C:\Users\loutr\fd-v3-setA\corpus\_dup_series"),
)

# The four rows that moved when the v1.13.5 guard landed. Read off the
# registered before/after pair, keyed on (file, population).
MUST_MOVE = {
    "rh1982-10-18.late.178810.sbd.ellingsen.lennox.miksis.flac24__s2t05 - West L.A. Fadeaway.flac",
    "src056.flac",
    "src059.flac",
    "src060.flac",
}


def main(tree: Path, out_path: Path) -> int:
    """Band-limit the four control files and score them with one tree's engine."""
    sys.path.insert(0, str(tree / "src"))
    sys.path.insert(0, str(tree / "ml"))

    import flac_detective
    from flac_detective.__version__ import __version__
    from flac_detective.analysis.analyzer import FLACAnalyzer
    from v3_build_set_a import BAND_LIMIT_FILTER

    paths = [p for folder in PARKED for p in sorted(folder.glob("*.flac")) if p.name in MUST_MOVE]
    # The module PATH is the check that matters, not the version string.
    print(f"tree     {tree}")
    print(f"version  {__version__}")
    print(f"module   {flac_detective.__file__}")
    print(f"files    {len(paths)}/{len(MUST_MOVE)}")
    if len(paths) != len(MUST_MOVE):
        missing = MUST_MOVE - {p.name for p in paths}
        raise SystemExit(f"control files not found, nothing proved: {sorted(missing)}")

    report = {
        "tree": str(tree),
        "version": __version__,
        "module": flac_detective.__file__,
        "band_limit_filter": BAND_LIMIT_FILTER,
        "rows": {},
    }
    analyzer = FLACAnalyzer(deep=True)
    with tempfile.TemporaryDirectory() as tmp:
        for path in paths:
            band = Path(tmp) / "bl.flac"
            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(path),
                    "-map", "0:a:0", "-map_metadata", "-1",
                    "-af", BAND_LIMIT_FILTER,
                    "-ar", "44100", "-sample_fmt", "s16",
                    "-c:a", "flac", str(band),
                ],
                check=True,
                capture_output=True,
            )
            result = analyzer.analyze_file(str(band))
            report["rows"][path.name] = {
                "verdict": result.get("verdict", ""),
                "score": result.get("score", ""),
                "families": result.get("evidence_families") or [],
            }
            print(f"  {result.get('verdict', '?'):>14}  {path.name}")

    out_path.write_bytes(json.dumps(report, indent=2).encode("utf-8"))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2])))
