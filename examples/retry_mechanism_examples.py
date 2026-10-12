"""
Exemple d'utilisation du système de retry pour les erreurs de décodage FLAC.

Ce script montre comment utiliser le nouveau mécanisme de retry automatique
pour analyser des fichiers FLAC qui peuvent générer des erreurs temporaires.
"""

import logging
import sys
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flac_detective.analysis.analyzer import FLACAnalyzer
from flac_detective.analysis.new_scoring.audio_loader import load_audio_with_retry


def example_1_basic_analysis():
    """Exemple 1 : Analyse basique d'un fichier avec gestion automatique des erreurs."""
    print("\n" + "=" * 70)
    print("EXEMPLE 1 : Analyse basique avec retry automatique")
    print("=" * 70)

    # Le retry est automatique, aucune configuration nécessaire
    analyzer = FLACAnalyzer()

    # Remplacez par le chemin de votre fichier
    file_path = Path("exemple.flac")

    if not file_path.exists():
        print(f"⚠️  Fichier non trouvé : {file_path}")
        print("   Créez un fichier 'exemple.flac' ou modifiez le chemin dans le script")
        return

    print(f"\n📁 Analyse de : {file_path.name}")

    # L'analyse utilise automatiquement le retry si nécessaire
    result = analyzer.analyze_file(file_path)

    # Afficher les résultats
    print("\n📊 Résultats :")
    print(f"   Verdict : {result['verdict']}")
    print(f"   Score : {result['score']}/100")
    print(f"   Corrompu : {result['is_corrupted']}")
    print(f"   Analyse partielle : {result.get('partial_analysis', False)}")

    if result.get("partial_analysis", False):
        print("\n⚠️  Attention : Analyse partielle effectuée")
        print(f"   Raison : {result.get('corruption_error', 'N/A')}")
        print("   Les règles R9 et R11 ont échoué, mais le fichier n'est pas corrompu")
    else:
        print("\n✅ Analyse complète effectuée avec succès")


def example_2_with_debug_logs():
    """Exemple 2 : Analyse avec logs détaillés pour voir le retry en action."""
    print("\n" + "=" * 70)
    print("EXEMPLE 2 : Analyse avec logs détaillés")
    print("=" * 70)

    # Activer les logs DEBUG pour voir le retry
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    analyzer = FLACAnalyzer()
    file_path = Path("exemple.flac")

    if not file_path.exists():
        print(f"⚠️  Fichier non trouvé : {file_path}")
        return

    print(f"\n📁 Analyse de : {file_path.name}")
    print("   (Regardez les logs ci-dessous pour voir le retry en action)\n")

    result = analyzer.analyze_file(file_path)

    print(f"\n📊 Résultat final : {result['verdict']} ({result['score']}/100)")


def example_3_direct_audio_loading():
    """Exemple 3 : Utilisation directe de load_audio_with_retry."""
    print("\n" + "=" * 70)
    print("EXEMPLE 3 : Utilisation directe de load_audio_with_retry")
    print("=" * 70)

    file_path = "exemple.flac"

    print(f"\n📁 Chargement de : {file_path}")

    # Chargement avec retry automatique
    audio_data, sample_rate = load_audio_with_retry(file_path)

    if audio_data is not None:
        print("\n✅ Audio chargé avec succès !")
        print(f"   Shape : {audio_data.shape}")
        print(f"   Sample rate : {sample_rate} Hz")
        print(f"   Durée : {len(audio_data) / sample_rate:.2f} secondes")
    else:
        print("\n❌ Échec du chargement après 3 tentatives")
        print("   Le fichier peut avoir une erreur temporaire persistante")


def example_4_custom_retry_parameters():
    """Exemple 4 : Personnalisation des paramètres de retry."""
    print("\n" + "=" * 70)
    print("EXEMPLE 4 : Paramètres de retry personnalisés")
    print("=" * 70)

    file_path = "exemple.flac"

    print(f"\n📁 Chargement de : {file_path}")
    print("   Paramètres : 5 tentatives, délai initial 0.5s, backoff ×2.0")

    # Retry avec paramètres personnalisés
    audio_data, _sample_rate = load_audio_with_retry(
        file_path,
        max_attempts=5,  # 5 tentatives au lieu de 3
        initial_delay=0.5,  # Délai initial de 0.5s
        backoff_multiplier=2.0,  # Doublement du délai à chaque tentative
    )

    if audio_data is not None:
        print("\n✅ Audio chargé avec succès !")
    else:
        print("\n❌ Échec après 5 tentatives")


def example_5_batch_analysis():
    """Exemple 5 : Analyse en batch avec gestion des erreurs."""
    print("\n" + "=" * 70)
    print("EXEMPLE 5 : Analyse en batch d'un dossier")
    print("=" * 70)

    # Dossier à analyser
    folder = Path(".")
    flac_files = list(folder.glob("*.flac"))

    if not flac_files:
        print(f"\n⚠️  Aucun fichier FLAC trouvé dans : {folder}")
        return

    print(f"\n📁 Analyse de {len(flac_files)} fichiers FLAC...")

    analyzer = FLACAnalyzer()
    results = {"authentic": [], "suspicious": [], "fake": [], "partial": [], "error": []}

    for file_path in flac_files:
        print(f"\n   Analyse : {file_path.name}...", end=" ")

        try:
            result = analyzer.analyze_file(file_path)

            # Classifier le résultat
            if result["verdict"] == "ERROR":
                results["error"].append(file_path.name)
                print("❌ ERREUR")
            elif result.get("partial_analysis", False):
                results["partial"].append(file_path.name)
                print("⚠️  PARTIEL")
            elif result["verdict"] == "AUTHENTIC":
                results["authentic"].append(file_path.name)
                print("✅ AUTHENTIC")
            elif result["verdict"] in ["SUSPICIOUS", "WARNING"]:
                results["suspicious"].append(file_path.name)
                print("⚠️  SUSPECT")
            else:
                results["fake"].append(file_path.name)
                print("❌ FAKE")

        except Exception as e:
            results["error"].append(file_path.name)
            print(f"❌ ERREUR : {e}")

    # Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"✅ Authentiques : {len(results['authentic'])}")
    print(f"⚠️  Suspects : {len(results['suspicious'])}")
    print(f"❌ Fakes : {len(results['fake'])}")
    print(f"⚠️  Analyses partielles : {len(results['partial'])}")
    print(f"❌ Erreurs : {len(results['error'])}")

    if results["partial"]:
        print("\n⚠️  Fichiers avec analyse partielle (R9/R11 ont échoué) :")
        for filename in results["partial"]:
            print(f"   - {filename}")


def main():
    """Menu principal."""
    print("\n" + "=" * 70)
    print("EXEMPLES D'UTILISATION - Système de retry FLAC Detective")
    print("=" * 70)
    print("\nChoisissez un exemple à exécuter :")
    print("  1. Analyse basique avec retry automatique")
    print("  2. Analyse avec logs détaillés (voir le retry en action)")
    print("  3. Utilisation directe de load_audio_with_retry")
    print("  4. Paramètres de retry personnalisés")
    print("  5. Analyse en batch d'un dossier")
    print("  0. Quitter")

    choice = input("\nVotre choix (0-5) : ").strip()

    examples = {
        "1": example_1_basic_analysis,
        "2": example_2_with_debug_logs,
        "3": example_3_direct_audio_loading,
        "4": example_4_custom_retry_parameters,
        "5": example_5_batch_analysis,
    }

    if choice == "0":
        print("\n👋 Au revoir !")
        return

    example_func = examples.get(choice)
    if example_func:
        example_func()
    else:
        print("\n❌ Choix invalide")

    print("\n" + "=" * 70)
    print("Exemple terminé !")
    print("=" * 70)


if __name__ == "__main__":
    main()
