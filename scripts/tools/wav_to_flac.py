#!/usr/bin/env python3
"""
WAV to FLAC Converter
Simple, efficient, and safe batch converter.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


# Colors for terminal
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"


def colorize(text, color):
    return f"{color}{text}{Colors.RESET}"


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("WavToFlac")


def check_flac_installed():
    """Check if flac is available in PATH."""
    try:
        subprocess.run(
            ["flac", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_file(args):
    """Convert a single file."""
    wav_path, compression_level, verify, delete_wav = args
    flac_path = wav_path.with_suffix(".flac")

    # Skip if FLAC exists
    if flac_path.exists():
        return {"status": "skipped", "file": wav_path.name, "msg": "FLAC already exists"}

    # Build command
    cmd = ["flac", f"-{compression_level}", "--silent", "--force"]
    if verify:
        cmd.append("--verify")
    cmd.append(str(wav_path))

    try:
        start_time = time.time()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        duration = time.time() - start_time

        if result.returncode == 0:
            # Check sizes
            wav_size = wav_path.stat().st_size
            flac_size = flac_path.stat().st_size
            ratio = (flac_size / wav_size) * 100

            # Delete WAV if requested
            if delete_wav:
                os.remove(wav_path)

            return {
                "status": "success",
                "file": wav_path.name,
                "wav_size": wav_size,
                "flac_size": flac_size,
                "ratio": ratio,
                "duration": duration,
            }
        else:
            return {"status": "error", "file": wav_path.name, "msg": result.stderr.decode().strip()}

    except Exception as e:
        return {"status": "error", "file": wav_path.name, "msg": str(e)}


def print_banner():
    print(
        f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              {Colors.WHITE}🎵 WAV → FLAC Converter 🎵{Colors.CYAN}                   ║
║                                                           ║
║          Simple batch converter using official           ║
║                    FLAC encoder                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    )


def main():
    # Allow drag and drop (sys.argv[1] is the folder path)
    if len(sys.argv) == 2 and not sys.argv[1].startswith("-"):
        target_dir = sys.argv[1]
        sys.argv = [sys.argv[0], target_dir]

    parser = argparse.ArgumentParser(description="Batch convert WAV files to FLAC.")
    parser.add_argument("directory", nargs="?", help="Directory containing WAV files")
    parser.add_argument("-r", "--recursive", action="store_true", help="Search recursively")
    parser.add_argument(
        "-l", "--level", type=int, default=5, choices=range(0, 9), help="Compression level (0-8)"
    )
    parser.add_argument("--no-verify", action="store_true", help="Skip integrity verification")
    parser.add_argument(
        "--delete-wav", action="store_true", help="Delete WAV files after successful conversion"
    )

    args = parser.parse_args()

    print_banner()

    # Interactive mode if no directory provided
    if not args.directory:
        print(f"  {Colors.YELLOW}Drag and drop a folder here or type the path:{Colors.RESET}")
        try:
            user_input = input("  Path: ").strip()
            if user_input:
                args.directory = user_input.strip("\"'")
            else:
                args.directory = "."
        except KeyboardInterrupt:
            sys.exit(0)

    root_dir = Path(args.directory)
    if not root_dir.exists():
        print(f"\n{Colors.RED}❌ Error: Directory not found: {root_dir}{Colors.RESET}")
        input("Press Enter to exit...")
        sys.exit(1)

    if not check_flac_installed():
        print(f"\n{Colors.RED}❌ Error: 'flac' command not found!{Colors.RESET}")
        print("Please install FLAC (https://xiph.org/flac/) and add it to your PATH.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Find WAV files
    print(f"\nScanning: {root_dir}")
    pattern = "*.wav"
    if args.recursive:
        wav_files = list(root_dir.rglob(pattern))
    else:
        wav_files = list(root_dir.glob(pattern))

    if not wav_files:
        print(f"{Colors.YELLOW}No WAV files found.{Colors.RESET}")
        input("Press Enter to exit...")
        sys.exit(0)

    print(f"{Colors.GREEN}Found {len(wav_files)} WAV files.{Colors.RESET}")
    print(
        f"Options: Level {args.level}, Verify: {not args.no_verify}, Delete WAV: {args.delete_wav}"
    )

    if args.delete_wav:
        print(
            f"\n{Colors.RED}⚠️  WARNING: WAV files will be DELETED after conversion!{Colors.RESET}"
        )
        confirm = input("  Continue? (yes/no): ").lower()
        if confirm not in ["yes", "y"]:
            print("Aborted.")
            sys.exit(0)

    print(f"\n{Colors.CYAN}=== STARTING CONVERSION ==={Colors.RESET}\n")

    success_count = 0
    total_wav_size = 0
    total_flac_size = 0

    # Process files
    # Using ThreadPoolExecutor for speed? FLAC is single threaded so multiple files can be processed in parallel.
    # But usually disk I/O is bottleneck. Let's use max 4 workers.
    max_workers = min(4, os.cpu_count() or 1)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        job_args = [(f, args.level, not args.no_verify, args.delete_wav) for f in wav_files]
        results = executor.map(convert_file, job_args)

        for i, res in enumerate(results, 1):
            if res["status"] == "success":
                success_count += 1
                total_wav_size += res["wav_size"]
                total_flac_size += res["flac_size"]
                print(f"[{i}/{len(wav_files)}] {Colors.GREEN}✓ {res['file']}{Colors.RESET}")
                print(
                    f"        {res['flac_size']/1024/1024:.1f} MB ({res['ratio']:.1f}%) - {res['duration']:.1f}s"
                )
            elif res["status"] == "skipped":
                print(
                    f"[{i}/{len(wav_files)}] {Colors.YELLOW}SKIP {res['file']} (already exists){Colors.RESET}"
                )
            else:
                print(
                    f"[{i}/{len(wav_files)}] {Colors.RED}✗ {res['file']} - {res['msg']}{Colors.RESET}"
                )

    print(f"\n{Colors.CYAN}=== COMPLETED ==={Colors.RESET}")
    if success_count > 0:
        saved = (total_wav_size - total_flac_size) / 1024 / 1024
        print(f"Converted: {success_count}/{len(wav_files)}")
        print(f"Space saved: {saved:.1f} MB")

    input("\nPress Enter to exit...")


# Fix for name 'Resources' is not defined in the code block above, I used Resources.GREEN instead of Colors.GREEN
# Let's fix that in the file content I actually write.

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
