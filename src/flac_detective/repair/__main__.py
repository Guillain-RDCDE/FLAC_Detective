"""Point d'entrée CLI pour le module de réparation."""

import argparse
import logging
import sys
from pathlib import Path

from ..utils import LOGO
from .fixer import FLACDurationFixer

logger = logging.getLogger(__name__)


def main():
    """Fonction principale du CLI de réparation."""
    # Afficher le logo
    print(LOGO)
    print()

    parser = argparse.ArgumentParser(
        description="Répare automatiquement les problèmes de durée FLAC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Simulation (dry run) sur un fichier
  python3 -m flac_detective.repair fichier.flac --dry-run

  # Réparation réelle d'un fichier
  python3 -m flac_detective.repair fichier.flac

  # Réparation d'un dossier (récursif)
  python3 -m flac_detective.repair /chemin/vers/dossier --recursive

  # Sans créer de backup
  python3 -m flac_detective.repair fichier.flac --no-backup
        """,
    )

    parser.add_argument("path", type=str, help="Fichier ou dossier à traiter")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans modification")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Parcourir les sous-dossiers (pour dossier)"
    )
    parser.add_argument("--no-backup", action="store_true", help="Ne pas créer de backup .bak")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        logger.error(f"❌ Chemin introuvable: {path}")
        sys.exit(1)

    # Créer le fixer
    fixer = FLACDurationFixer(create_backup=not args.no_backup)

    # Traitement
    if path.is_file():
        if path.suffix.lower() != ".flac":
            logger.error("❌ Le fichier doit être un .flac")
            sys.exit(1)

        result = fixer.fix_file(path, dry_run=args.dry_run)

        if not result.get("success", False) and not result.get("skipped", False):
            sys.exit(1)

    elif path.is_dir():
        results = fixer.fix_directory(path, dry_run=args.dry_run, recursive=args.recursive)

        if results["errors"] > 0:
            sys.exit(1)

    else:
        logger.error(f"❌ Le chemin n'est ni un fichier ni un dossier: {path}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        sys.exit(1)
