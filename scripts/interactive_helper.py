#!/usr/bin/env python3
"""
FLAC Detective - Interactive Helper
Guided workflow for analysis and repair
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path so we can import flac_detective
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from flac_detective.utils import LOGO

# Define paths to scripts
SCRIPT_DIR = Path(__file__).parent
ANALYZER_SCRIPT = SCRIPT_DIR / "run_detective.py"
REPAIR_SCRIPT = SCRIPT_DIR / "repair_flac.py"


def show_workflow():
    """Displays the proposed workflow"""
    print("=" * 80)
    print("🔄 3-STEP WORKFLOW")
    print("=" * 80)
    print()

    print("STEP 1 : FULL ANALYSIS")
    print("-" * 80)
    print("First, run a full analysis of your library:")
    print()
    print(f"  python {ANALYZER_SCRIPT.name}")
    print()
    print("This generates an Excel report with all detected issues,")
    print("including files with duration mismatch.")
    print()

    print("STEP 2 : IDENTIFY FILES TO REPAIR")
    print("-" * 80)
    print("Open the Excel report and filter:")
    print()
    print("  • Column 'Duration Issue' ≠ '✓ OK'")
    print("  • OR Score < 90% with mention of inconsistent duration")
    print()
    print("Note the paths of files or folders to repair.")
    print()

    print("STEP 3A : REPAIR A SPECIFIC FILE")
    print("-" * 80)
    print("Test first in simulation mode (dry-run):")
    print()
    print(f"  python {REPAIR_SCRIPT.name} 'path/to/file.flac' --dry-run")
    print()
    print("If the result looks correct, run the real repair:")
    print()
    print(f"  python {REPAIR_SCRIPT.name} 'path/to/file.flac'")
    print()
    print("A .bak backup is created automatically.")
    print()

    print("STEP 3B : REPAIR A FULL FOLDER")
    print("-" * 80)
    print("To repair all files in an album or folder:")
    print()
    print("  # Simulation")
    print(f"  python {REPAIR_SCRIPT.name} 'path/to/folder/' --recursive --dry-run")
    print()
    print("  # Real repair")
    print(f"  python {REPAIR_SCRIPT.name} 'path/to/folder/' --recursive")
    print()

    print("STEP 4 : RE-ANALYSIS")
    print("-" * 80)
    print("After repair, re-run the analysis to verify:")
    print()
    print("  rm progress.json  # Delete old analysis")
    print(f"  python {ANALYZER_SCRIPT.name}")
    print()
    print("Repaired files should now have:")
    print("  • Duration Issue: '✓ OK'")
    print("  • Potentially improved score")
    print()

    print("=" * 80)
    print()


def show_examples():
    """Displays concrete examples"""
    print("=" * 80)
    print("📖 PRACTICAL EXAMPLES")
    print("=" * 80)
    print()

    print("EXAMPLE 1 : Single file with duration issue")
    print("-" * 80)
    print("Situation : The Excel report shows:")
    print("  • track01.flac - Score 80%")
    print("  • Duration Issue: '⚠️ Mismatch: 88,200 samples (2000ms)'")
    print()
    print("Actions:")
    print(f"  1. Test: python {REPAIR_SCRIPT.name} 'track01.flac' --dry-run")
    print(f"  2. Fix:  python {REPAIR_SCRIPT.name} 'track01.flac'")
    print("  3. Check: (Re-run analysis)")
    print()

    print("EXAMPLE 2 : Full album with incorrect durations")
    print("-" * 80)
    print("Situation : All files in an album have a 500ms mismatch")
    print("(Issue during album split/rip)")
    print()
    print("Actions:")
    print(f"  1. Test:  python {REPAIR_SCRIPT.name} 'Album/' --recursive --dry-run")
    print(f"  2. Fix:   python {REPAIR_SCRIPT.name} 'Album/' --recursive")
    print("  3. Check: Verify that .bak files were created")
    print("  4. Full re-analysis")
    print()

    print("EXAMPLE 3 : Mass repair after analysis")
    print("-" * 80)
    print("Situation : Analysis detected 125 files with duration issues")
    print()
    print("Option A - Repair folder by folder:")
    print("  for dir in 'Artist1/' 'Artist2/' 'Artist3/'; do")
    print(f'    python {REPAIR_SCRIPT.name} "$dir" --recursive')
    print("  done")
    print()
    print("Option B - Bash script to process a list:")
    print("  # Create list.txt with paths of problematic files")
    print("  while read file; do")
    print(f'    python {REPAIR_SCRIPT.name} "$file"')
    print("  done < list.txt")
    print()

    print("=" * 80)
    print()


def show_important_notes():
    """Displays important notes"""
    print("=" * 80)
    print("⚠️  IMPORTANT NOTES")
    print("=" * 80)
    print()

    print("AUTOMATIC BACKUPS")
    print("-" * 80)
    print("  • A .bak file is created BEFORE any modification")
    print("  • Format: file.flac.bak")
    print("  • Delete them after verification to save space")
    print("  • Option --no-backup to disable (not recommended)")
    print()

    print("AUDIO PROCESSING")
    print("-" * 80)
    print("  Audio processing uses the soundfile library (libsndfile):")
    print()
    print("  ✅ No external tools required")
    print("  ✅ Everything is handled by Python libraries")
    print("  ✅ Simple installation via pip")
    print()

    print("METADATA PRESERVATION")
    print("-" * 80)
    print("  The script preserves 100% of metadata:")
    print("  ✅ All Vorbis tags (artist, album, title, etc.)")
    print("  ✅ All artworks (cover images)")
    print("  ✅ Comments and custom tags")
    print("  ✅ Replay Gain")
    print("  ✅ Vendor string")
    print()

    print("WHAT HAPPENS DURING REPAIR?")
    print("-" * 80)
    print("  1. Extraction of ALL metadata (tags + images)")
    print("  2. FLAC → WAV decoding (temporary)")
    print("  3. WAV → FLAC re-encoding (correct metadata)")
    print("  4. Restoration of all metadata")
    print("  5. Verification that the issue is resolved")
    print("  6. Replacement of the original file")
    print()

    print("  The AUDIO content remains 100% identical (lossless)")
    print("  Only the FLAC container metadata is recalculated")
    print()

    print("WHEN TO REPAIR?")
    print("-" * 80)
    print("  ✅ Mismatch > 1 second : RECOMMENDED")
    print("     (Potential corruption or failed transcoding)")
    print()
    print("  ⚠️  Mismatch 100-1000ms : CASE BY CASE")
    print("     (Edited metadata, but file OK)")
    print()
    print("  ✅ Mismatch < 100ms : NOT NECESSARY")
    print("     (Normal tolerance, rounding)")
    print()

    print("=" * 80)
    print()


def show_menu():
    """Displays the interactive menu"""
    while True:
        print(LOGO)
        print("\n╔═══════════════════════════════════════════════════════════════════════╗")
        print("║                        MAIN MENU                                      ║")
        print("╚═══════════════════════════════════════════════════════════════════════╝\n")
        print("  1. 📖 View full workflow (3 steps)")
        print("  2. 💡 View practical examples")
        print("  3. ⚠️  Read important notes")
        print("  4. 🔧 Start full analysis")
        print("  5. 🛠️  Repair a specific file")
        print("  6. 📁 Repair a folder")
        print("  0. ❌ Exit")
        print()

        choice = input("Your choice: ").strip()

        if choice == "1":
            show_workflow()
            input("\nPress Enter to continue...")

        elif choice == "2":
            show_examples()
            input("\nPress Enter to continue...")

        elif choice == "3":
            show_important_notes()
            input("\nPress Enter to continue...")

        elif choice == "4":
            print("\n🔄 Starting full analysis...")
            print(f"Command: python {ANALYZER_SCRIPT.name}")
            print()
            run = input("Start now? (y/n): ").strip().lower()
            if run == "y":
                subprocess.run([sys.executable, str(ANALYZER_SCRIPT)])

        elif choice == "5":
            print("\n🛠️  REPAIR A FILE")
            print("-" * 80)
            filepath = input("Path to .flac file: ").strip().strip("\"'")

            if not Path(filepath).exists():
                print(f"❌ File not found: {filepath}")
                continue

            print("\nMode:")
            print("  1. Simulation (dry-run)")
            print("  2. Real repair")
            mode = input("Choice (1/2): ").strip()

            if mode == "1":
                cmd = [sys.executable, str(REPAIR_SCRIPT), filepath, "--dry-run"]
            elif mode == "2":
                cmd = [sys.executable, str(REPAIR_SCRIPT), filepath]
            else:
                print("❌ Invalid choice")
                continue

            print(f"\n🔄 Command: {' '.join(cmd)}")
            subprocess.run(cmd)
            input("\nPress Enter to continue...")

        elif choice == "6":
            print("\n📁 REPAIR A FOLDER")
            print("-" * 80)
            dirpath = input("Folder path: ").strip().strip("\"'")

            if not Path(dirpath).exists():
                print(f"❌ Folder not found: {dirpath}")
                continue

            recursive = input("Scan subfolders? (y/n): ").strip().lower()

            print("\nMode:")
            print("  1. Simulation (dry-run)")
            print("  2. Real repair")
            mode = input("Choice (1/2): ").strip()

            cmd = [sys.executable, str(REPAIR_SCRIPT), dirpath]

            if recursive == "y":
                cmd.append("--recursive")

            if mode == "1":
                cmd.append("--dry-run")
            elif mode != "2":
                print("❌ Invalid choice")
                continue

            print(f"\n🔄 Command: {' '.join(cmd)}")
            subprocess.run(cmd)
            input("\nPress Enter to continue...")

        elif choice == "0":
            print("\n👋 Goodbye !\n")
            break

        else:
            print("\n❌ Invalid choice\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assistant for FLAC analysis and repair")
    parser.add_argument("--workflow", action="store_true", help="Show workflow")
    parser.add_argument("--examples", action="store_true", help="Show examples")
    parser.add_argument("--notes", action="store_true", help="Show important notes")

    args = parser.parse_args()

    if args.workflow:
        show_workflow()
    elif args.examples:
        show_examples()
    elif args.notes:
        show_important_notes()
    else:
        # Interactive menu
        show_menu()
