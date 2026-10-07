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

# The hi-res verdicts that mean the label on the file is wrong. A separate axis
# from the transcode verdict: a file can be genuine lossless AND fake hi-res.
# Until 2.2.0 the text report — the one most people read — never printed them;
# they reached the CSV, the JSON and the GUI only (hi-res axis registration,
# 2026-10-07).
FAKE_HIRES_VERDICTS = ("UPSAMPLED", "PADDED_DEPTH", "UPSAMPLED_AND_PADDED")


def is_fake_hires(result: dict[str, Any]) -> bool:
    """True when the result's hi-res verdict says the file is not what it claims."""
    return result.get("hires_verdict", "") in FAKE_HIRES_VERDICTS


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
        # Fake hi-res files the transcode axis did not already flag: genuine
        # lossless audio sold at a resolution it does not have.
        fake_hires = [
            r for r in results if is_fake_hires(r) and verdict_of(r) not in FLAGGED_VERDICTS
        ]

        attention = len(flagged) + len(fake_hires)
        lines = [
            "=" * self.width,
            f" FLAC DETECTIVE — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * self.width,
            f" {len(results)} file(s) checked · {attention} need attention.",
            "",
        ]
        if flagged or fake_hires:
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
            for r in fake_hires:
                lines.append(f" 🎚️  FAKE HI-RES — {self._get_display_path(r, scan_paths)}")
                explanation = plain_explanation(r)
                if explanation:
                    lines.append(f"      {explanation}")
                lines.append(
                    "      → The audio may well be genuine lossless, but not at the "
                    "resolution on the label."
                )
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

    def _fake_hires_lines(
        self, fake_hires: list[dict[str, Any]], scan_paths: list[Path] | None
    ) -> list[str]:
        """The fake hi-res table: the hi-res verdict, the format claimed, the file.

        Replaces the "UPSAMPLED FILES" table of 1.x, which listed upsampling
        only and never a padded bit depth, and which printed the suspected
        original rate without the verdict that carried it. The ``why:`` line
        is the hi-res reason the analyzer wrote (cliff and floor, or the bits
        actually used).
        """
        if not fake_hires:
            return [" No fake hi-res files found.", "-" * self.width]
        lines = [
            f" FAKE HI-RES FILES ({len(fake_hires)})",
            f" {'Icon':<4} | {'Hi-res verdict':<20} | {'Format':<9} | {'File'}",
            " " + "-" * (self.width - 2),
        ]
        for result in fake_hires:
            display_name = self._get_display_path(result, scan_paths)
            hires_verdict = result.get("hires_verdict", "")
            fmt_str = self._format_label(result)
            lines.append(f" [?]  | {hires_verdict:<20} | {fmt_str:<9} | {display_name}")
            why = result.get("hires_reason") or ""
            if why:
                lines.append(f"      why: {why}")
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
        fake_hires = [r for r in results if is_fake_hires(r)]

        report_lines = (
            self._header_lines(stats)
            + self._suspicious_lines(suspicious, scan_paths)
            + self._corrupted_lines(corrupted, scan_paths)
            + self._fake_hires_lines(fake_hires, scan_paths)
            + [self._recommendation_line(stats)]
        )

        output_file.write_text("\n".join(report_lines), encoding="utf-8")
        logger.info(f"Report generated: {output_file}")
