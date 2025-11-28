#!/usr/bin/env python3
"""FLAC Detective v4.0 - Advanced FLAC Authenticity Analyzer.

Hunting Down Fake FLACs Since 2025

Multi-criteria detection:
- Spectral frequency analysis (MP3 cutoff detection)
- High-frequency energy ratio (context-aware)
- Metadata consistency validation
- Duration integrity checking
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from .analysis import FLACAnalyzer
from .config import analysis_config
from .reporting import TextReporter
from .tracker import ProgressTracker
from .utils import LOGO, find_flac_files

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_multiple_paths(user_input: str) -> list[str]:
    """Parse une entrée utilisateur contenant potentiellement plusieurs chemins.

    Args:
        user_input: Chaîne entrée par l'utilisateur.

    Returns:
        Liste de chemins bruts (non nettoyés).
    """
    if ";" in user_input:
        return [p.strip() for p in user_input.split(";")]
    elif "," in user_input:
        return [p.strip() for p in user_input.split(",")]
    return [user_input]


def _clean_path_string(path_str: str) -> str:
    """Nettoie les guillemets d'un chemin.

    Args:
        path_str: Chaîne de chemin potentiellement entourée de guillemets.

    Returns:
        Chemin nettoyé.
    """
    if path_str.startswith('"') and path_str.endswith('"'):
        return path_str[1:-1]
    elif path_str.startswith("'") and path_str.endswith("'"):
        return path_str[1:-1]
    return path_str


def _validate_paths(raw_paths: list[str]) -> list[Path]:
    """Valide et convertit une liste de chemins bruts en objets Path.

    Args:
        raw_paths: Liste de chemins sous forme de chaînes.

    Returns:
        Liste de Path valides (existants).
    """
    valid_paths = []
    for raw_path in raw_paths:
        if not raw_path:
            continue

        cleaned = _clean_path_string(raw_path)
        path = Path(cleaned)

        if path.exists():
            valid_paths.append(path)
            print(f"  ✅ Ajouté : {path.absolute()}")
        else:
            print(f"  ⚠️  Ignoré (n'existe pas) : {raw_path}")

    return valid_paths


def get_user_input_path() -> list[Path]:
    """Demande à l'utilisateur de saisir un ou plusieurs chemins via une interface interactive.

    Returns:
        Liste de chemins (dossiers ou fichiers) à analyser.
    """
    print(LOGO)
    print("\n" + "═" * 75)
    print("  📂 MODE INTERACTIF")
    print("═" * 75)
    print("  Glissez-déposez un ou plusieurs dossiers/fichiers ci-dessous")
    print("  (Vous pouvez séparer plusieurs chemins par des virgules ou points-virgules)")
    print("  (Ou appuyez sur Entrée pour analyser le dossier actuel)")
    print("═" * 75)

    while True:
        try:
            user_input = input("\n  👉 Chemin(s) : ").strip()

            # Si vide, utiliser le dossier courant
            if not user_input:
                return [Path.cwd()]

            # Parser et valider les chemins
            raw_paths = _parse_multiple_paths(user_input)
            valid_paths = _validate_paths(raw_paths)

            if valid_paths:
                print(f"\n  📊 Total : {len(valid_paths)} emplacement(s) sélectionné(s)")
                return valid_paths
            else:
                print("  ❌ Aucun chemin valide trouvé. Veuillez réessayer.")

        except KeyboardInterrupt:
            print("\n\n👋 Au revoir !")
            sys.exit(0)


def main():
    """Fonction principale."""
    # Détermination des chemins à analyser
    if len(sys.argv) > 1:
        # Mode ligne de commande : tous les arguments sont des chemins
        paths = [Path(arg) for arg in sys.argv[1:]]
        invalid_paths = [p for p in paths if not p.exists()]
        if invalid_paths:
            logger.error(f"❌ Chemins invalides : {', '.join(str(p) for p in invalid_paths)}")
            sys.exit(1)
        print(LOGO)
    else:
        # Mode interactif
        paths = get_user_input_path()

    print()
    print("=" * 70)
    print("  🎵 FLAC AUTHENTICITY ANALYZER")
    print("  Détection de MP3 transcodés en FLAC")
    print("  Méthode: Analyse spectrale (type Fakin' The Funk)")
    print("=" * 70)
    print()

    # Collecte de tous les fichiers FLAC depuis tous les chemins
    all_flac_files = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".flac":
            # C'est un fichier FLAC directement
            all_flac_files.append(path)
            logger.info(f"📄 Fichier ajouté : {path.name}")
        elif path.is_dir():
            # C'est un dossier, scanner récursivement
            flac_files = find_flac_files(path)
            all_flac_files.extend(flac_files)
        else:
            logger.warning(f"⚠️  Ignoré (ni fichier FLAC ni dossier) : {path}")

    if not all_flac_files:
        logger.error("❌ Aucun fichier FLAC trouvé!")
        return

    # Déterminer le dossier de sortie (pour progress.json et le rapport)
    # Utiliser le dossier du premier chemin, ou le dossier courant si c'est un fichier
    output_dir = paths[0] if paths[0].is_dir() else paths[0].parent

    # Initialisation
    analyzer = FLACAnalyzer(sample_duration=analysis_config.SAMPLE_DURATION)
    tracker = ProgressTracker(progress_file=output_dir / "progress.json")

    # Filtrer les fichiers déjà traités
    files_to_process = [f for f in all_flac_files if not tracker.is_processed(str(f))]

    if not files_to_process:
        logger.info("✅ Tous les fichiers ont déjà été traités!")
        logger.info("Supprimez progress.json pour recommencer l'analyse")
    else:
        tracker.set_total(len(all_flac_files))
        processed, total = tracker.get_progress()

        logger.info(f"📊 Reprise: {processed}/{total} fichiers déjà traités")
        logger.info(f"🔄 {len(files_to_process)} fichiers restants à analyser")
        logger.info(f"⚡ Multi-threading: {analysis_config.MAX_WORKERS} workers")
        print()

        # Analyse multi-threadée
        with ThreadPoolExecutor(max_workers=analysis_config.MAX_WORKERS) as executor:
            futures = {executor.submit(analyzer.analyze_file, f): f for f in files_to_process}

            for future in as_completed(futures):
                result = future.result()
                tracker.add_result(result)

                # Affichage du progrès
                processed, total = tracker.get_progress()
                score_icon = (
                    "✅" if result["score"] >= 90 else "⚠️" if result["score"] >= 70 else "🚨"
                )

                logger.info(
                    f"[{processed}/{total}] {score_icon} {result['filename'][:50]} "
                    f"- Score: {result['score']}%"
                )

                # Sauvegarde périodique
                if processed % analysis_config.SAVE_INTERVAL == 0:
                    tracker.save()
                    logger.info(f"💾 Progression sauvegardée ({processed}/{total})")

        # Sauvegarde finale
        tracker.save()

    # Génération du rapport texte
    logger.info("\n📊 Génération du rapport...")
    results = tracker.get_results()

    output_file = output_dir / f"rapport_flac_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    reporter = TextReporter()
    reporter.generate_report(results, output_file)

    # Résumé
    suspicious = [r for r in results if r["score"] < 90]
    print()
    print("=" * 70)
    print("  ✅ ANALYSE TERMINÉE")
    print("=" * 70)
    print(f"  📁 Fichiers analysés: {len(results)}")
    print(f"  ⚠️  Fichiers suspects: {len(suspicious)}")
    print(f"  📄 Rapport texte: {output_file.name}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur")
        print("💾 La progression est sauvegardée dans progress.json")
        print("🔄 Relancez le script pour reprendre l'analyse")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        sys.exit(1)
