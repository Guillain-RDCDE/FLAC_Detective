#!/usr/bin/env python3
"""
Script to update version across all project files.

This script reads the version from src/flac_detective/__version__.py
and updates it in all relevant files.

Usage:
    python scripts/update_version.py
"""

import re
import sys
from pathlib import Path

# Add src to path to import __version__
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flac_detective.__version__ import __version__, __release_date__

# Project root
ROOT = Path(__file__).parent.parent

# Files to update with their patterns
FILES_TO_UPDATE = {
    "pyproject.toml": [
        (r'version = "[^"]*"', f'version = "{__version__}"'),
    ],
    "README.md": [
        (
            r"Advanced FLAC Authenticity Analyzer - v[0-9.]+",
            f"Advanced FLAC Authenticity Analyzer - v{__version__}",
        ),
        (r"\*\*Version\*\*: [0-9.]+", f"**Version**: {__version__}"),
        (r"FLAC Detective v[0-9.]+", f"FLAC Detective v{__version__}"),
    ],
    "CHANGELOG.md": [
        # Don't auto-update CHANGELOG, it should be manual
    ],
    "docs/README.md": [
        (r"FLAC Detective v[0-9.]+", f"FLAC Detective v{__version__}"),
    ],
    "docs/TECHNICAL_DOCUMENTATION.md": [
        (
            r"FLAC Detective v[0-9.]+ - Technical Documentation",
            f"FLAC Detective v{__version__} - Technical Documentation",
        ),
        (r"\*\*Last Updated: [^*]+\*\*", f"**Last Updated: {__release_date__}**"),
    ],
    "docs/RULE_SPECIFICATIONS.md": [
        (r"FLAC Detective v[0-9.]+", f"FLAC Detective v{__version__}"),
    ],
}


def update_file(filepath: Path, patterns: list) -> bool:
    """Update a file with the given patterns.

    Args:
        filepath: Path to the file to update
        patterns: List of (pattern, replacement) tuples

    Returns:
        True if file was modified, False otherwise
    """
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return False

    if not patterns:
        return False

    try:
        # Try UTF-8 first
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            # Fallback to latin-1
            content = filepath.read_text(encoding="latin-1")
        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")
            return False

    original_content = content

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original_content:
        try:
            filepath.write_text(content, encoding="utf-8")
            print(f"✅ Updated: {filepath.relative_to(ROOT)}")
            return True
        except Exception as e:
            print(f"❌ Error writing {filepath}: {e}")
            return False
    else:
        print(f"⏭️  No changes: {filepath.relative_to(ROOT)}")
        return False


def main():
    """Main function to update all files."""
    print(f"\n{'='*60}")
    print(f"Updating version to {__version__}")
    print(f"Release date: {__release_date__}")
    print(f"{'='*60}\n")

    updated_count = 0

    for filename, patterns in FILES_TO_UPDATE.items():
        filepath = ROOT / filename
        if update_file(filepath, patterns):
            updated_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Updated {updated_count} files")
    print(f"Version: {__version__}")
    print(f"{'='*60}\n")

    print("📝 Next steps:")
    print(f"1. Update CHANGELOG.md manually with version {__version__}")
    print(f"2. Review changes: git diff")
    print(f"3. Commit: git commit -am 'chore: Bump version to {__version__}'")
    print(f"4. Tag: git tag -a v{__version__} -m 'Release v{__version__}'")
    print(f"5. Push: git push && git push --tags")


if __name__ == "__main__":
    main()
