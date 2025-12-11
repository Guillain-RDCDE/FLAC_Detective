"""Text report generation with ASCII formatting."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .statistics import calculate_statistics

logger = logging.getLogger(__name__)


class TextReporter:
    """Text report generator with ASCII formatting."""

    def __init__(self):
        """Initialize the report generator."""
        self.width = 140  # Report width (increased for better file visibility)

    def _header(self, title: str) -> str:
        """Generates a formatted header.

        Args:
            title: Section title.

        Returns:
            Formatted header.
        """
        border = "═" * self.width
        padding = (self.width - len(title) - 2) // 2
        return f"\n{border}\n{' ' * padding} {title}\n{border}\n"

    def _section(self, title: str) -> str:
        """Generates a section title.

        Args:
            title: Section title.

        Returns:
            Formatted title.
        """
        return f"\n{'─' * self.width}\n  {title}\n{'─' * self.width}\n"

    def _table_row(self, *columns: str, widths: list[int] | None = None) -> str:
        """Generates a table row.

        Args:
            *columns: Columns to display.
            widths: Column widths (optional).

        Returns:
            Formatted row.
        """
        if widths is None:
            widths = [20, 10, 10, 15, 45]

        formatted_cols = []
        for col, width in zip(columns, widths):
            col_str = str(col)
            if len(col_str) > width:
                col_str = col_str[: width - 3] + "..."
            formatted_cols.append(col_str.ljust(width))

        return "  " + " │ ".join(formatted_cols)

    def _score_icon(self, score: int, verdict: str = "") -> str:
        """Returns an icon based on score (NEW SYSTEM: higher = more fake).

        Args:
            score: Score from 0 to 100 (higher = more fake).
            verdict: Verdict string (optional).

        Returns:
            ASCII icon.
        """
        if score >= 80:  # FAKE_CERTAIN
            return "[XX]"
        elif score >= 50:  # FAKE_PROBABLE
            return "[!!]"
        elif score >= 30:  # DOUTEUX
            return "[?]"
        else:  # AUTHENTIQUE
            return "[OK]"

    def _get_display_path(self, result: dict[str, Any], scan_paths: list[Path] | None = None) -> str:
        """Get the full display path for a file (relative to scan root if possible).

        Args:
            result: Analysis result dictionary.
            scan_paths: List of scan root directories.

        Returns:
            Full path string from scan root to file (not truncated).
        """
        display_name = result.get("filename", "Unknown")
        file_path_str = result.get("filepath", "")

        if scan_paths and file_path_str:
            try:
                p = Path(file_path_str)
                for root in scan_paths:
                    try:
                        rel_path = p.relative_to(root)
                        # Prepend separator to indicate it's a relative path from root
                        display_name = f"\\{rel_path}"
                        break
                    except ValueError:
                        continue
            except Exception:
                pass # Keep original filename if any error

        # DO NOT TRUNCATE - show full path
        return display_name

    def generate_report(self, results: list[dict[str, Any]], output_file: Path, scan_paths: list[Path] | None = None) -> None:
        """Generates a complete text report.

        Args:
            results: List of analysis results.
            output_file: Output file path.
            scan_paths: List of scan root directories to calculate relative paths.
        """
        logger.info(f"Generating text report: {output_file}")

        # Calculate statistics
        stats = calculate_statistics(results)
        # NEW SCORING: score >= 50 = suspicious
        suspicious = [r for r in results if r.get("score", 0) >= 50]
        corrupted = [r for r in results if r.get("is_corrupted", False)]
        upsampled = [r for r in results if r.get("is_upsampled", False)]

        # Build report
        report_lines = []

        # Compact Header
        report_lines.append("=" * self.width)
        report_lines.append(f" FLAC DETECTIVE REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("=" * self.width)

        # Global statistics (Compact)
        total = stats['total']
        if total > 0:
            quality = (stats["authentic"] / total) * 100
            report_lines.append(f" Files: {total} | Quality: {quality:.1f}% | Authentic: {stats['authentic']} | Fake/Suspicious: {stats['fake'] + stats['suspect']}")

            issues = []
            if stats['duration_issues'] > 0:
                issues.append(f"Duration: {stats['duration_issues']}")
            if stats['clipping_issues'] > 0:
                issues.append(f"Clip: {stats['clipping_issues']}")
            if stats['dc_offset_issues'] > 0:
                issues.append(f"DC: {stats['dc_offset_issues']}")
            if stats['silence_issues'] > 0:
                issues.append(f"Silence: {stats['silence_issues']}")
            if stats['fake_high_res'] > 0:
                issues.append(f"FakeHiRes: {stats['fake_high_res']}")
            if stats['upsampled_files'] > 0:
                issues.append(f"Upsampled: {stats['upsampled_files']}")
            if stats['corrupted_files'] > 0:
                issues.append(f"Corrupt: {stats['corrupted_files']}")
            if stats.get('non_flac_files', 0) > 0:
                issues.append(f"Non-FLAC: {stats['non_flac_files']}")

            if issues:
                report_lines.append(" Issues: " + ", ".join(issues))
        else:
            report_lines.append(" No files analyzed.")

        report_lines.append("-" * self.width)

        # Suspicious files (score < 90%)
        if suspicious:
            report_lines.append(f" SUSPICIOUS FILES ({len(suspicious)})")

            # Table header
            # Icon (4) | Score (7) | Verdict (15) | Cutoff (8) | Bitrate (8) | File (Rest)
            report_lines.append(f" {'Icon':<4} | {'Score':<7} | {'Verdict':<15} | {'Cutoff':<8} | {'Bitrate':<8} | {'File'}")
            report_lines.append(" " + "-" * (self.width - 2))

            # Sort by descending score (worst first - NEW SYSTEM: higher = worse)
            sorted_suspicious = sorted(suspicious, key=lambda x: x.get("score", 0), reverse=True)

            # Display ALL suspicious files (no limit)
            for result in sorted_suspicious:
                score = result.get("score", 0)
                verdict = result.get("verdict", "UNKNOWN")
                icon = self._score_icon(score, verdict)
                score_str = f"{score}/100"
                cutoff = f"{result.get('cutoff_freq', 0) / 1000:.1f}k"

                bitrate = result.get("estimated_mp3_bitrate", 0)
                bitrate_str = f"{bitrate}k" if bitrate > 0 else "-"

                # Get full display path (not truncated)
                display_name = self._get_display_path(result, scan_paths)

                report_lines.append(f" {icon:<4} | {score_str:<7} | {verdict:<15} | {cutoff:<8} | {bitrate_str:<8} | {display_name}")

        else:
            report_lines.append(" No suspicious files found.")


        report_lines.append("-" * self.width)

        # Corrupted files
        if corrupted:
            report_lines.append(f" CORRUPTED FILES ({len(corrupted)})")
            report_lines.append(f" {'Icon':<4} | {'File'}")
            report_lines.append(" " + "-" * (self.width - 2))

            for result in corrupted:
                display_name = self._get_display_path(result, scan_paths)
                report_lines.append(f" [!!] | {display_name}")

        else:
            report_lines.append(" No corrupted files found.")

        report_lines.append("-" * self.width)

        # Upsampled files
        if upsampled:
            report_lines.append(f" UPSAMPLED FILES ({len(upsampled)})")
            report_lines.append(f" {'Icon':<4} | {'Original Rate':<15} | {'File'}")
            report_lines.append(" " + "-" * (self.width - 2))

            for result in upsampled:
                display_name = self._get_display_path(result, scan_paths)
                original_rate = result.get("upsampling", {}).get("suspected_original_rate", "Unknown")
                original_rate_str = f"{original_rate} Hz" if isinstance(original_rate, int) else str(original_rate)
                report_lines.append(f" [?]  | {original_rate_str:<15} | {display_name}")

        else:
            report_lines.append(" No upsampled files found.")

        # Footer
        report_lines.append("-" * self.width)

        # Recommendations (Very compact)
        recs = []
        if stats["fake"] > 0:
            recs.append("Delete Fakes")
        if stats["suspect"] > 0:
            recs.append("Check Suspicious")
        if stats["duration_issues_critical"] > 0:
            recs.append("Repair Duration")

        if recs:
            report_lines.append(" Action: " + ", ".join(recs))
        else:
            report_lines.append(" Status: All Good")

        # Write file
        report_text = "\n".join(report_lines)
        output_file.write_text(report_text, encoding="utf-8")

        logger.info(f"Report generated: {output_file}")
