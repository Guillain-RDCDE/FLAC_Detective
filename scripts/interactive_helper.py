#!/usr/bin/env python3
"""
FLAC Detective - Interactive Helper
Guided workflow for analysis and repair
"""

import argparse
import sys
import subprocess
from pathlib import Path

# Add src to path so we can import flac_detective
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))

from flac_detective.utils import LOGO

# Define paths to scripts
SCRIPT_DIR = Path(__file__).parent
ANALYZER_SCRIPT = SCRIPT_DIR / 'run_detective.py'
REPAIR_SCRIPT = SCRIPT_DIR / 'repair_flac.py'

def show_workflow():
    """Affiche le workflow proposé"""
    print("=" * 80)
    print("🔄 WORKFLOW EN 3 ÉTAPES")
    print("=" * 80)
    print()
    
    print("ÉTAPE 1 : ANALYSE COMPLÈTE")
    print("-" * 80)
    print("Lancez d'abord l'analyse complète de votre bibliothèque:")
    print()
    print(f"  python {ANALYZER_SCRIPT.name}")
    print()
    print("Cela génère un rapport Excel avec tous les problèmes détectés,")
    print("incluant les fichiers avec décalage de durée.")
    print()
    
    print("ÉTAPE 2 : IDENTIFIER LES FICHIERS À RÉPARER")
    print("-" * 80)
    print("Ouvrez le rapport Excel et filtrez:")
    print()
    print("  • Colonne 'Problème Durée' ≠ '✓ OK'")
    print("  • OU Score < 90% avec mention de durée incohérente")
    print()
    print("Notez les chemins des fichiers ou dossiers à réparer.")
    print()
    
    print("ÉTAPE 3A : RÉPARATION D'UN FICHIER SPÉCIFIQUE")
    print("-" * 80)
    print("Test d'abord en mode simulation (dry-run):")
    print()
    print(f"  python {REPAIR_SCRIPT.name} 'chemin/vers/fichier.flac' --dry-run")
    print()
    print("Si le résultat semble correct, lancez la réparation réelle:")
    print()
    print(f"  python {REPAIR_SCRIPT.name} 'chemin/vers/fichier.flac'")
    print()
    print("Un backup .bak est créé automatiquement.")
    print()
    
    print("ÉTAPE 3B : RÉPARATION D'UN DOSSIER COMPLET")
    print("-" * 80)
    print("Pour réparer tous les fichiers d'un album ou dossier:")
    print()
    print("  # Simulation")
    print(f"  python {REPAIR_SCRIPT.name} 'chemin/vers/dossier/' --recursive --dry-run")
    print()
    print("  # Réparation réelle")
    print(f"  python {REPAIR_SCRIPT.name} 'chemin/vers/dossier/' --recursive")
    print()
    
    print("ÉTAPE 4 : RÉANALYSE")
    print("-" * 80)
    print("Après réparation, relancez l'analyse pour vérifier:")
    print()
    print("  rm progress.json  # Effacer l'ancienne analyse")
    print(f"  python {ANALYZER_SCRIPT.name}")
    print()
    print("Les fichiers réparés devraient maintenant avoir:")
    print("  • Problème Durée: '✓ OK'")
    print("  • Score potentiellement amélioré")
    print()
    
    print("=" * 80)
    print()


def show_examples():
    """Affiche des exemples concrets"""
    print("=" * 80)
    print("📖 EXEMPLES PRATIQUES")
    print("=" * 80)
    print()
    
    print("EXEMPLE 1 : Fichier unique avec problème de durée")
    print("-" * 80)
    print("Situation : Le rapport Excel montre:")
    print("  • track01.flac - Score 80%")
    print("  • Problème Durée: '⚠️ Décalage: 88,200 samples (2000ms)'")
    print()
    print("Actions:")
    print(f"  1. Test: python {REPAIR_SCRIPT.name} 'track01.flac' --dry-run")
    print(f"  2. Fix:  python {REPAIR_SCRIPT.name} 'track01.flac'")
    print("  3. Vérif: (Re-run analysis)")
    print()
    
    print("EXEMPLE 2 : Album complet avec durées erronées")
    print("-" * 80)
    print("Situation : Tous les fichiers d'un album ont un décalage de 500ms")
    print("(Problème lors du split/rip de l'album)")
    print()
    print("Actions:")
    print(f"  1. Test:  python {REPAIR_SCRIPT.name} 'Album/' --recursive --dry-run")
    print(f"  2. Fix:   python {REPAIR_SCRIPT.name} 'Album/' --recursive")
    print("  3. Check: Vérifier que les .bak ont été créés")
    print("  4. Réanalyse complète")
    print()
    
    print("EXEMPLE 3 : Réparation massive après analyse")
    print("-" * 80)
    print("Situation : L'analyse a détecté 125 fichiers avec problèmes de durée")
    print()
    print("Option A - Réparer dossier par dossier:")
    print("  for dir in 'Artist1/' 'Artist2/' 'Artist3/'; do")
    print(f"    python {REPAIR_SCRIPT.name} \"$dir\" --recursive")
    print("  done")
    print()
    print("Option B - Script bash pour traiter une liste:")
    print("  # Créer liste.txt avec les chemins des fichiers problématiques")
    print("  while read file; do")
    print(f"    python {REPAIR_SCRIPT.name} \"$file\"")
    print("  done < liste.txt")
    print()
    
    print("=" * 80)
    print()


def show_important_notes():
    """Affiche les notes importantes"""
    print("=" * 80)
    print("⚠️  NOTES IMPORTANTES")
    print("=" * 80)
    print()
    
    print("BACKUPS AUTOMATIQUES")
    print("-" * 80)
    print("  • Un fichier .bak est créé AVANT toute modification")
    print("  • Format: fichier.flac.bak")
    print("  • Supprimez-les après vérification pour économiser l'espace")
    print("  • Option --no-backup pour désactiver (non recommandé)")
    print()
    
    print("DÉPENDANCE : OUTIL 'flac'")
    print("-" * 80)
    print("  Le script nécessite l'outil officiel 'flac' installé:")
    print()
    print("  Ubuntu/Debian : sudo apt install flac")
    print("  macOS         : brew install flac")
    print("  Windows       : Télécharger depuis xiph.org")
    print()
    print("  Vérification : flac --version")
    print()
    
    print("PRÉSERVATION DES MÉTADONNÉES")
    print("-" * 80)
    print("  Le script préserve 100% des métadonnées:")
    print("  ✅ Tous les tags Vorbis (artiste, album, titre, etc.)")
    print("  ✅ Tous les artworks (images de pochette)")
    print("  ✅ Commentaires et tags custom")
    print("  ✅ Replay Gain")
    print("  ✅ Vendor string")
    print()
    
    print("QUE SE PASSE-T-IL LORS DE LA RÉPARATION ?")
    print("-" * 80)
    print("  1. Extraction de TOUTES les métadonnées (tags + images)")
    print("  2. Décodage FLAC → WAV (temporaire)")
    print("  3. Re-encodage WAV → FLAC (métadonnées correctes)")
    print("  4. Restauration de toutes les métadonnées")
    print("  5. Vérification que le problème est résolu")
    print("  6. Remplacement du fichier original")
    print()
    
    print("  Le contenu AUDIO reste 100% identique (lossless)")
    print("  Seules les métadonnées du conteneur FLAC sont recalculées")
    print()
    
    print("QUAND RÉPARER ?")
    print("-" * 80)
    print("  ✅ Décalage > 1 seconde : RECOMMANDÉ")
    print("     (Corruption potentielle ou transcodage raté)")
    print()
    print("  ⚠️  Décalage 100-1000ms : AU CAS PAR CAS")
    print("     (Métadonnées éditées, mais fichier OK)")
    print()
    print("  ✅ Décalage < 100ms : PAS NÉCESSAIRE")
    print("     (Tolérance normale, arrondi)")
    print()
    
    print("=" * 80)
    print()


def show_menu():
    """Affiche le menu interactif"""
    while True:
        print(LOGO)
        print("\n╔═══════════════════════════════════════════════════════════════════════╗")
        print("║                        MENU PRINCIPAL                                 ║")
        print("╚═══════════════════════════════════════════════════════════════════════╝\n")
        print("  1. 📖 Voir le workflow complet (3 étapes)")
        print("  2. 💡 Voir des exemples pratiques")
        print("  3. ⚠️  Lire les notes importantes")
        print("  4. 🔧 Lancer l'analyse complète")
        print("  5. 🛠️  Réparer un fichier spécifique")
        print("  6. 📁 Réparer un dossier")
        print("  0. ❌ Quitter")
        print()
        
        choice = input("Votre choix: ").strip()
        
        if choice == '1':
            show_workflow()
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == '2':
            show_examples()
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == '3':
            show_important_notes()
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == '4':
            print("\n🔄 Lancement de l'analyse complète...")
            print(f"Commande: python {ANALYZER_SCRIPT.name}")
            print()
            run = input("Lancer maintenant ? (o/n): ").strip().lower()
            if run == 'o':
                subprocess.run([sys.executable, str(ANALYZER_SCRIPT)])
        
        elif choice == '5':
            print("\n🛠️  RÉPARATION D'UN FICHIER")
            print("-" * 80)
            filepath = input("Chemin du fichier .flac: ").strip().strip('"\'')
            
            if not Path(filepath).exists():
                print(f"❌ Fichier introuvable: {filepath}")
                continue
            
            print("\nMode:")
            print("  1. Simulation (dry-run)")
            print("  2. Réparation réelle")
            mode = input("Choix (1/2): ").strip()
            
            if mode == '1':
                cmd = [sys.executable, str(REPAIR_SCRIPT), filepath, '--dry-run']
            elif mode == '2':
                cmd = [sys.executable, str(REPAIR_SCRIPT), filepath]
            else:
                print("❌ Choix invalide")
                continue
            
            print(f"\n🔄 Commande: {' '.join(cmd)}")
            subprocess.run(cmd)
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == '6':
            print("\n📁 RÉPARATION D'UN DOSSIER")
            print("-" * 80)
            dirpath = input("Chemin du dossier: ").strip().strip('"\'')
            
            if not Path(dirpath).exists():
                print(f"❌ Dossier introuvable: {dirpath}")
                continue
            
            recursive = input("Parcourir les sous-dossiers ? (o/n): ").strip().lower()
            
            print("\nMode:")
            print("  1. Simulation (dry-run)")
            print("  2. Réparation réelle")
            mode = input("Choix (1/2): ").strip()
            
            cmd = [sys.executable, str(REPAIR_SCRIPT), dirpath]
            
            if recursive == 'o':
                cmd.append('--recursive')
            
            if mode == '1':
                cmd.append('--dry-run')
            elif mode != '2':
                print("❌ Choix invalide")
                continue
            
            print(f"\n🔄 Commande: {' '.join(cmd)}")
            subprocess.run(cmd)
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == '0':
            print("\n👋 Au revoir !\n")
            break
        
        else:
            print("\n❌ Choix invalide\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Assistant pour analyse et réparation FLAC')
    parser.add_argument('--workflow', action='store_true', help='Afficher le workflow')
    parser.add_argument('--examples', action='store_true', help='Afficher des exemples')
    parser.add_argument('--notes', action='store_true', help='Afficher les notes importantes')
    
    args = parser.parse_args()
    
    if args.workflow:
        show_workflow()
    elif args.examples:
        show_examples()
    elif args.notes:
        show_important_notes()
    else:
        # Menu interactif
        show_menu()
