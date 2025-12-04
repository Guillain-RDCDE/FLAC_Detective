#!/usr/bin/env python3
"""
WAV to FLAC Converter - Simple batch converter
Converts all WAV files in a directory to FLAC format
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Logo simple
LOGO = r"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              🎵 WAV → FLAC Converter 🎵                   ║
║                                                           ║
║          Simple batch converter using official           ║
║                    FLAC encoder                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""

def check_flac_installed():
    """Vérifie que l'outil flac est installé"""
    try:
        result = subprocess.run(['flac', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print(f"✅ {version}\n")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("❌ ERREUR: L'outil 'flac' n'est pas installé !\n")
    print("Installation:")
    print("  • Linux/Ubuntu: sudo apt install flac")
    print("  • macOS:        brew install flac")
    print("  • Windows:      Télécharger depuis https://xiph.org/flac/download.html\n")
    return False

def find_wav_files(directory, recursive=False):
    """Trouve tous les fichiers WAV dans le répertoire"""
    wav_files = []
    
    if recursive:
        # Recherche récursive
        for wav_file in Path(directory).rglob('*.wav'):
            wav_files.append(wav_file)
        for wav_file in Path(directory).rglob('*.WAV'):
            wav_files.append(wav_file)
    else:
        # Recherche non récursive
        for wav_file in Path(directory).glob('*.wav'):
            wav_files.append(wav_file)
        for wav_file in Path(directory).glob('*.WAV'):
            wav_files.append(wav_file)
    
    return sorted(wav_files)

def convert_wav_to_flac(wav_file, compression_level=5, verify=True, delete_wav=False):
    """
    Convertit un fichier WAV en FLAC
    
    Args:
        wav_file: Chemin du fichier WAV
        compression_level: Niveau de compression (0-8, défaut: 5)
        verify: Vérifier l'intégrité après conversion
        delete_wav: Supprimer le WAV après conversion réussie
    
    Returns:
        (success, flac_file, message)
    """
    wav_path = Path(wav_file)
    flac_path = wav_path.with_suffix('.flac')
    
    # Si le FLAC existe déjà
    if flac_path.exists():
        return False, None, "FLAC existe déjà"
    
    # Construction de la commande
    cmd = [
        'flac',
        f'-{compression_level}',  # Niveau de compression
        '--silent',                # Mode silencieux
    ]
    
    if verify:
        cmd.append('--verify')     # Vérification intégrité
    
    cmd.extend([
        '--output-name', str(flac_path),
        str(wav_path)
    ])
    
    try:
        # Exécution de la conversion
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True, 
                              timeout=300)
        
        if result.returncode == 0 and flac_path.exists():
            # Conversion réussie
            
            # Supprimer le WAV si demandé
            if delete_wav:
                wav_path.unlink()
                return True, flac_path, "Converti + WAV supprimé"
            else:
                return True, flac_path, "Converti"
        else:
            error_msg = result.stderr.strip() if result.stderr else "Erreur inconnue"
            return False, None, f"Erreur: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, None, "Timeout (>5min)"
    except Exception as e:
        return False, None, f"Exception: {str(e)}"

def format_size(size_bytes):
    """Formate la taille en octets en format lisible"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def main():
    """Fonction principale"""
    import argparse
    
    print(LOGO)
    
    parser = argparse.ArgumentParser(
        description='Convertit tous les fichiers WAV d\'un répertoire en FLAC',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Convertir tous les WAV du dossier actuel
  python3 wav_to_flac.py .
  
  # Convertir avec recherche récursive
  python3 wav_to_flac.py /path/to/music --recursive
  
  # Compression maximale avec suppression des WAV
  python3 wav_to_flac.py /path/to/music --level 8 --delete-wav
  
  # Sans vérification (plus rapide)
  python3 wav_to_flac.py /path/to/music --no-verify

Niveaux de compression:
  0 = Rapide, fichiers plus gros
  5 = Équilibré (défaut)
  8 = Lent, fichiers plus petits
        """
    )
    
    parser.add_argument('directory',
                       help='Répertoire contenant les fichiers WAV')
    
    parser.add_argument('-r', '--recursive',
                       action='store_true',
                       help='Rechercher dans les sous-dossiers')
    
    parser.add_argument('-l', '--level',
                       type=int,
                       choices=range(0, 9),
                       default=5,
                       help='Niveau de compression (0-8, défaut: 5)')
    
    parser.add_argument('--no-verify',
                       action='store_true',
                       help='Ne pas vérifier l\'intégrité après conversion')
    
    parser.add_argument('--delete-wav',
                       action='store_true',
                       help='Supprimer les fichiers WAV après conversion réussie')
    
    args = parser.parse_args()
    
    # Vérification de l'outil flac
    if not check_flac_installed():
        sys.exit(1)
    
    # Vérification du répertoire
    directory = Path(args.directory)
    if not directory.exists():
        print(f"❌ ERREUR: Le répertoire '{directory}' n'existe pas !\n")
        sys.exit(1)
    
    if not directory.is_dir():
        print(f"❌ ERREUR: '{directory}' n'est pas un répertoire !\n")
        sys.exit(1)
    
    # Recherche des fichiers WAV
    print(f"🔍 Recherche des fichiers WAV dans: {directory}")
    if args.recursive:
        print("   Mode récursif activé")
    print()
    
    wav_files = find_wav_files(directory, args.recursive)
    
    if not wav_files:
        print("❌ Aucun fichier WAV trouvé !\n")
        sys.exit(0)
    
    print(f"✅ {len(wav_files)} fichier(s) WAV trouvé(s)\n")
    
    # Confirmation si suppression WAV activée
    if args.delete_wav:
        print("⚠️  ATTENTION: Les fichiers WAV seront SUPPRIMÉS après conversion !")
        response = input("   Continuer ? (oui/non): ").strip().lower()
        if response not in ['oui', 'o', 'yes', 'y']:
            print("\n❌ Conversion annulée.\n")
            sys.exit(0)
        print()
    
    # Affichage des paramètres
    print("📋 Paramètres de conversion:")
    print(f"   • Niveau compression: {args.level}")
    print(f"   • Vérification intégrité: {'Oui' if not args.no_verify else 'Non'}")
    print(f"   • Supprimer WAV: {'Oui' if args.delete_wav else 'Non'}")
    print()
    
    # Conversion
    print("=" * 80)
    print("🔄 DÉBUT DE LA CONVERSION")
    print("=" * 80)
    print()
    
    converted = 0
    skipped = 0
    errors = 0
    
    total_wav_size = 0
    total_flac_size = 0
    
    start_time = datetime.now()
    
    for i, wav_file in enumerate(wav_files, 1):
        # Taille du WAV
        wav_size = wav_file.stat().st_size
        total_wav_size += wav_size
        
        # Affichage progression
        print(f"[{i}/{len(wav_files)}] {wav_file.name}")
        print(f"        Taille WAV: {format_size(wav_size)}")
        
        # Conversion
        success, flac_file, message = convert_wav_to_flac(
            wav_file,
            compression_level=args.level,
            verify=not args.no_verify,
            delete_wav=args.delete_wav
        )
        
        if success:
            # Taille du FLAC
            flac_size = flac_file.stat().st_size
            total_flac_size += flac_size
            ratio = (flac_size / wav_size) * 100 if wav_size > 0 else 0
            
            print(f"        ✅ {message}")
            print(f"        Taille FLAC: {format_size(flac_size)} ({ratio:.1f}% du WAV)")
            converted += 1
        elif "existe déjà" in message:
            print(f"        ⏭️  {message}")
            skipped += 1
        else:
            print(f"        ❌ {message}")
            errors += 1
        
        print()
    
    # Statistiques finales
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("=" * 80)
    print("✅ CONVERSION TERMINÉE")
    print("=" * 80)
    print()
    print(f"📊 Statistiques:")
    print(f"   • Fichiers convertis: {converted}")
    print(f"   • Fichiers ignorés: {skipped}")
    print(f"   • Erreurs: {errors}")
    print(f"   • Temps total: {duration:.1f} secondes")
    
    if converted > 0:
        print()
        print(f"💾 Taille totale:")
        print(f"   • WAV:  {format_size(total_wav_size)}")
        print(f"   • FLAC: {format_size(total_flac_size)}")
        
        if total_wav_size > 0:
            ratio = (total_flac_size / total_wav_size) * 100
            saved = total_wav_size - total_flac_size
            print(f"   • Ratio: {ratio:.1f}%")
            print(f"   • Économie: {format_size(saved)} ({100-ratio:.1f}%)")
        
        avg_time = duration / converted
        print()
        print(f"⚡ Temps moyen par fichier: {avg_time:.1f}s")
    
    print()

if __name__ == '__main__':
    main()
