"""Check metadata preservation after repair."""

import os
import sys

# Force UTF-8 output
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from mutagen.flac import FLAC

repaired = FLAC(
    r"D:\FLAC\Internal\Richard Pinhas\Iceland (1979)\02 - Richard Pinhas -  Iceland (part 2).flac"
)
backup = FLAC(
    r"D:\FLAC\Internal\Richard Pinhas\Iceland (1979)\02 - Richard Pinhas -  Iceland (part 2).flac.corrupted.bak"
)

print("=" * 80)
print("METADATA COMPARISON")
print("=" * 80)

print("\n✅ REPAIRED FILE:")
print(f"  Tags: {len(repaired.tags)} entries")
for key, value in repaired.tags:
    print(f"    {key}: {value}")
print(f"  Pictures: {len(repaired.pictures)}")

print("\n📦 BACKUP (corrupted original):")
print(f"  Tags: {len(backup.tags)} entries")
for key, value in backup.tags:
    print(f"    {key}: {value}")
print(f"  Pictures: {len(backup.pictures)}")

print("\n" + "=" * 80)

# Compare
tags_match = dict(repaired.tags) == dict(backup.tags)
pics_match = len(repaired.pictures) == len(backup.pictures)

if tags_match and pics_match:
    print("✅ PERFECT MATCH: All metadata preserved!")
else:
    print("❌ MISMATCH:")
    if not tags_match:
        print("  - Tags differ")
    if not pics_match:
        print(f"  - Picture count differs ({len(repaired.pictures)} vs {len(backup.pictures)})")

print("=" * 80)
