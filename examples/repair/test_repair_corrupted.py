"""Test the improved repair function on actual corrupted files."""

import sys
import os

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add src to path
sys.path.insert(0, "src")

from flac_detective.analysis.new_scoring.audio_loader import repair_flac_file
import logging

# Setup logging to see repair progress
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")


def test_repair(file_path, replace_source=False):
    """Test repair on a corrupted file."""
    print(f"\n{'='*80}")
    print(f"Testing repair on: {file_path}")
    print(f"Replace source: {replace_source}")
    print(f"{'='*80}\n")

    repaired = repair_flac_file(
        corrupted_path=file_path,
        source_path=file_path if replace_source else None,
        replace_source=replace_source,
    )

    if repaired:
        print(f"\n✅ Repair successful!")
        print(f"   Repaired file: {repaired}")
        if replace_source:
            print(f"   Original file has been replaced")
            backup = file_path + ".corrupted.bak"
            if os.path.exists(backup):
                print(f"   Backup created: {backup}")
    else:
        print(f"\n❌ Repair failed")

    print(f"\n{'='*80}\n")
    return repaired


if __name__ == "__main__":
    # Test files identified as corrupted
    corrupted_files = [
        r"D:\FLAC\Internal\Richard Pinhas\Iceland (1979)\02 - Richard Pinhas -  Iceland (part 2).flac",
        r"D:\FLAC\Internal\Richard Pinhas\Iceland (1979)\08 - Richard Pinhas -  Greenland.flac",
    ]

    print("\n" + "=" * 80)
    print("TESTING IMPROVED REPAIR FUNCTION")
    print("=" * 80)
    print("\nThis will test repair on the 2 corrupted files found earlier.")
    print("First run: DRY RUN (no replacement)")
    print("Second run: REPLACE SOURCE (with backup)")
    print("\n" + "=" * 80)

    # First test: dry run (don't replace)
    print("\n📋 PHASE 1: Testing repair without replacing source files")
    print("-" * 80)
    for file_path in corrupted_files:
        if os.path.exists(file_path):
            test_repair(file_path, replace_source=False)
        else:
            print(f"⚠️  File not found: {file_path}")

    # Ask user if they want to proceed with replacement
    print("\n" + "=" * 80)
    response = input(
        "\n⚠️  Do you want to REPLACE the source files with repaired versions? (yes/no): "
    )
    print("=" * 80 + "\n")

    if response.lower() in ["yes", "y", "oui", "o"]:
        print("\n📋 PHASE 2: Repairing and REPLACING source files")
        print("-" * 80)
        for file_path in corrupted_files:
            if os.path.exists(file_path):
                test_repair(file_path, replace_source=True)
            else:
                print(f"⚠️  File not found: {file_path}")

        print("\n✅ DONE! Check your files:")
        for file_path in corrupted_files:
            backup = file_path + ".corrupted.bak"
            print(f"\n  Original (repaired): {file_path}")
            print(f"  Backup (corrupted):  {backup}")
    else:
        print("\n❌ Cancelled - no files were replaced")
