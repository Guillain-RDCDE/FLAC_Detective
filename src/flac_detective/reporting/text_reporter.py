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
        self.width = 100  # Report width

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

    def generate_report(self, results: list[dict[str, Any]], output_file: Path) -> None:
        """Generates a complete text report.

        Args:
            results: List of analysis results.
            output_file: Output file path.
        """
        logger.info(f"Generating text report: {output_file}")

        # Calculate statistics
        stats = calculate_statistics(results)
        # NEW SCORING: score >= 50 = suspicious
        suspicious = [r for r in results if r.get("score", 0) >= 50]

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

                filename = result.get("filename", "Unknown")

                # Truncate filename if too long
                max_name_len = self.width - 56
                if len(filename) > max_name_len:
                    filename = filename[:max_name_len-3] + "..."

                report_lines.append(f" {icon:<4} | {score_str:<7} | {verdict:<15} | {cutoff:<8} | {bitrate_str:<8} | {filename}")

        else:
            report_lines.append(" No suspicious files found. Collection looks clean.")

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
