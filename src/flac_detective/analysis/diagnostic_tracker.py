"""Diagnostic tracker for monitoring file analysis issues.

This module tracks all issues encountered during file analysis to provide
a detailed diagnostic report at the end.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class IssueType(Enum):
    """Types of issues that can occur during analysis."""

    PARTIAL_READ = "partial_read"  # File was read but incomplete
    REPAIR_ATTEMPTED = "repair_attempted"  # File required repair attempt
    REPAIR_FAILED = "repair_failed"  # Repair was unsuccessful
    READ_FAILED = "read_failed"  # Complete read failure after all retries
    DECODER_SYNC_LOST = "decoder_sync_lost"  # FLAC decoder lost sync
    SEEK_FAILED = "seek_failed"  # Internal seek failure
    CORRUPTED = "corrupted"  # File appears corrupted


@dataclass
class FileIssue:
    """Details about an issue encountered with a file."""

    filepath: str
    issue_type: IssueType
    message: str
    frames_read: Optional[int] = None  # For partial reads
    total_frames: Optional[int] = None  # For partial reads
    retry_count: int = 0
    timestamp: str = ""


class DiagnosticTracker:
    """Tracks all analysis issues for diagnostic reporting."""

    def __init__(self):
        """Initialize the diagnostic tracker."""
        self._issues: Dict[str, List[FileIssue]] = {}
        self._files_analyzed: int = 0
        self._files_with_issues: int = 0

    def record_issue(
        self,
        filepath: str,
        issue_type: IssueType,
        message: str,
        frames_read: Optional[int] = None,
        total_frames: Optional[int] = None,
        retry_count: int = 0,
    ):
        """Record an issue encountered during file analysis.

        Args:
            filepath: Path to the file
            issue_type: Type of issue encountered
            message: Detailed error message
            frames_read: Number of frames successfully read (for partial reads)
            total_frames: Total frames in file (for partial reads)
            retry_count: Number of retries attempted
        """
        from datetime import datetime

        issue = FileIssue(
            filepath=filepath,
            issue_type=issue_type,
            message=message,
            frames_read=frames_read,
            total_frames=total_frames,
            retry_count=retry_count,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )

        if filepath not in self._issues:
            self._issues[filepath] = []
            self._files_with_issues += 1

        self._issues[filepath].append(issue)
        logger.debug(f"DIAGNOSTIC: Recorded {issue_type.value} for {Path(filepath).name}")

    def increment_files_analyzed(self):
        """Increment the counter of files analyzed."""
        self._files_analyzed += 1

    def get_files_with_issues(self) -> List[str]:
        """Get list of all files that had issues.

        Returns:
            List of file paths with issues
        """
        return list(self._issues.keys())

    def get_issues_for_file(self, filepath: str) -> List[FileIssue]:
        """Get all issues for a specific file.

        Args:
            filepath: Path to the file

        Returns:
            List of issues for this file
        """
        return self._issues.get(filepath, [])

    def has_critical_issues(self, filepath: str) -> bool:
        """Check if a file has critical issues (complete read failure).

        Args:
            filepath: Path to the file

        Returns:
            True if file has critical issues
        """
        if filepath not in self._issues:
            return False

        critical_types = {IssueType.READ_FAILED, IssueType.CORRUPTED}
        return any(issue.issue_type in critical_types for issue in self._issues[filepath])

    def get_statistics(self) -> Dict:
        """Get diagnostic statistics.

        Returns:
            Dictionary with diagnostic statistics
        """
        stats = {
            "total_files": self._files_analyzed,
            "files_with_issues": self._files_with_issues,
            "clean_files": self._files_analyzed - self._files_with_issues,
            "issue_types": {},
            "critical_failures": 0,
        }

        # Count issues by type
        for filepath, issues in self._issues.items():
            for issue in issues:
                issue_type_name = issue.issue_type.value
                stats["issue_types"][issue_type_name] = (
                    stats["issue_types"].get(issue_type_name, 0) + 1
                )

            # Count critical failures
            if self.has_critical_issues(filepath):
                stats["critical_failures"] += 1

        return stats

    def generate_report(self) -> str:
        """Generate a detailed diagnostic report.

        Returns:
            Formatted diagnostic report as string
        """
        stats = self.get_statistics()

        lines = []
        lines.append("=" * 80)
        lines.append("DIAGNOSTIC REPORT - File Analysis Issues")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY:")
        lines.append(f"  Total files analyzed: {stats['total_files']}")
        lines.append(
            f"  Files with issues: {stats['files_with_issues']} ({stats['files_with_issues']/max(stats['total_files'], 1)*100:.1f}%)"
        )
        lines.append(f"  Clean files: {stats['clean_files']}")
        lines.append(f"  Critical failures: {stats['critical_failures']}")
        lines.append("")

        # Issue types breakdown
        if stats["issue_types"]:
            lines.append("ISSUE TYPES:")
            for issue_type, count in sorted(stats["issue_types"].items()):
                lines.append(f"  {issue_type}: {count}")
            lines.append("")

        # Detailed file list
        if self._issues:
            lines.append("DETAILED FILE ISSUES:")
            lines.append("-" * 80)

            for filepath in sorted(self._issues.keys()):
                filename = Path(filepath).name
                issues = self._issues[filepath]

                # Mark critical issues
                is_critical = self.has_critical_issues(filepath)
                marker = "[CRITICAL]" if is_critical else "[WARNING]"

                lines.append(f"\n{marker} {filename}")
                lines.append(f"  Path: {filepath}")

                for idx, issue in enumerate(issues, 1):
                    lines.append(f"  Issue {idx}: {issue.issue_type.value}")
                    lines.append(f"    Time: {issue.timestamp}")
                    lines.append(f"    Message: {issue.message}")

                    if issue.frames_read is not None and issue.total_frames is not None:
                        completion = (
                            (issue.frames_read / issue.total_frames * 100)
                            if issue.total_frames > 0
                            else 0
                        )
                        lines.append(
                            f"    Data read: {issue.frames_read}/{issue.total_frames} frames ({completion:.1f}%)"
                        )

                    if issue.retry_count > 0:
                        lines.append(f"    Retries: {issue.retry_count}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def clear(self):
        """Clear all tracked issues."""
        self._issues.clear()
        self._files_analyzed = 0
        self._files_with_issues = 0


# Global instance for tracking across the application
_global_tracker: Optional[DiagnosticTracker] = None


def get_tracker() -> DiagnosticTracker:
    """Get the global diagnostic tracker instance.

    Returns:
        The global DiagnosticTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = DiagnosticTracker()
    return _global_tracker


def reset_tracker():
    """Reset the global diagnostic tracker."""
    global _global_tracker
    _global_tracker = DiagnosticTracker()
