"""CLI entry point for the repair module."""

import argparse
import logging
import sys
from pathlib import Path

from ..utils import LOGO
from .fixer import FLACDurationFixer

logger = logging.getLogger(__name__)


def main():
    """Main CLI function for repair."""
    # Display logo
    print(LOGO)
    print()

    parser = argparse.ArgumentParser(
        description="Automatically repairs FLAC duration issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulation (dry run) on a file
  python3 -m flac_detective.repair file.flac --dry-run

  # Real repair of a file
  python3 -m flac_detective.repair file.flac

  # Directory repair (recursive)
  python3 -m flac_detective.repair /path/to/folder --recursive

  # Without creating backup
  python3 -m flac_detective.repair file.flac --no-backup
        """,
    )

    parser.add_argument("path", type=str, help="File or folder to process")
    parser.add_argument("--dry-run", action="store_true", help="Simulation without modification")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Scan subfolders (for folder)"
    )
    parser.add_argument("--no-backup", action="store_true", help="Do not create .bak backup")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        logger.error(f"❌ Path not found: {path}")
        sys.exit(1)

    # Create fixer
    fixer = FLACDurationFixer(create_backup=not args.no_backup)

    # Processing
    if path.is_file():
        if path.suffix.lower() != ".flac":
            logger.error("❌ File must be a .flac")
            sys.exit(1)

        result = fixer.fix_file(path, dry_run=args.dry_run)

        if not result.get("success", False) and not result.get("skipped", False):
            sys.exit(1)

    elif path.is_dir():
        results = fixer.fix_directory(path, dry_run=args.dry_run, recursive=args.recursive)

        if results["errors"] > 0:
            sys.exit(1)

    else:
        logger.error(f"❌ Path is neither a file nor a folder: {path}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
