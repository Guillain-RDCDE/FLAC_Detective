"""Test script for diagnostic tracker."""

from src.flac_detective.analysis.diagnostic_tracker import DiagnosticTracker, IssueType


def test_diagnostic_tracker():
    """Test the diagnostic tracker functionality."""
    tracker = DiagnosticTracker()

    # Simulate some issues
    tracker.record_issue(
        filepath="/path/to/file1.flac",
        issue_type=IssueType.PARTIAL_READ,
        message="Decoder lost sync after 10000 frames",
        frames_read=10000,
        total_frames=20000,
        retry_count=5,
    )

    tracker.record_issue(
        filepath="/path/to/file1.flac",
        issue_type=IssueType.REPAIR_ATTEMPTED,
        message="Attempting repair with flac tool",
    )

    tracker.record_issue(
        filepath="/path/to/file2.flac",
        issue_type=IssueType.READ_FAILED,
        message="Complete read failure",
        retry_count=5,
    )

    tracker.increment_files_analyzed()
    tracker.increment_files_analyzed()
    tracker.increment_files_analyzed()

    # Get statistics
    stats = tracker.get_statistics()
    print("Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Files with issues: {stats['files_with_issues']}")
    print(f"  Clean files: {stats['clean_files']}")
    print(f"  Critical failures: {stats['critical_failures']}")
    print(f"  Issue types: {stats['issue_types']}")
    print()

    # Generate report
    report = tracker.generate_report()
    print(report)


if __name__ == "__main__":
    test_diagnostic_tracker()
