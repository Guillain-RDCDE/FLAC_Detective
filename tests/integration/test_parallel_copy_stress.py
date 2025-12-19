"""Stress test: simulate parallel file copying like during actual scan.

This tests if corruption occurs when multiple files are copied simultaneously,
which is what happens during the actual FLAC analysis.
"""

import shutil
import tempfile
import subprocess
import hashlib
from pathlib import Path
import sys
import os
import concurrent.futures
from threading import Lock

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print_lock = Lock()

def safe_print(*args, **kwargs):
    """Thread-safe print."""
    with print_lock:
        print(*args, **kwargs)

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
        return False

def copy_and_verify(source_path, copy_num):
    """Copy a file and verify integrity (simulates one analysis task)."""
    source = Path(source_path)

    # Get original hash
    original_hash = get_file_hash(source)
    original_size = source.stat().st_size

    # Create temp copy (same as analyzer.py)
    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tmp:
        temp_path = Path(tmp.name)

    try:
        # Copy (same method as analyzer.py)
        shutil.copy2(source, temp_path)

        # Verify size
        temp_size = temp_path.stat().st_size
        if temp_size != original_size:
            return {
                'copy_num': copy_num,
                'file': source.name,
                'success': False,
                'error': f'Size mismatch: {temp_size} vs {original_size}'
            }

        # Verify hash
        temp_hash = get_file_hash(temp_path)
        if temp_hash != original_hash:
            return {
                'copy_num': copy_num,
                'file': source.name,
                'success': False,
                'error': f'Hash mismatch'
            }

        # Verify FLAC integrity
        flac_valid = test_flac_integrity(temp_path)
        if not flac_valid:
            return {
                'copy_num': copy_num,
                'file': source.name,
                'success': False,
                'error': 'FLAC validation failed'
            }

        return {
            'copy_num': copy_num,
            'file': source.name,
            'success': True,
            'size': temp_size
        }

    finally:
        if temp_path.exists():
            temp_path.unlink()

def stress_test_parallel_copies(directory, num_workers=4, copies_per_file=3):
    """Stress test: copy multiple files in parallel multiple times."""

    # Find all FLAC files
    flac_files = list(Path(directory).rglob("*.flac"))

    if not flac_files:
        safe_print(f"❌ No FLAC files found in {directory}")
        return

    # Limit to first 10 files for reasonable test duration
    flac_files = flac_files[:10]

    safe_print(f"\n{'='*80}")
    safe_print(f"PARALLEL COPY STRESS TEST")
    safe_print(f"{'='*80}")
    safe_print(f"Directory: {directory}")
    safe_print(f"Files to test: {len(flac_files)}")
    safe_print(f"Copies per file: {copies_per_file}")
    safe_print(f"Parallel workers: {num_workers}")
    safe_print(f"Total operations: {len(flac_files) * copies_per_file}")
    safe_print(f"{'='*80}\n")

    # Create task list (each file copied multiple times)
    tasks = []
    for flac_file in flac_files:
        for copy_num in range(1, copies_per_file + 1):
            tasks.append((str(flac_file), copy_num))

    # Execute in parallel
    results = []
    failures = []

    safe_print(f"Starting parallel copy operations with {num_workers} workers...\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(copy_and_verify, task[0], task[1]): task for task in tasks}

        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            if result['success']:
                safe_print(f"[{completed}/{len(tasks)}] ✅ {result['file'][:50]} (copy {result['copy_num']})")
            else:
                safe_print(f"[{completed}/{len(tasks)}] ❌ {result['file'][:50]} (copy {result['copy_num']}): {result['error']}")
                failures.append(result)

    # Summary
    safe_print(f"\n{'='*80}")
    safe_print(f"RESULTS")
    safe_print(f"{'='*80}")
    safe_print(f"Total operations: {len(results)}")
    safe_print(f"Successful: {len([r for r in results if r['success']])}")
    safe_print(f"Failed: {len(failures)}")

    if failures:
        safe_print(f"\n❌ FAILURES DETECTED:")
        for fail in failures:
            safe_print(f"  - {fail['file']} (copy {fail['copy_num']}): {fail['error']}")
        safe_print(f"\n⚠️  CONCLUSION: Parallel copying MAY introduce corruption under load!")
    else:
        safe_print(f"\n✅ CONCLUSION: All parallel copies succeeded - no corruption detected!")

    safe_print(f"{'='*80}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_parallel_copy_stress.py <directory>")
        print('\nExample: python test_parallel_copy_stress.py "D:\\FLAC\\Internal\\Richard Pinhas"')
        sys.exit(1)

    test_dir = sys.argv[1]

    # Run stress test with settings similar to actual scan
    stress_test_parallel_copies(
        directory=test_dir,
        num_workers=4,  # Simulate parallel processing
        copies_per_file=3  # Each file copied 3 times to detect intermittent issues
    )
