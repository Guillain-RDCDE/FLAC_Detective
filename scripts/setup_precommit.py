#!/usr/bin/env python3
"""Setup script for installing and configuring pre-commit hooks.

This script automates the installation of pre-commit hooks for FLAC Detective,
ensuring all developers have the same code quality checks in place.

Usage:
    python scripts/setup_precommit.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status.

    Args:
        cmd: Command to run as a list of strings
        description: Human-readable description of the command

    Returns:
        True if command succeeded, False otherwise
    """
    print(f"📋 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"❌ {description} - FAILED (command not found)")
        return False


def check_git_repo() -> bool:
    """Check if we're in a git repository.

    Returns:
        True if in a git repository, False otherwise
    """
    git_dir = Path(".git")
    if not git_dir.exists():
        print("❌ Not in a git repository! Please run from the repository root.")
        return False
    print("✅ Git repository detected")
    return True


def check_precommit_config() -> bool:
    """Check if .pre-commit-config.yaml exists.

    Returns:
        True if config file exists, False otherwise
    """
    config_file = Path(".pre-commit-config.yaml")
    if not config_file.exists():
        print("❌ .pre-commit-config.yaml not found!")
        return False
    print("✅ .pre-commit-config.yaml found")
    return True


def install_precommit() -> bool:
    """Install pre-commit package.

    Returns:
        True if installation succeeded, False otherwise
    """
    return run_command(
        [sys.executable, "-m", "pip", "install", "pre-commit"],
        "Installing pre-commit package",
    )


def install_hooks() -> bool:
    """Install pre-commit hooks.

    Returns:
        True if installation succeeded, False otherwise
    """
    return run_command(["pre-commit", "install"], "Installing pre-commit Git hooks")


def install_commit_msg_hook() -> bool:
    """Install commit-msg hook (optional).

    Returns:
        True if installation succeeded, False otherwise
    """
    return run_command(
        ["pre-commit", "install", "--hook-type", "commit-msg"],
        "Installing commit-msg hook (optional)",
    )


def run_initial_check() -> bool:
    """Run pre-commit on all files as an initial check.

    Returns:
        True if all checks passed, False otherwise
    """
    print("\n📋 Running initial pre-commit check on all files...")
    print("   (This may take a few minutes on first run)")
    result = run_command(
        ["pre-commit", "run", "--all-files"],
        "Running pre-commit checks on all files",
    )

    if not result:
        print("\n⚠️  Some pre-commit checks failed!")
        print("   This is normal for the first run.")
        print("   Review the output above and fix any issues.")
        print("\n   Common fixes:")
        print("   - Black/isort: Automatically fixed, just commit the changes")
        print("   - flake8: Fix code style issues manually")
        print("   - mypy: Add type hints where needed")
        return False

    print("✅ All pre-commit checks passed!")
    return True


def main() -> int:
    """Main setup function.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("=" * 70)
    print("🔧 FLAC Detective - Pre-commit Hooks Setup")
    print("=" * 70)
    print()

    # Step 1: Check prerequisites
    print("Step 1: Checking prerequisites")
    print("-" * 70)
    if not check_git_repo():
        return 1
    if not check_precommit_config():
        return 1
    print()

    # Step 2: Install pre-commit
    print("Step 2: Installing pre-commit")
    print("-" * 70)
    if not install_precommit():
        print("\n⚠️  Failed to install pre-commit package")
        print("   Try running manually: pip install pre-commit")
        return 1
    print()

    # Step 3: Install hooks
    print("Step 3: Installing Git hooks")
    print("-" * 70)
    if not install_hooks():
        print("\n⚠️  Failed to install pre-commit hooks")
        print("   Try running manually: pre-commit install")
        return 1

    # Optional: Install commit-msg hook
    install_commit_msg_hook()
    print()

    # Step 4: Run initial check
    print("Step 4: Running initial validation")
    print("-" * 70)
    run_initial_check()
    print()

    # Final summary
    print("=" * 70)
    print("✅ Pre-commit hooks installation complete!")
    print("=" * 70)
    print()
    print("ℹ️  What's next?")
    print("   - Hooks will run automatically on 'git commit'")
    print("   - To run manually: pre-commit run --all-files")
    print("   - To skip hooks: git commit --no-verify (not recommended)")
    print("   - To update hooks: pre-commit autoupdate")
    print()
    print("📚 For more info, see: docs/PRE_COMMIT_SETUP.md")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
