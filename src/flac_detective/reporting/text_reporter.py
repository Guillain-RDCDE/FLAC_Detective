"""Text report generation with ASCII formatting."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..__version__ import __version__
from ..analysis.new_scoring import determine_verdict
from .common import display_path, rank_by_score, verdict_of
from .evidence import RULE_LABEL, deciding_evidence
from .statistics import calculate_statistics

logger = logging.getLogger(__name__)

# What the text report (and the console summary) calls "problematic": the
# authoritative verdict says SUSPICIOUS or worse. Not a re-derived score cut
# point. Each report surface keeps its own membership (the HTML report, for
# instance, also plots WARNING files).
FLAGGED_VERDICTS = ("SUSPICIOUS", "FAKE_CERTAIN", "NON_FLAC")

# (statistic key, label in the run-level tally), in the order they are printed.
_ISSUE_TALLY = (
    ("duration_issues", "Duration"),
    ("clipping_issues", "Clip"),
    ("dc_offset_issues", "DC"),
    ("silence_issues", "Silence"),
    ("fake_high_res", "FakeHiRes"),
    ("upsampled_files", "Upsampled"),
    ("corrupted_files", "Corrupt"),
    ("non_flac_files", "Non-FLAC"),
)


class TextReporter:
    """Text report generator with ASCII formatting."""

    def __init__(self, advanced: bool = True):
        """Initialize the report generator.

        Args:
            advanced: When True (default, the historical behaviour) the report shows
                the plumbing — scores, cutoff, bitrate, per-issue counts. When False
                ('easy' mode) it prints a plain-language verdict + recommended action
                per flagged file and hides the technical columns.
        """
        self.width = 140  # Report width (increased for better file visibility)
        self.advanced = advanced

    # ------------------------------------------------------------- easy mode

    def _generate_easy(
        self, results: list[dict[str, Any]], output_file: Path, scan_paths: list[Path] | None
    ) -> None:
        """Write a plain-language report: traffic-light verdicts + actions, no plumbing."""
        from ..presentation import plain_explanation, verdict_plain

        flagged = rank_by_score(r for r in results if verdict_of(r) in FLAGGED_VERDICTS)

        lines = [
            "=" * self.width,
            f" FLAC DETECTIVE — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * self.width,
            f" {len(results)} file(s) checked · {len(flagged)} need attention.",
            "",
        ]
        if flagged:
            lines.append(" FILES TO LOOK AT")
            lines.append("")
            for r in flagged:
                icon, label, action = verdict_plain(verdict_of(r))
                lines.append(f" {icon}  {label.upper()} — {self._get_display_path(r, scan_paths)}")
                explanation = plain_explanation(r)
                if explanation:
                    lines.append(f"      {explanation}")
                lines.append(f"      → {action}")
                lines.append("")
        else:
            lines.append(" All clear — no transcodes or fakes found. Everything looks genuine.")
            lines.append("")
        lines.append(
            " Tip: run with --advanced for scores, cutoff frequencies and per-rule detail."
        )
        output_file.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Report generated (easy mode): {output_file}")

    # ------------------------------------------------------------ formatting

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

    # Rule class name -> the shortest phrase that still says what was read. Lives
    # in reporting/evidence.py since v1.13.13, shared with the GUI; kept as a
    # class attribute so nothing that read it here breaks.
    _RULE_LABEL: dict[str, str] = RULE_LABEL

    def _deciding_evidence(self, result: dict) -> str:
        """What actually carried this verdict, in one line.

        The table above reports every reading the engine took — score, format,
        cutoff, implied bitrate — and, until 1.13.11, not the one thing the reader
        actually wants: WHICH RULE DECIDED. See ``reporting.evidence`` for the
        history; the GUI prints the same line from the same function, because
        issue #8's reporter was looking at the GUI and it did not.
        """
        return deciding_evidence(result)

    def _format_label(self, result: dict) -> str:
        """Sample rate and bit depth, as "44.1/16", or "-" when unknown.

        Short because it shares a table row, and present because its absence sent
        a user hunting a container bug that was a bit-depth difference (issue #7).
        An unknown value prints as "-" rather than as a plausible default: a
        missing reading is not 16 bits.
        """
        rate = result.get("sample_rate") or 0
        depth = result.get("bit_depth") or 0
        if not rate and not depth:
            return "-"
        rate_str = f"{rate / 1000:g}" if rate else "?"
        depth_str = f"{depth}" if depth else "?"
        return f"{rate_str}/{depth_str}"

    def _score_icon(self, score: int, verdict: str = "") -> str:
        """Returns an icon for a result, driven by its authoritative verdict.

        The verdict is the single source of truth (new_scoring.determine_verdict /
        constants.py); the icon must not re-derive its own score cut points. Falls
        back to determine_verdict(score) only when no verdict is supplied.

        Args:
            score: Score from 0 to 150 (higher = more fake).
            verdict: Authoritative verdict string.

        Returns:
            ASCII icon.
        """
        if not verdict:
            verdict = determine_verdict(score)[0]
        return {
            "FAKE_CERTAIN": "[XX]",
            "NON_FLAC": "[XX]",
            "SUSPICIOUS": "[!!]",
            "WARNING": "[?]",
        }.get(verdict, "[OK]")

    def _get_display_path(
        self, result: dict[str, Any], scan_paths: list[Path] | None = None
    ) -> str:
        """Get the full display path for a file (relative to scan root if possible).

        A relative path carries a leading backslash to mark it as relative to the
        scan root. Never truncated.

        Args:
            result: Analysis result dictionary.
            scan_paths: List of scan root directories.

        Returns:
            Full path string from scan root to file (not truncated).
        """
        return display_path(result, scan_paths, prefix="\\")

    # --------------------------------------------------------- report blocks

    def _header_lines(self, stats: dict) -> list[str]:
        """The compact header: version, date, counts and the run-level quality tally."""
        lines = [
            "=" * self.width,
            f" FLAC DETECTIVE REPORT v{__version__} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * self.width,
        ]
        total = stats["total"]
        if total > 0:
            quality = (stats["authentic"] / total) * 100
            lines.append(
                f" Files: {total} | Quality: {quality:.1f}% | Authentic: {stats['authentic']} | Fake/Suspicious: {stats['fake'] + stats['suspect']}"
            )
            issues = [
                f"{label}: {stats[key]}" for key, label in _ISSUE_TALLY if stats.get(key, 0) > 0
            ]
            if issues:
                # Named for what it is, since issue #7. This is a RUN-LEVEL tally of
                # audio-quality observations — clipping, DC offset, a silent stretch
                # — and not one of them moves a score. Printed as bare "Issues:" four
                # lines above the verdict table, it was read as the reason for a
                # verdict by the reporter (twice, in writing) and by the maintainer
                # analysing his report. Two of the three rounds this issue ran for
                # were spent chasing a silence rule that had never been consulted.
                lines.append(
                    " Audio-quality notes across this run (these do not affect any verdict): "
                    + ", ".join(issues)
                )
        else:
            lines.append(" No files analyzed.")
        lines.append("-" * self.width)
        return lines

    def _suspicious_lines(
        self, suspicious: list[dict[str, Any]], scan_paths: list[Path] | None
    ) -> list[str]:
        """The verdict table, worst first, each row followed by its ``why:`` line."""
        if not suspicious:
            return [" No suspicious files found.", "-" * self.width]
        lines = [f" SUSPICIOUS FILES ({len(suspicious)})"]
        # Icon (4) | Score (7) | Verdict (15) | Format (9) | Cutoff (8) | Bitrate (8) | File
        #
        # Format carries the sample rate and bit depth, added 2026-09-03 after
        # issue #7. Someone compared one album in four containers, saw the
        # FLAC flagged and the WAV clean, and reasonably concluded the wrapper
        # decided the verdict. The likely answer was that one file was 24-bit
        # and another 16-bit — different audio, read differently on purpose —
        # and this report never said so. The CSV and HTML carried it; the
        # report most people actually read did not.
        lines.append(
            f" {'Icon':<4} | {'Score':<7} | {'Verdict':<15} | {'Format':<9} | "
            f"{'Cutoff':<8} | {'Bitrate':<8} | {'File'}"
        )
        lines.append(" " + "-" * (self.width - 2))
        for result in rank_by_score(suspicious):
            score = result.get("score", 0)
            verdict = result.get("verdict", "UNKNOWN")
            icon = self._score_icon(score, verdict)
            score_str = f"{score}/100"
            cutoff = f"{result.get('cutoff_freq', 0) / 1000:.1f}k"
            bitrate = result.get("estimated_mp3_bitrate", 0)
            bitrate_str = f"{bitrate}k" if bitrate > 0 else "-"
            fmt_str = self._format_label(result)
            display_name = self._get_display_path(result, scan_paths)
            lines.append(
                f" {icon:<4} | {score_str:<7} | {verdict:<15} | {fmt_str:<9} | "
                f"{cutoff:<8} | {bitrate_str:<8} | {display_name}"
            )
            # The reason the verdict exists, directly under the verdict. See
            # _deciding_evidence: without it this table publishes every reading
            # except the inference, and a nearby quality counter gets mistaken
            # for the motive.
            why = self._deciding_evidence(result)
            if why:
                lines.append(f"      why: {why}")
        lines.append("-" * self.width)
        return lines

    def _corrupted_lines(
        self, corrupted: list[dict[str, Any]], scan_paths: list[Path] | None
    ) -> list[str]:
        if not corrupted:
            return [" No corrupted files found.", "-" * self.width]
        lines = [
            f" CORRUPTED FILES ({len(corrupted)})",
            f" {'Icon':<4} | {'File'}",
            " " + "-" * (self.width - 2),
        ]
        for result in corrupted:
            lines.append(f" [!!] | {self._get_display_path(result, scan_paths)}")
        lines.append("-" * self.width)
        return lines

    def _upsampled_lines(
        self, upsampled: list[dict[str, Any]], scan_paths: list[Path] | None
    ) -> list[str]:
        if not upsampled:
            return [" No upsampled files found.", "-" * self.width]
        lines = [
            f" UPSAMPLED FILES ({len(upsampled)})",
            f" {'Icon':<4} | {'Original Rate':<15} | {'File'}",
            " " + "-" * (self.width - 2),
        ]
        for result in upsampled:
            display_name = self._get_display_path(result, scan_paths)
            # Check both old format (nested) and new format (flat)
            original_rate = result.get("suspected_original_rate") or result.get(
                "upsampling", {}
            ).get("suspected_original_rate", "Unknown")
            if original_rate == 0:
                original_rate = "Unknown"
            original_rate_str = (
                f"{original_rate} Hz" if isinstance(original_rate, int) else str(original_rate)
            )
            lines.append(f" [?]  | {original_rate_str:<15} | {display_name}")
        lines.append("-" * self.width)
        return lines

    @staticmethod
    def _recommendation_line(stats: dict) -> str:
        recs = []
        if stats["fake"] > 0:
            recs.append("Delete Fakes")
        if stats["suspect"] > 0:
            recs.append("Check Suspicious")
        if stats["duration_issues_critical"] > 0:
            recs.append("Repair Duration")
        return " Action: " + ", ".join(recs) if recs else " Status: All Good"

    # ---------------------------------------------------------------- report

    def generate_report(
        self, results: list[dict[str, Any]], output_file: Path, scan_paths: list[Path] | None = None
    ) -> None:
        """Generates a complete text report.

        Args:
            results: List of analysis results.
            output_file: Output file path.
            scan_paths: List of scan root directories to calculate relative paths.
        """
        logger.info(f"Generating text report: {output_file}")

        if not self.advanced:
            self._generate_easy(results, output_file, scan_paths)
            return

        stats = calculate_statistics(results)
        suspicious = [r for r in results if verdict_of(r) in FLAGGED_VERDICTS]
        corrupted = [r for r in results if r.get("is_corrupted", False)]
        upsampled = [r for r in results if r.get("is_upsampled", False)]

        report_lines = (
            self._header_lines(stats)
            + self._suspicious_lines(suspicious, scan_paths)
            + self._corrupted_lines(corrupted, scan_paths)
            + self._upsampled_lines(upsampled, scan_paths)
            + [self._recommendation_line(stats)]
        )

        output_file.write_text("\n".join(report_lines), encoding="utf-8")
        logger.info(f"Report generated: {output_file}")
