"""Test script to verify if copy operations introduce corruption.

This script tests whether shutil.copy2() corrupts FLAC files when copying
from external drives to temp directory.
"""

import shutil
import tempfile
import subprocess
import hashlib
from pathlib import Path
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def test_flac_integrity(filepath):
    """Test FLAC file integrity using flac --test."""
    try:
        result = subprocess.run(
            ['flac', '--test', '--totally-silent', str(filepath)],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    ❌ Error testing with flac: {e}")
        return False

def test_copy_corruption(source_path, num_tests=3):
    """Test if copying a FLAC file introduces corruption."""
    source = Path(source_path)

    if not source.exists():
        print(f"❌ Source file not found: {source}")
        return

    print(f"\n{'='*80}")
    print(f"Testing copy integrity for: {source.name}")
    print(f"Source location: {source.parent}")
    print(f"{'='*80}\n")

    # Step 1: Test original file
    print("1️⃣  Testing ORIGINAL file...")
    print(f"    Size: {source.stat().st_size:,} bytes")

    original_hash = get_file_hash(source)
    print(f"    Hash: {original_hash[:16]}...")

    original_valid = test_flac_integrity(source)
    print(f"    FLAC test: {'✅ PASS' if original_valid else '❌ FAIL'}")

    if not original_valid:
        print("\n⚠️  WARNING: Original file is already corrupted!")
        return

    # Step 2: Test multiple copies
    print(f"\n2️⃣  Testing {num_tests} COPY operations...")

    all_passed = True
    for i in range(1, num_tests + 1):
        print(f"\n  Copy #{i}:")

        # Create temp copy
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tmp:
            temp_path = Path(tmp.name)

        try:
            # Copy using shutil.copy2 (same as analyzer.py)
            print(f"    Copying to: {temp_path}")
            shutil.copy2(source, temp_path)

            # Check size
            temp_size = temp_path.stat().st_size
            size_match = temp_size == source.stat().st_size
            print(f"    Size: {temp_size:,} bytes {'✅' if size_match else '❌ MISMATCH'}")

            if not size_match:
                all_passed = False
                print(f"    ❌ Size mismatch: {temp_size} vs {source.stat().st_size}")
                continue

            # Check hash
            temp_hash = get_file_hash(temp_path)
            hash_match = temp_hash == original_hash
            print(f"    Hash: {temp_hash[:16]}... {'✅' if hash_match else '❌ MISMATCH'}")

            if not hash_match:
                all_passed = False
                print(f"    ❌ Hash mismatch!")
                print(f"       Original: {original_hash}")
                print(f"       Copy:     {temp_hash}")
                continue

            # Test FLAC integrity
            copy_valid = test_flac_integrity(temp_path)
            print(f"    FLAC test: {'✅ PASS' if copy_valid else '❌ FAIL'}")

            if not copy_valid:
                all_passed = False
                print(f"    ❌ Copy is corrupted!")

        finally:
            # Cleanup
            if temp_path.exists():
                temp_path.unlink()

    # Summary
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ RESULT: All copies are IDENTICAL and VALID")
        print("   → The copy process does NOT introduce corruption")
    else:
        print("❌ RESULT: Some copies are CORRUPTED or DIFFERENT")
        print("   → The copy process MAY introduce corruption")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_copy_integrity.py <path_to_flac_file>")
        print("\nSuggested test files from your collection:")
        print('  python test_copy_integrity.py "D:\\FLAC\\Internal\\Richard Pinhas\\L\'Ethique (1982)\\02 - Richard Pinhas -  Dedicated to k.c..flac"')
        print('  python test_copy_integrity.py "D:\\FLAC\\Internal\\Richard Pinhas\\<any_other_file>.flac"')
        sys.exit(1)

    test_file = sys.argv[1]
    test_copy_corruption(test_file, num_tests=5)
