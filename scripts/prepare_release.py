#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare a new release by updating version numbers and validating configuration.

This script helps automate the release preparation process:
1. Updates version in all necessary files
2. Validates CHANGELOG.md has an entry for the new version
3. Creates a git tag for the release
4. Provides instructions for pushing the release

Usage:
    python scripts/prepare_release.py 0.9.0
"""

import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def get_current_version():
    """Get current version from __version__.py."""
    version_file = Path("src/flac_detective/__version__.py")
    content = version_file.read_text(encoding="utf-8")
    match = re.search(r'^__version__ = ["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Could not find __version__ in __version__.py")


def update_version_file(new_version, release_name):
    """Update src/flac_detective/__version__.py with new version."""
    version_file = Path("src/flac_detective/__version__.py")
    content = version_file.read_text(encoding="utf-8")

    # Update version
    content = re.sub(
        r'^__version__ = ["\']([^"\']+)["\']',
        f'__version__ = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )

    # Update release date
    today = date.today().isoformat()
    content = re.sub(
        r'^__release_date__ = ["\']([^"\']+)["\']',
        f'__release_date__ = "{today}"',
        content,
        flags=re.MULTILINE,
    )

    # Update release name if provided
    if release_name:
        content = re.sub(
            r'^__release_name__ = ["\']([^"\']+)["\']',
            f'__release_name__ = "{release_name}"',
            content,
            flags=re.MULTILINE,
        )

    version_file.write_text(content, encoding="utf-8")
    print(f"✅ Updated {version_file}")


def update_pyproject_toml(new_version):
    """Update version in pyproject.toml."""
    pyproject_file = Path("pyproject.toml")
    content = pyproject_file.read_text(encoding="utf-8")

    content = re.sub(
        r'^version = ["\']([^"\']+)["\']',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )

    pyproject_file.write_text(content, encoding="utf-8")
    print(f"✅ Updated {pyproject_file}")


def validate_changelog(version):
    """Validate that CHANGELOG.md has an entry for the new version."""
    changelog = Path("CHANGELOG.md")
    content = changelog.read_text(encoding="utf-8")

    # Check if version entry exists
    version_pattern = rf"## \[{re.escape(version)}\]"
    if not re.search(version_pattern, content):
        print(f"\n⚠️  WARNING: No CHANGELOG.md entry found for version {version}")
        print("\nPlease add a changelog entry in this format:")
        print(f"\n## [{version}] - {date.today().isoformat()}\n")
        print("### Added")
        print("- New feature 1")
        print("\n### Changed")
        print("- Change 1")
        print("\n### Fixed")
        print("- Bug fix 1")
        return False

    print(f"✅ CHANGELOG.md has entry for version {version}")
    return True


def extract_changelog_section(version):
    """Extract the changelog section for a specific version."""
    changelog = Path("CHANGELOG.md")
    content = changelog.read_text(encoding="utf-8")

    # Find the section for this version
    pattern = rf"## \[{re.escape(version)}\].*?\n(.*?)(?=\n## \[|$)"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        return match.group(1).strip()
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Prepare a new release by updating version numbers"
    )
    parser.add_argument("version", help="New version number (e.g., 0.9.0)")
    parser.add_argument("--release-name", help="Release name (e.g., 'Enhanced Spectral Analysis')")
    parser.add_argument("--no-tag", action="store_true", help="Skip git tag creation instructions")

    args = parser.parse_args()

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", args.version):
        print(f"❌ Error: Invalid version format '{args.version}'")
        print("   Version must be in format: MAJOR.MINOR.PATCH (e.g., 0.9.0)")
        sys.exit(1)

    current_version = get_current_version()
    print(f"\n📦 Preparing release")
    print(f"   Current version: {current_version}")
    print(f"   New version:     {args.version}")

    if args.release_name:
        print(f"   Release name:    {args.release_name}")

    # Confirm with user
    response = input("\nProceed with version update? [y/N]: ")
    if response.lower() != "y":
        print("❌ Aborted")
        sys.exit(1)

    # Update version files
    update_version_file(args.version, args.release_name)
    update_pyproject_toml(args.version)

    # Validate changelog
    changelog_ok = validate_changelog(args.version)

    print("\n" + "=" * 70)
    print("📋 Next steps:")
    print("=" * 70)

    if not changelog_ok:
        print("\n1. Update CHANGELOG.md with release notes")

    print("\n2. Review the changes:")
    print("   git diff")

    print("\n3. Commit the version bump:")
    print(f"   git add -A")
    print(f'   git commit -m "chore: Bump version to {args.version}"')

    if not args.no_tag:
        print("\n4. Create and push git tag:")
        print(f"   git tag -a v{args.version} -m 'Release v{args.version}'")
        print(f"   git push origin main")
        print(f"   git push origin v{args.version}")

        print("\n5. Monitor GitHub Actions:")
        print("   https://github.com/GuillainM/FLAC_Detective/actions")

    # Show changelog preview if available
    changelog_section = extract_changelog_section(args.version)
    if changelog_section:
        print("\n" + "=" * 70)
        print("📝 Release Notes Preview:")
        print("=" * 70)
        print(changelog_section[:500])
        if len(changelog_section) > 500:
            print("\n... (truncated)")

    print("\n✅ Release preparation complete!")


if __name__ == "__main__":
    main()
