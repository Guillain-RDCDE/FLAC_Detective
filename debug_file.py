"""Script de diagnostic pour analyser un fichier FLAC specifique."""

import logging
import sys
from pathlib import Path

# Configure UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configure logging pour voir tous les details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import de l'analyseur
from src.flac_detective.analysis.analyzer import FLACAnalyzer

def main():
    # Fichier a analyser
    filepath = Path(r"E:\FLAC\External\Habibi Funk\HABIBI006 - Al Massrieen - Modern music (2017)\04 - Al Massrieen -  Longa 79.flac")
    
    if not filepath.exists():
        print(f"[X] Fichier introuvable: {filepath}")
        return
    
    print("=" * 80)
    print("[ANALYSE DETAILLEE DU FICHIER]")
    print("=" * 80)
    print(f"Fichier: {filepath.name}")
    print(f"Chemin: {filepath}")
    print("=" * 80)
    print()
    
    # Creer l'analyseur
    analyzer = FLACAnalyzer(sample_duration=30.0)
    
    # Analyser le fichier
    print("[ANALYSE] Lancement de l'analyse...\n")
    result = analyzer.analyze_file(filepath)
    
    # Afficher les resultats detailles
    print("\n" + "=" * 80)
    print("[RESULTATS DE L'ANALYSE]")
    print("=" * 80)
    
    print(f"\n[SCORE]: {result['score']}%")
    print(f"[RAISON]: {result['reason']}")
    
    print(f"\n[ANALYSE SPECTRALE]:")
    print(f"  - Frequence de coupure detectee: {result['cutoff_freq']:.0f} Hz")
    print(f"  - Taux d'echantillonnage: {result['sample_rate']} Hz")
    print(f"  - Profondeur de bits: {result['bit_depth']} bits")
    print(f"  - Encodeur: {result['encoder']}")
    
    print(f"\n[VERIFICATION DE DUREE]:")
    print(f"  - Incoherence detectee: {result['duration_mismatch']}")
    print(f"  - Duree (metadata): {result['duration_metadata']}")
    print(f"  - Duree (reelle): {result['duration_real']}")
    print(f"  - Difference: {result['duration_diff']} samples")
    
    print(f"\n[QUALITE AUDIO - Phase 1]:")
    print(f"  - Clipping detecte: {result['has_clipping']}")
    if result['has_clipping']:
        print(f"    -> Severite: {result['clipping_severity']}")
        print(f"    -> Pourcentage: {result['clipping_percentage']:.4f}%")
    
    print(f"  - DC Offset detecte: {result['has_dc_offset']}")
    if result['has_dc_offset']:
        print(f"    -> Severite: {result['dc_offset_severity']}")
        print(f"    -> Valeur: {result['dc_offset_value']:.6f}")
    
    print(f"  - Fichier corrompu: {result['is_corrupted']}")
    if result['is_corrupted']:
        print(f"    -> Erreur: {result['corruption_error']}")
    
    print(f"\n[QUALITE AUDIO - Phase 2]:")
    print(f"  - Probleme de silence: {result['has_silence_issue']}")
    if result['has_silence_issue']:
        print(f"    -> Type: {result['silence_issue_type']}")
    
    print(f"  - Fausse haute resolution: {result['is_fake_high_res']}")
    if result['is_fake_high_res']:
        print(f"    -> Profondeur estimee: {result['estimated_bit_depth']} bits")
    
    print(f"  - Upsampling detecte: {result['is_upsampled']}")
    if result['is_upsampled']:
        print(f"    -> Taux original suspecte: {result['suspected_original_rate']} Hz")
    
    print("\n" + "=" * 80)
    print("[ANALYSE TERMINEE]")
    print("=" * 80)
    
    # Analyse detaillee du score
    print("\n" + "=" * 80)
    print("[DECOMPOSITION DU SCORE]")
    print("=" * 80)
    
    score = 100
    print(f"Score initial: {score}%")
    
    # Analyser les penalites basees sur la raison
    reasons = result['reason'].split(' | ')
    for reason in reasons:
        print(f"\n[*] {reason}")
        
        # Identifier les penalites
        if "Cutoff at" in reason:
            cutoff = result['cutoff_freq']
            if cutoff >= 21000:
                penalty = 0
            elif cutoff >= 19500:
                penalty = 40
            elif cutoff >= 19000:
                penalty = 50
            elif cutoff >= 18000:
                penalty = 65
            elif cutoff >= 16000:
                penalty = 80
            else:
                penalty = 95
            
            if penalty > 0:
                score -= penalty
                print(f"   -> Penalite: -{penalty}% (score: {score}%)")
        
        elif "energy" in reason.lower():
            # Penalite pour energie faible
            if "No energy" in reason:
                score -= 25
                print(f"   -> Penalite: -25% (score: {score}%)")
            elif "Very low energy" in reason:
                score -= 15
                print(f"   -> Penalite: -15% (score: {score}%)")
            elif "Low energy" in reason:
                score -= 5
                print(f"   -> Penalite: -5% (score: {score}%)")
            elif "Minimal ultra-high content" in reason:
                score -= 5
                print(f"   -> Penalite: -5% (score: {score}%)")
        
        elif "duration" in reason.lower():
            if "Inconsistent duration" in reason:
                score -= 20
                print(f"   -> Penalite: -20% (score: {score}%)")
            elif "Slight duration mismatch" in reason:
                score -= 10
                print(f"   -> Penalite: -10% (score: {score}%)")
        
        elif "encoder" in reason.lower():
            score -= 30
            print(f"   -> Penalite: -30% (score: {score}%)")
        
        elif "bit depth" in reason.lower():
            score -= 20
            print(f"   -> Penalite: -20% (score: {score}%)")
    
    print(f"\n[SCORE FINAL] Calcule: {max(0, min(100, score))}%")
    print(f"[SCORE FINAL] Retourne: {result['score']}%")
    
    if score != result['score']:
        print("\n[ATTENTION] Difference entre le score calcule et le score retourne!")

if __name__ == "__main__":
    main()
