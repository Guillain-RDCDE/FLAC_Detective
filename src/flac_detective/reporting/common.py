"""Helpers shared by every report surface (text, CSV, HTML, console, GUI)."""

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ..analysis.new_scoring import determine_verdict


def verdict_of(result: Dict) -> str:
    """The authoritative verdict of a result row.

    ``verdict`` as written by the analyzer when present; otherwise derived from
    the score with ``determine_verdict`` for rows that predate verdict
    assignment. No report surface recomputes its own cut points from the score.
    """
    return result.get("verdict") or determine_verdict(result.get("score", 0))[0]


def rank_by_score(results: Iterable[Dict]) -> List[Dict]:
    """Most suspicious first: sorted by score, descending, a missing score as 0.

    ``sorted`` is stable, so rows with equal scores keep their input order.
    """
    return sorted(results, key=lambda r: r.get("score", 0) or 0, reverse=True)


def display_path(result: Dict, scan_paths: Optional[List[Path]], prefix: str = "") -> str:
    """The path shown to the reader: relative to the first scan root that contains it.

    Falls back to the bare filename when no root matches or anything goes wrong.
    ``prefix`` is put in front of a relative path (the text report uses a leading
    backslash to mark "relative to the scan root"; the HTML report uses none).
    Never truncated: the full path is what a reader needs to find the file.
    """
    name = result.get("filename", "Unknown")
    filepath = result.get("filepath", "")
    if scan_paths and filepath:
        try:
            p = Path(filepath)
            for root in scan_paths:
                try:
                    return f"{prefix}{p.relative_to(root)}"
                except ValueError:
                    continue
        except Exception:
            pass  # Keep the filename if anything about the paths is unusable
    return str(name)
