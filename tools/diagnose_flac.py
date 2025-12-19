#!/usr/bin/env python3
"""Diagnostic tool to identify and analyze corrupted FLAC files."""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class FlacDiagnostic:
    """Diagnose FLAC file integrity issues."""

    def __init__(self, directory: Path):
        """Initialize diagnostic tool.

        Args:
            directory: Directory containing FLAC files to diagnose
        """
        self.directory = Path(directory)
        self.corrupted_files = []
        self.healthy_files = []
        self.results = {}

    def test_file(self, flac_file: Path) -> Tuple[bool, str, List[str]]:
        """Test a single FLAC file for integrity.

        Args:
            flac_file: Path to FLAC file

        Returns:
            Tuple of (is_healthy, error_type, error_messages)
        """
        try:
            # Run flac --test to verify file integrity
            result = subprocess.run(
                ["flac", "--test", "--totally-silent", str(flac_file)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, "OK", []

            # File is corrupted, parse errors
            stderr = result.stderr
            errors = []
            error_type = "UNKNOWN"

            if "LOST_SYNC" in stderr:
                error_type = "LOST_SYNC"
                errors.append("Decoder lost synchronization")

            if "BAD_HEADER" in stderr:
                error_type = "BAD_HEADER"
                errors.append("Bad frame header")

            if "FRAME_CRC_MISMATCH" in stderr:
                error_type = "CRC_MISMATCH"
                errors.append("Frame CRC mismatch")

            if "END_OF_STREAM" in stderr:
                errors.append("Unexpected end of stream")

            if not errors:
                errors.append(stderr[:200])  # First 200 chars of error

            return False, error_type, errors

        except subprocess.TimeoutExpired:
            return False, "TIMEOUT", ["File test timed out"]
        except Exception as e:
            return False, "ERROR", [str(e)]

    def scan_directory(self) -> Dict:
        """Scan directory for FLAC files and test each one.

        Returns:
            Dictionary with diagnostic results
        """
        print(f"Scanning directory: {self.directory}")
        print("=" * 80)

        flac_files = list(self.directory.rglob("*.flac"))
        total = len(flac_files)

        print(f"Found {total} FLAC files\n")

        for idx, flac_file in enumerate(flac_files, 1):
            print(f"[{idx}/{total}] Testing: {flac_file.name[:60]:<60}", end=" ")
            sys.stdout.flush()

            is_healthy, error_type, errors = self.test_file(flac_file)

            if is_healthy:
                print("[OK]")
                self.healthy_files.append(flac_file)
            else:
                print(f"[{error_type}]")
                self.corrupted_files.append({
                    "file": flac_file,
                    "error_type": error_type,
                    "errors": errors
                })

        return self.generate_report()

    def generate_report(self) -> Dict:
        """Generate diagnostic report.

        Returns:
            Dictionary with diagnostic statistics and file lists
        """
        total = len(self.healthy_files) + len(self.corrupted_files)

        report = {
            "total_files": total,
            "healthy_files": len(self.healthy_files),
            "corrupted_files": len(self.corrupted_files),
            "corruption_rate": len(self.corrupted_files) / total * 100 if total > 0 else 0,
            "error_types": {},
            "files_by_error": {}
        }

        # Count error types
        for item in self.corrupted_files:
            error_type = item["error_type"]
            report["error_types"][error_type] = report["error_types"].get(error_type, 0) + 1

            if error_type not in report["files_by_error"]:
                report["files_by_error"][error_type] = []
            report["files_by_error"][error_type].append(item)

        return report

    def print_report(self, report: Dict):
        """Print diagnostic report to console.

        Args:
            report: Report dictionary from generate_report()
        """
        print("\n" + "=" * 80)
        print("DIAGNOSTIC REPORT")
        print("=" * 80)
        print(f"Total files:       {report['total_files']}")
        print(f"Healthy files:     {report['healthy_files']} ({report['healthy_files']/report['total_files']*100:.1f}%)")
        print(f"Corrupted files:   {report['corrupted_files']} ({report['corruption_rate']:.1f}%)")
        print()

        if report["error_types"]:
            print("ERROR TYPES:")
            for error_type, count in sorted(report["error_types"].items()):
                print(f"  {error_type}: {count} file(s)")
            print()

        if self.corrupted_files:
            print("CORRUPTED FILES DETAILS:")
            print("-" * 80)
            for item in self.corrupted_files:
                print(f"\n[X] {item['file'].relative_to(self.directory)}")
                print(f"    Error type: {item['error_type']}")
                for error in item['errors']:
                    print(f"    - {error}")

        print("\n" + "=" * 80)

    def save_report(self, output_file: Path, report: Dict):
        """Save report to file.

        Args:
            output_file: Path to output file
            report: Report dictionary
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("FLAC DIAGNOSTIC REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total files:       {report['total_files']}\n")
            f.write(f"Healthy files:     {report['healthy_files']} ({report['healthy_files']/report['total_files']*100:.1f}%)\n")
            f.write(f"Corrupted files:   {report['corrupted_files']} ({report['corruption_rate']:.1f}%)\n\n")

            if report["error_types"]:
                f.write("ERROR TYPES:\n")
                for error_type, count in sorted(report["error_types"].items()):
                    f.write(f"  {error_type}: {count} file(s)\n")
                f.write("\n")

            if self.corrupted_files:
                f.write("CORRUPTED FILES (sorted by error type):\n")
                f.write("-" * 80 + "\n\n")

                for error_type, items in sorted(report["files_by_error"].items()):
                    f.write(f"\n[{error_type}] - {len(items)} file(s):\n")
                    for item in items:
                        f.write(f"  {item['file']}\n")
                        for error in item['errors']:
                            f.write(f"    - {error}\n")

        print(f"\nReport saved to: {output_file}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python diagnose_flac.py <directory>")
        print("Example: python diagnose_flac.py \"D:\\FLAC\\Internal\\Radiohead\"")
        sys.exit(1)

    directory = Path(sys.argv[1])

    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    diagnostic = FlacDiagnostic(directory)
    report = diagnostic.scan_directory()
    diagnostic.print_report(report)

    # Save report
    output_file = directory / f"flac_diagnostic_integrity_{Path(directory).name}.txt"
    diagnostic.save_report(output_file, report)


if __name__ == "__main__":
    main()
