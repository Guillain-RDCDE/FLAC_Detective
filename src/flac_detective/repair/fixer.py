"""Main class for FLAC file repair."""

import logging
import shutil
from pathlib import Path

import soundfile as sf
from mutagen.flac import FLAC

from ..config import repair_config
from .encoding import reencode_flac
from .metadata import extract_all_metadata, restore_all_metadata

logger = logging.getLogger(__name__)


class FLACDurationFixer:
    """Automatic repairer for FLAC duration issues."""

    def __init__(self, create_backup: bool = True):
        """Initializes the repairer.

        Args:
            create_backup: If True, creates a .bak backup before modification.
        """
        self.create_backup = create_backup
        self.fixed_count = 0
        self.error_count = 0
        self.skip_count = 0

    def check_duration_mismatch(self, filepath: Path) -> dict:
        """Checks if a file has a duration issue.

        Args:
            filepath: Path to the FLAC file.

        Returns:
            Dict with: has_mismatch, metadata_duration, real_duration, diff_samples, diff_ms.
        """
        try:
            # Metadata duration
            audio = FLAC(filepath)
            metadata_duration = audio.info.length

            # Real duration
            info = sf.info(filepath)
            real_duration = info.duration

            # Calculate difference
            sample_rate = audio.info.sample_rate
            metadata_samples = int(metadata_duration * sample_rate)
            real_samples = int(real_duration * sample_rate)
            diff_samples = abs(metadata_samples - real_samples)
            diff_ms = (diff_samples / sample_rate) * 1000

            # Configurable tolerance
            has_mismatch = diff_samples > repair_config.DURATION_TOLERANCE_SAMPLES

            return {
                "has_mismatch": has_mismatch,
                "metadata_duration": metadata_duration,
                "real_duration": real_duration,
                "diff_samples": diff_samples,
                "diff_ms": diff_ms,
                "sample_rate": sample_rate,
            }

        except Exception as e:
            logger.error(f"Verification error {filepath.name}: {e}")
            return {"has_mismatch": False, "error": str(e)}

    def fix_file(self, filepath: Path, dry_run: bool = False) -> dict:
        """Repairs a FLAC file with duration issues.

        Args:
            filepath: Path to the file to repair.
            dry_run: If True, simulate without modifying.

        Returns:
            Dict with: success, message, before, after.
        """
        logger.info(f"🔧 Processing: {filepath.name}")

        # 1. Check for issue
        check = self.check_duration_mismatch(filepath)

        if not check.get("has_mismatch", False):
            logger.info(f"  ✅ No duration issue (diff: {check.get('diff_ms', 0):.1f}ms)")
            self.skip_count += 1
            return {"success": False, "message": "No issue detected", "skipped": True}

        logger.info(
            f"  ⚠️  Issue detected: {check['diff_samples']:,} samples ({check['diff_ms']:.1f}ms)"
        )

        if dry_run:
            logger.info("  🔍 [DRY RUN] File would be repaired")
            return {
                "success": True,
                "message": "Dry run - no modification",
                "dry_run": True,
                "before": check,
            }

        # 2. Extract metadata
        logger.info("  📋 Extracting metadata...")
        metadata = extract_all_metadata(filepath)

        if not metadata["success"]:
            logger.error("  ❌ Metadata extraction failed")
            self.error_count += 1
            return {
                "success": False,
                "message": f"Extraction error: {metadata.get('error', 'Unknown')}",
            }

        logger.info(f"     Tags: {len(metadata['tags'])} entries")
        logger.info(f"     Images: {len(metadata['pictures'])} artwork(s)")

        # 3. Create backup if requested
        if self.create_backup:
            backup_path = filepath.with_suffix(".flac.bak")
            logger.info(f"  💾 Creating backup: {backup_path.name}")
            shutil.copy2(filepath, backup_path)

        # 4. Re-encode file
        temp_fixed = filepath.with_suffix(".fixed.flac")

        logger.info("  🔄 Re-encoding FLAC...")
        if not reencode_flac(filepath, temp_fixed):
            logger.error("  ❌ Re-encoding failed")
            if temp_fixed.exists():
                temp_fixed.unlink()
            self.error_count += 1
            return {"success": False, "message": "Re-encoding error"}

        # 5. Restore metadata
        logger.info("  📝 Restoring metadata...")
        if not restore_all_metadata(temp_fixed, metadata):
            logger.error("  ❌ Metadata restoration failed")
            temp_fixed.unlink()
            self.error_count += 1
            return {"success": False, "message": "Metadata restoration error"}

        # 6. Verify fix
        check_after = self.check_duration_mismatch(temp_fixed)

        if check_after.get("has_mismatch", True):
            logger.warning("  ⚠️  Issue persists after repair!")
            logger.warning(f"     New difference: {check_after['diff_samples']:,} samples")
            temp_fixed.unlink()
            self.error_count += 1
            return {
                "success": False,
                "message": "Issue persists after repair",
                "before": check,
                "after": check_after,
            }

        # 7. Replace original file
        logger.info("  🔄 Replacing original file...")
        filepath.unlink()
        temp_fixed.rename(filepath)

        logger.info("  ✅ File repaired successfully!")
        logger.info(f"     Before: {check['diff_samples']:,} samples ({check['diff_ms']:.1f}ms)")
        logger.info(
            f"     After: {check_after['diff_samples']:,} samples ({check_after['diff_ms']:.1f}ms)"
        )

        self.fixed_count += 1

        return {
            "success": True,
            "message": "Repaired successfully",
            "before": check,
            "after": check_after,
        }

    def fix_directory(
        self, directory: Path, dry_run: bool = False, recursive: bool = True
    ) -> dict:
        """Repairs all FLAC files in a directory.

        Args:
            directory: Directory to process.
            dry_run: If True, simulate without modifying.
            recursive: If True, scan subdirectories.

        Returns:
            Dict with statistics.
        """
        logger.info("=" * 80)
        logger.info("🔧 FLAC DETECTIVE - DURATION REPAIR MODULE")
        logger.info("=" * 80)
        logger.info(f"Directory: {directory}")
        logger.info(f"Mode: {'DRY RUN (simulation)' if dry_run else 'REAL REPAIR'}")
        logger.info(f"Recursive: {'Yes' if recursive else 'No'}")
        logger.info(f"Backup: {'Yes (.bak)' if self.create_backup else 'No'}")
        logger.info("")

        # Find FLAC files
        if recursive:
            flac_files = list(directory.rglob("*.flac"))
        else:
            flac_files = list(directory.glob("*.flac"))

        logger.info(f"📁 {len(flac_files)} FLAC files found")
        logger.info("")

        # Process
        results = []
        for i, filepath in enumerate(flac_files, 1):
            logger.info(f"[{i}/{len(flac_files)}] {filepath.relative_to(directory)}")
            result = self.fix_file(filepath, dry_run)
            results.append(result)
            logger.info("")

        # Final statistics
        logger.info("=" * 80)
        logger.info("📊 FINAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Files processed:      {len(flac_files)}")
        logger.info(f"Files repaired:       {self.fixed_count}")
        logger.info(f"Files OK:             {self.skip_count}")
        logger.info(f"Errors:               {self.error_count}")
        logger.info("=" * 80)

        return {
            "total": len(flac_files),
            "fixed": self.fixed_count,
            "skipped": self.skip_count,
            "errors": self.error_count,
            "results": results,
        }
