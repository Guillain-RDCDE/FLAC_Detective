"""Classe principale de réparation de fichiers FLAC."""

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
    """Réparateur automatique de problèmes de durée FLAC."""

    def __init__(self, create_backup: bool = True):
        """Initialise le réparateur.

        Args:
            create_backup: Si True, crée un backup .bak avant modification.
        """
        self.create_backup = create_backup
        self.fixed_count = 0
        self.error_count = 0
        self.skip_count = 0

    def check_duration_mismatch(self, filepath: Path) -> dict:
        """Vérifie si un fichier a un problème de durée.

        Args:
            filepath: Chemin vers le fichier FLAC.

        Returns:
            Dict avec: has_mismatch, metadata_duration, real_duration, diff_samples, diff_ms.
        """
        try:
            # Durée métadonnées
            audio = FLAC(filepath)
            metadata_duration = audio.info.length

            # Durée réelle
            info = sf.info(filepath)
            real_duration = info.duration

            # Calcul différence
            sample_rate = audio.info.sample_rate
            metadata_samples = int(metadata_duration * sample_rate)
            real_samples = int(real_duration * sample_rate)
            diff_samples = abs(metadata_samples - real_samples)
            diff_ms = (diff_samples / sample_rate) * 1000

            # Tolérance configurable
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
            logger.error(f"Erreur vérification {filepath.name}: {e}")
            return {"has_mismatch": False, "error": str(e)}

    def fix_file(self, filepath: Path, dry_run: bool = False) -> dict:
        """Répare un fichier FLAC avec problème de durée.

        Args:
            filepath: Chemin du fichier à réparer.
            dry_run: Si True, simule sans modifier.

        Returns:
            Dict avec: success, message, before, after.
        """
        logger.info(f"🔧 Traitement: {filepath.name}")

        # 1. Vérifier le problème
        check = self.check_duration_mismatch(filepath)

        if not check.get("has_mismatch", False):
            logger.info(f"  ✅ Aucun problème de durée (diff: {check.get('diff_ms', 0):.1f}ms)")
            self.skip_count += 1
            return {"success": False, "message": "Aucun problème détecté", "skipped": True}

        logger.info(
            f"  ⚠️  Problème détecté: {check['diff_samples']:,} samples ({check['diff_ms']:.1f}ms)"
        )

        if dry_run:
            logger.info("  🔍 [DRY RUN] Fichier serait réparé")
            return {
                "success": True,
                "message": "Dry run - pas de modification",
                "dry_run": True,
                "before": check,
            }

        # 2. Extraire les métadonnées
        logger.info("  📋 Extraction des métadonnées...")
        metadata = extract_all_metadata(filepath)

        if not metadata["success"]:
            logger.error("  ❌ Échec extraction métadonnées")
            self.error_count += 1
            return {
                "success": False,
                "message": f"Erreur extraction: {metadata.get('error', 'Unknown')}",
            }

        logger.info(f"     Tags: {len(metadata['tags'])} entrées")
        logger.info(f"     Images: {len(metadata['pictures'])} artwork(s)")

        # 3. Créer un backup si demandé
        if self.create_backup:
            backup_path = filepath.with_suffix(".flac.bak")
            logger.info(f"  💾 Création backup: {backup_path.name}")
            shutil.copy2(filepath, backup_path)

        # 4. Ré-encoder le fichier
        temp_fixed = filepath.with_suffix(".fixed.flac")

        logger.info("  🔄 Ré-encodage FLAC...")
        if not reencode_flac(filepath, temp_fixed):
            logger.error("  ❌ Échec ré-encodage")
            if temp_fixed.exists():
                temp_fixed.unlink()
            self.error_count += 1
            return {"success": False, "message": "Erreur ré-encodage"}

        # 5. Restaurer les métadonnées
        logger.info("  📝 Restauration des métadonnées...")
        if not restore_all_metadata(temp_fixed, metadata):
            logger.error("  ❌ Échec restauration métadonnées")
            temp_fixed.unlink()
            self.error_count += 1
            return {"success": False, "message": "Erreur restauration métadonnées"}

        # 6. Vérifier que le problème est résolu
        check_after = self.check_duration_mismatch(temp_fixed)

        if check_after.get("has_mismatch", True):
            logger.warning("  ⚠️  Le problème persiste après réparation!")
            logger.warning(f"     Nouvelle différence: {check_after['diff_samples']:,} samples")
            temp_fixed.unlink()
            self.error_count += 1
            return {
                "success": False,
                "message": "Problème persiste après réparation",
                "before": check,
                "after": check_after,
            }

        # 7. Remplacer le fichier original
        logger.info("  🔄 Remplacement du fichier original...")
        filepath.unlink()
        temp_fixed.rename(filepath)

        logger.info("  ✅ Fichier réparé avec succès!")
        logger.info(f"     Avant: {check['diff_samples']:,} samples ({check['diff_ms']:.1f}ms)")
        logger.info(
            f"     Après: {check_after['diff_samples']:,} samples ({check_after['diff_ms']:.1f}ms)"
        )

        self.fixed_count += 1

        return {
            "success": True,
            "message": "Réparé avec succès",
            "before": check,
            "after": check_after,
        }

    def fix_directory(
        self, directory: Path, dry_run: bool = False, recursive: bool = True
    ) -> dict:
        """Répare tous les fichiers FLAC d'un dossier.

        Args:
            directory: Dossier à traiter.
            dry_run: Si True, simule sans modifier.
            recursive: Si True, parcourt les sous-dossiers.

        Returns:
            Dict avec statistiques.
        """
        logger.info("=" * 80)
        logger.info("🔧 FLAC DETECTIVE - DURATION REPAIR MODULE")
        logger.info("=" * 80)
        logger.info(f"Dossier: {directory}")
        logger.info(f"Mode: {'DRY RUN (simulation)' if dry_run else 'RÉPARATION RÉELLE'}")
        logger.info(f"Récursif: {'Oui' if recursive else 'Non'}")
        logger.info(f"Backup: {'Oui (.bak)' if self.create_backup else 'Non'}")
        logger.info("")

        # Recherche des fichiers FLAC
        if recursive:
            flac_files = list(directory.rglob("*.flac"))
        else:
            flac_files = list(directory.glob("*.flac"))

        logger.info(f"📁 {len(flac_files)} fichiers FLAC trouvés")
        logger.info("")

        # Traitement
        results = []
        for i, filepath in enumerate(flac_files, 1):
            logger.info(f"[{i}/{len(flac_files)}] {filepath.relative_to(directory)}")
            result = self.fix_file(filepath, dry_run)
            results.append(result)
            logger.info("")

        # Statistiques finales
        logger.info("=" * 80)
        logger.info("📊 STATISTIQUES FINALES")
        logger.info("=" * 80)
        logger.info(f"Fichiers traités:     {len(flac_files)}")
        logger.info(f"Fichiers réparés:     {self.fixed_count}")
        logger.info(f"Fichiers OK:          {self.skip_count}")
        logger.info(f"Erreurs:              {self.error_count}")
        logger.info("=" * 80)

        return {
            "total": len(flac_files),
            "fixed": self.fixed_count,
            "skipped": self.skip_count,
            "errors": self.error_count,
            "results": results,
        }
