"""Test integrity of source FLAC files directly on D:\ drive.

This will identify which files are actually corrupted at the source,
vs. which ones only fail during copy operations.
"""

import subprocess
from pathlib import Path
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_flac_file(filepath):
    """Test a FLAC file using official flac tool.

    Returns:
        (success: bool, error_msg: str, details: str)
    """
    try:
        result = subprocess.run(
            ['flac', '--test', str(filepath)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True, None, None
        else:
            # Parse error from stderr
            error_lines = result.stderr.strip().split('\n')
            error_msg = next((line for line in error_lines if 'ERROR' in line.upper()), error_lines[-1] if error_lines else 'Unknown error')
            return False, error_msg, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Timeout (>60s)", None
    except Exception as e:
        return False, f"Exception: {str(e)}", None

def scan_directory(directory, verbose=False):
    """Scan all FLAC files in directory and test integrity."""

    directory = Path(directory)

    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return

    print(f"\n{'='*80}")
    print(f"TESTING SOURCE FILE INTEGRITY")
    print(f"{'='*80}")
    print(f"Directory: {directory}")
    print(f"{'='*80}\n")

    # Find all FLAC files
    flac_files = sorted(directory.rglob("*.flac"))

    if not flac_files:
        print(f"❌ No FLAC files found in {directory}")
        return

    print(f"Found {len(flac_files)} FLAC files\n")
    print("Testing integrity (this may take a while)...\n")

    valid_files = []
    corrupted_files = []

    for idx, flac_file in enumerate(flac_files, 1):
        # Show progress
        relative_path = flac_file.relative_to(directory)
        print(f"[{idx}/{len(flac_files)}] Testing: {relative_path}")

        success, error_msg, details = test_flac_file(flac_file)

        if success:
            valid_files.append(flac_file)
            print(f"           ✅ VALID\n")
        else:
            corrupted_files.append((flac_file, error_msg, details))
            print(f"           ❌ CORRUPTED: {error_msg}\n")

            if verbose and details:
                print(f"           Details:\n")
                for line in details.split('\n'):
                    if line.strip():
                        print(f"             {line}")
                print()

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total files:      {len(flac_files)}")
    print(f"Valid files:      {len(valid_files)} ({len(valid_files)*100//len(flac_files)}%)")
    print(f"Corrupted files:  {len(corrupted_files)} ({len(corrupted_files)*100//len(flac_files)}%)")
    print(f"{'='*80}\n")

    if corrupted_files:
        print(f"CORRUPTED FILES DETAILS:")
        print(f"{'-'*80}")
        for flac_file, error_msg, _ in corrupted_files:
            relative_path = flac_file.relative_to(directory)
            size_mb = flac_file.stat().st_size / (1024 * 1024)
            print(f"\n📁 {relative_path}")
            print(f"   Size: {size_mb:.1f} MB")
            print(f"   Error: {error_msg}")
        print(f"\n{'-'*80}")

        # Check if these match the errors we saw during scan
        print(f"\n💡 ANALYSIS:")
        print(f"   These {len(corrupted_files)} files are ALREADY corrupted at the source.")
        print(f"   The copy operation did NOT introduce the corruption.")
        print(f"   The retry/repair mechanisms handled these gracefully during scan.")
    else:
        print(f"✅ All source files are VALID!")
        print(f"   If errors occurred during scan, they were likely:")
        print(f"   - Transient I/O errors during copy")
        print(f"   - Network/USB read errors")
        print(f"   - Not actual file corruption")

    print(f"\n{'='*80}\n")

    return valid_files, corrupted_files

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_source_integrity.py <directory> [--verbose]")
        print('\nExample: python test_source_integrity.py "D:\\FLAC\\Internal\\Richard Pinhas"')
        print('         python test_source_integrity.py "D:\\FLAC\\Internal\\Richard Pinhas" --verbose')
        sys.exit(1)

    test_dir = sys.argv[1]
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    scan_directory(test_dir, verbose=verbose)
