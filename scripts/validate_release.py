#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate release configuration and version consistency.

This script performs comprehensive validation before a release:
1. Checks version consistency across all files
2. Validates CHANGELOG.md format and content
3. Verifies package build configuration
4. Checks for common release mistakes

Usage:
    python scripts/validate_release.py
    python scripts/validate_release.py --version 0.9.0
"""

import argparse
import io
import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ReleaseValidator:
    """Validates release configuration and catches common mistakes."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, message):
        """Record an error."""
        self.errors.append(message)
        print(f"❌ ERROR: {message}")

    def warning(self, message):
        """Record a warning."""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def success(self, message):
        """Print a success message."""
        print(f"✅ {message}")

    def get_version_from_file(self, file_path, pattern):
        """Extract version from a file using a regex pattern."""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            self.error(f"Failed to read {file_path}: {e}")
            return None

    def validate_version_consistency(self, expected_version=None):
        """Check that all version files have consistent version numbers."""
        print("\n📋 Validating version consistency...")

        # Get versions from all files
        version_py = self.get_version_from_file(
            "src/flac_detective/__version__.py", r'^__version__ = ["\']([^"\']+)["\']'
        )

        pyproject_version = self.get_version_from_file(
            "pyproject.toml", r'^version = ["\']([^"\']+)["\']'
        )

        versions = {
            "__version__.py": version_py,
            "pyproject.toml": pyproject_version,
        }

        # Check for missing versions
        for file, version in versions.items():
            if version is None:
                self.error(f"Could not find version in {file}")

        # Check consistency
        unique_versions = set(v for v in versions.values() if v is not None)

        if len(unique_versions) == 0:
            self.error("No versions found in any file")
        elif len(unique_versions) > 1:
            self.error(f"Version mismatch across files: {versions}")
        else:
            current_version = unique_versions.pop()
            self.success(f"All version files consistent: {current_version}")

            # Check against expected version if provided
            if expected_version and current_version != expected_version:
                self.error(
                    f"Version mismatch: expected {expected_version}, "
                    f"found {current_version}"
                )

            return current_version

        return None

    def validate_changelog(self, version):
        """Validate CHANGELOG.md format and content."""
        print("\n📋 Validating CHANGELOG.md...")

        changelog_path = Path("CHANGELOG.md")
        if not changelog_path.exists():
            self.error("CHANGELOG.md not found")
            return

        content = changelog_path.read_text(encoding="utf-8")

        # Check for version entry
        version_pattern = rf"## \[{re.escape(version)}\]"
        if not re.search(version_pattern, content):
            self.error(f"No CHANGELOG.md entry found for version {version}")
            return

        self.success(f"CHANGELOG.md has entry for version {version}")

        # Extract changelog section
        section_pattern = rf"## \[{re.escape(version)}\].*?\n(.*?)(?=\n## \[|$)"
        match = re.search(section_pattern, content, re.DOTALL)

        if match:
            section_content = match.group(1).strip()

            # Check section is not empty
            if len(section_content) < 50:
                self.warning(
                    f"CHANGELOG section for {version} seems very short "
                    f"({len(section_content)} chars)"
                )

            # Check for common sections
            has_added = "### Added" in section_content
            has_changed = "### Changed" in section_content
            has_fixed = "### Fixed" in section_content

            if not (has_added or has_changed or has_fixed):
                self.warning("CHANGELOG section has no standard subsections (Added/Changed/Fixed)")

            # Check for date
            date_pattern = r"## \[" + re.escape(version) + r"\] - (\d{4}-\d{2}-\d{2})"
            if not re.search(date_pattern, content):
                self.warning(f"CHANGELOG entry for {version} missing date")

    def validate_pyproject_toml(self):
        """Validate pyproject.toml configuration."""
        print("\n📋 Validating pyproject.toml...")

        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            self.error("pyproject.toml not found")
            return

        content = pyproject_path.read_text(encoding="utf-8")

        # Check required fields
        required_fields = [
            ("name", r'^name = "([^"]+)"'),
            ("version", r'^version = "([^"]+)"'),
            ("description", r'^description = "([^"]+)"'),
            ("readme", r'^readme = "([^"]+)"'),
            ("requires-python", r'^requires-python = "([^"]+)"'),
        ]

        for field_name, pattern in required_fields:
            if not re.search(pattern, content, re.MULTILINE):
                self.error(f"Missing required field in pyproject.toml: {field_name}")

        self.success("pyproject.toml has all required fields")

        # Check classifiers
        if "classifiers" not in content:
            self.warning("No classifiers in pyproject.toml")

        # Check dependencies
        if "dependencies" not in content:
            self.warning("No dependencies listed in pyproject.toml")

    def validate_readme(self):
        """Validate README.md exists and has content."""
        print("\n📋 Validating README.md...")

        readme_path = Path("README.md")
        if not readme_path.exists():
            self.error("README.md not found")
            return

        content = readme_path.read_text(encoding="utf-8")

        if len(content) < 500:
            self.warning("README.md seems very short")
        else:
            self.success(f"README.md exists ({len(content)} chars)")

        # Check for common sections
        expected_sections = ["Installation", "Usage", "Features"]
        missing_sections = [s for s in expected_sections if s not in content]

        if missing_sections:
            self.warning(f"README.md missing sections: {', '.join(missing_sections)}")

    def validate_package_structure(self):
        """Validate basic package structure."""
        print("\n📋 Validating package structure...")

        required_paths = [
            "src/flac_detective/__init__.py",
            "src/flac_detective/__version__.py",
            "pyproject.toml",
            "README.md",
            "CHANGELOG.md",
        ]

        for path_str in required_paths:
            path = Path(path_str)
            if not path.exists():
                self.error(f"Required file missing: {path_str}")
            else:
                self.success(f"Found {path_str}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)

        if self.errors:
            print(f"\n❌ {len(self.errors)} ERROR(S):")
            for error in self.errors:
                print(f"   - {error}")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} WARNING(S):")
            for warning in self.warnings:
                print(f"   - {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
            return True
        elif not self.errors:
            print("\n⚠️  Validation passed with warnings")
            print("   Consider addressing warnings before release")
            return True
        else:
            print("\n❌ Validation failed!")
            print("   Fix errors before proceeding with release")
            return False


def main():
    parser = argparse.ArgumentParser(description="Validate release configuration")
    parser.add_argument(
        "--version",
        help="Expected version to validate (e.g., 0.9.0)",
    )

    args = parser.parse_args()

    validator = ReleaseValidator()

    print("🔍 FLAC Detective Release Validator")
    print("=" * 70)

    # Run all validations
    current_version = validator.validate_version_consistency(args.version)

    if current_version:
        validator.validate_changelog(current_version)

    validator.validate_pyproject_toml()
    validator.validate_readme()
    validator.validate_package_structure()

    # Print summary and exit with appropriate code
    success = validator.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
