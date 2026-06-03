"""CSV report writer — a library-triage view, sorted most-suspicious first.

Where the text report is for reading and the JSON report is for machines, the CSV
report is for *triaging a whole collection*: one row per file, ranked by score so
the files most likely to be transcodes are at the top, and openable in any
spreadsheet for further sorting/filtering.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

# Columns written, in order. Kept stable so downstream scripts/spreadsheets can rely on it.
_FIELDNAMES = [
    "rank",
    "score",
    "verdict",
    "filename",
    "cutoff_freq_hz",
    "sample_rate",
    "bit_depth",
    "reason",
    "filepath",
]


class CSVReporter:
    """Write analysis results to a CSV, ranked by descending score."""

    def generate_report(
        self,
        results: List[Dict[str, Any]],
        output_file: Path,
        scan_paths: Optional[List[Path]] = None,
    ) -> None:
        """Write ``results`` to ``output_file`` as CSV, most-suspicious first.

        Args:
            results: Per-file analysis result dicts (as returned by FLACAnalyzer).
            output_file: Destination CSV path.
            scan_paths: Unused; accepted for interface parity with TextReporter.
        """
        ranked = sorted(results, key=lambda r: r.get("score", 0) or 0, reverse=True)

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for rank, r in enumerate(ranked, start=1):
                cutoff = r.get("cutoff_freq")
                writer.writerow(
                    {
                        "rank": rank,
                        "score": r.get("score", ""),
                        "verdict": r.get("verdict", ""),
                        "filename": r.get("filename", ""),
                        "cutoff_freq_hz": round(cutoff) if isinstance(cutoff, (int, float)) else "",
                        "sample_rate": r.get("sample_rate", ""),
                        "bit_depth": r.get("bit_depth", ""),
                        # Reason can carry newlines/pipes; CSV quoting handles commas/quotes,
                        # but collapse newlines so each record stays on one row.
                        "reason": str(r.get("reason", "")).replace("\n", " ").strip(),
                        "filepath": r.get("filepath", ""),
                    }
                )
