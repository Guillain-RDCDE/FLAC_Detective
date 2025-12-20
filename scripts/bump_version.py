#!/usr/bin/env python3
"""
Helper script to bump version and prepare release with Commitizen.

This script automates the release process:
1. Checks git status is clean
2. Runs tests
3. Bumps version with Commitizen
4. Generates CHANGELOG
5. Creates git tag
6. Optionally pushes to remote

Usage:
    python scripts/bump_version.py [--increment LEVEL] [--dry-run] [--push]

Examples:
    # Auto-detect bump level from commits
    python scripts/bump_version.py

    # Force a specific bump level
    python scripts/bump_version.py --increment MINOR

    # Preview without making changes
    python scripts/bump_version.py --dry-run

    # Bump and push immediately
    python scripts/bump_version.py --push
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True, capture_output=True):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, check=check, capture_output=capture_output, text=True
    )
    if capture_output and result.stdout:
        print(result.stdout)
    return result


def check_git_status():
    """Check if git working directory is clean."""
    print("\n📋 Checking git status...")
    result = run_command(["git", "status", "--porcelain"])

    if result.stdout.strip():
        print("❌ Error: Git working directory is not clean.")
        print("Please commit or stash your changes first.")
        print("\nUncommitted changes:")
        print(result.stdout)
        return False

    print("✅ Git working directory is clean")
    return True


def run_tests():
    """Run the test suite."""
    print("\n🧪 Running tests...")
    try:
        result = run_command(
            ["python", "-m", "pytest", "tests/", "-v"],
            check=True
        )
        print("✅ All tests passed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Tests failed. Fix the issues before bumping version.")
        return False


def preview_changelog():
    """Preview what will be in the changelog."""
    print("\n📝 Preview of changelog changes:")
    print("=" * 60)
    result = run_command(["cz", "changelog", "--dry-run"], check=True)
    print("=" * 60)
    return True


def bump_version(increment=None, dry_run=False):
    """Bump version using Commitizen."""
    print("\n🚀 Bumping version...")

    cmd = ["cz", "bump", "--changelog"]

    if increment:
        cmd.extend(["--increment", increment.upper()])

    if dry_run:
        cmd.append("--dry-run")

    try:
        result = run_command(cmd, check=True)

        if dry_run:
            print("✅ Dry run completed successfully")
        else:
            print("✅ Version bumped successfully")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error bumping version: {e}")
        return False


def push_changes():
    """Push commits and tags to remote."""
    print("\n📤 Pushing to remote...")

    try:
        # Push commits
        run_command(["git", "push"], check=True)
        print("✅ Commits pushed")

        # Push tags
        run_command(["git", "push", "--tags"], check=True)
        print("✅ Tags pushed")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error pushing to remote: {e}")
        return False


def get_current_version():
    """Get the current version from git tags."""
    try:
        result = run_command(
            ["git", "describe", "--tags", "--abbrev=0"],
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "No tags yet"


def main():
    parser = argparse.ArgumentParser(
        description="Bump version and prepare release",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--increment",
        choices=["MAJOR", "MINOR", "PATCH"],
        help="Force a specific version increment level"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push commits and tags to remote after bumping"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests (not recommended)"
    )

    args = parser.parse_args()

    print("🔧 FLAC Detective Version Bump Tool")
    print("=" * 60)

    # Get current version
    current_version = get_current_version()
    print(f"Current version: {current_version}")

    # Check git status (skip in dry-run mode)
    if not args.dry_run and not check_git_status():
        sys.exit(1)

    # Run tests (unless skipped or dry-run)
    if not args.skip_tests and not args.dry_run:
        if not run_tests():
            response = input("\n⚠️  Tests failed. Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)

    # Preview changelog
    preview_changelog()

    # Confirm before proceeding (unless dry-run)
    if not args.dry_run:
        print("\n" + "=" * 60)
        response = input("Continue with version bump? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    # Bump version
    if not bump_version(args.increment, args.dry_run):
        sys.exit(1)

    if args.dry_run:
        print("\n✅ Dry run completed. No changes were made.")
        print("\nTo apply these changes, run without --dry-run")
        sys.exit(0)

    # Get new version
    new_version = get_current_version()
    print(f"\n🎉 Version bumped: {current_version} → {new_version}")

    # Push if requested
    if args.push:
        if not push_changes():
            print("\n⚠️  Version was bumped but push failed.")
            print("You can push manually with: git push && git push --tags")
            sys.exit(1)

        print(f"\n✅ Release {new_version} is complete!")
        print(f"GitHub Actions will now build and publish to PyPI.")
    else:
        print("\n✅ Version bump complete!")
        print("\nNext steps:")
        print("1. Review the changes: git log -1 && git show")
        print("2. Push when ready: git push && git push --tags")

    return 0


if __name__ == "__main__":
    sys.exit(main())
