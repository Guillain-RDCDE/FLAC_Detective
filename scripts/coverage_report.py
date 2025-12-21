#!/usr/bin/env python3
"""Generate a detailed, colorful coverage report.

This script provides a more readable coverage report than the default,
with color-coding and detailed statistics.

Usage:
    python scripts/coverage_report.py
"""

import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple


class CoverageReport:
    """Generate and display coverage reports with color."""

    def __init__(self, coverage_file: str = "coverage.xml"):
        """Initialize with coverage XML file.

        Args:
            coverage_file: Path to coverage.xml file
        """
        self.coverage_file = Path(coverage_file)
        self.min_coverage = 80.0

    def run_coverage(self) -> bool:
        """Run pytest with coverage.

        Returns:
            True if successful, False otherwise
        """
        print("🔍 Running tests with coverage...")
        print("-" * 70)

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--cov=flac_detective",
                    "--cov-report=xml",
                    "--cov-report=term-missing",
                ],
                check=False,
                capture_output=False,
            )

            if result.returncode != 0:
                print("\n⚠️  Some tests failed!")
                return False

            return True

        except Exception as e:
            print(f"\n❌ Error running coverage: {e}")
            return False

    def parse_coverage(self) -> Tuple[float, Dict[str, Dict[str, float]]]:
        """Parse coverage.xml file.

        Returns:
            Tuple of (total_coverage, file_coverage_dict)
        """
        if not self.coverage_file.exists():
            print(f"❌ Coverage file not found: {self.coverage_file}")
            sys.exit(1)

        tree = ET.parse(self.coverage_file)
        root = tree.getroot()

        # Get total coverage
        total_coverage = float(root.attrib.get("line-rate", 0)) * 100

        # Get per-file coverage
        file_coverage: Dict[str, Dict[str, float]] = {}

        for package in root.findall(".//package"):
            for cls in package.findall(".//class"):
                filename = cls.attrib.get("filename", "")
                line_rate = float(cls.attrib.get("line-rate", 0)) * 100
                branch_rate = float(cls.attrib.get("branch-rate", 0)) * 100

                if filename:
                    file_coverage[filename] = {
                        "line": line_rate,
                        "branch": branch_rate,
                    }

        return total_coverage, file_coverage

    def get_coverage_color(self, coverage: float) -> str:
        """Get ANSI color code for coverage percentage.

        Args:
            coverage: Coverage percentage (0-100)

        Returns:
            ANSI color code
        """
        if coverage >= 90:
            return "\033[92m"  # Bright green
        elif coverage >= self.min_coverage:
            return "\033[93m"  # Yellow
        else:
            return "\033[91m"  # Red

    def get_coverage_emoji(self, coverage: float) -> str:
        """Get emoji for coverage percentage.

        Args:
            coverage: Coverage percentage (0-100)

        Returns:
            Emoji string
        """
        if coverage >= 90:
            return "✅"
        elif coverage >= self.min_coverage:
            return "⚠️"
        else:
            return "❌"

    def print_detailed_report(self) -> None:
        """Print detailed coverage report with colors."""
        total_coverage, file_coverage = self.parse_coverage()

        # Header
        print("\n" + "=" * 70)
        print("📊 COVERAGE REPORT")
        print("=" * 70)

        # Total coverage
        color = self.get_coverage_color(total_coverage)
        emoji = self.get_coverage_emoji(total_coverage)
        reset = "\033[0m"

        print(f"\n{emoji} Total Coverage: {color}{total_coverage:.2f}%{reset}")
        print(f"   Minimum Required: {self.min_coverage:.0f}%")

        if total_coverage >= self.min_coverage:
            print(f"   Status: {color}PASS ✅{reset}")
        else:
            shortfall = self.min_coverage - total_coverage
            print(f"   Status: {color}FAIL ❌ (short by {shortfall:.2f}%){reset}")

        # Files sorted by coverage (lowest first)
        print("\n" + "-" * 70)
        print("📁 Coverage by File (lowest to highest)")
        print("-" * 70)

        sorted_files = sorted(file_coverage.items(), key=lambda x: x[1]["line"])

        for filename, cov in sorted_files:
            # Shorten filename for display
            short_name = filename.replace("src/flac_detective/", "")
            if len(short_name) > 50:
                short_name = "..." + short_name[-47:]

            line_cov = cov["line"]
            color = self.get_coverage_color(line_cov)
            emoji = self.get_coverage_emoji(line_cov)

            print(f"{emoji} {color}{line_cov:6.2f}%{reset}  {short_name}")

        # Coverage distribution
        print("\n" + "-" * 70)
        print("📈 Coverage Distribution")
        print("-" * 70)

        excellent = sum(1 for c in file_coverage.values() if c["line"] >= 90)
        good = sum(1 for c in file_coverage.values() if self.min_coverage <= c["line"] < 90)
        poor = sum(1 for c in file_coverage.values() if c["line"] < self.min_coverage)

        total_files = len(file_coverage)

        print(f"✅ Excellent (≥90%):  {excellent:3d} files ({excellent/total_files*100:5.1f}%)")
        print(f"⚠️  Good (≥80%):      {good:3d} files ({good/total_files*100:5.1f}%)")
        print(f"❌ Needs Work (<80%): {poor:3d} files ({poor/total_files*100:5.1f}%)")

        # Recommendations
        if poor > 0:
            print("\n" + "-" * 70)
            print("💡 Recommendations")
            print("-" * 70)
            print("Files needing attention (coverage < 80%):")

            low_coverage_files = [
                (f, c["line"]) for f, c in file_coverage.items() if c["line"] < self.min_coverage
            ]
            low_coverage_files.sort(key=lambda x: x[1])

            for filename, cov in low_coverage_files[:5]:  # Top 5
                short_name = filename.replace("src/flac_detective/", "")
                print(f"  • {short_name}: {cov:.2f}%")

            if len(low_coverage_files) > 5:
                print(f"  ... and {len(low_coverage_files) - 5} more")

        # Footer
        print("\n" + "=" * 70)
        print("📚 For more details, see: htmlcov/index.html")
        print("=" * 70 + "\n")

    def check_coverage_threshold(self, total_coverage: float) -> int:
        """Check if coverage meets minimum threshold.

        Args:
            total_coverage: Total coverage percentage

        Returns:
            Exit code (0 if pass, 1 if fail)
        """
        if total_coverage >= self.min_coverage:
            return 0
        else:
            return 1


def main() -> int:
    """Main function.

    Returns:
        Exit code
    """
    reporter = CoverageReport()

    # Run coverage
    if not reporter.run_coverage():
        print("\n⚠️  Coverage run failed, but continuing with report...")

    # Check if coverage.xml exists
    if not reporter.coverage_file.exists():
        print(f"\n❌ Coverage file not found: {reporter.coverage_file}")
        print("   Run 'pytest --cov=flac_detective --cov-report=xml' first")
        return 1

    # Print detailed report
    reporter.print_detailed_report()

    # Check threshold
    total_coverage, _ = reporter.parse_coverage()
    return reporter.check_coverage_threshold(total_coverage)


if __name__ == "__main__":
    sys.exit(main())
