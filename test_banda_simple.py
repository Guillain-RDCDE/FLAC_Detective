"""Simple test for Banda lobourou.flac - No emojis"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flac_detective.analysis.analyzer import FLACAnalyzer

# Fichier problématique
file_path = Path(r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac")

print("=" * 80)
print("ANALYSE COMPLETE DU FICHIER")
print("=" * 80)

analyzer = FLACAnalyzer()
result = analyzer.analyze_file(file_path)

print(f"Verdict: {result['verdict']}")
print(f"Score: {result['score']}")
print(f"Raison: {result['reason']}")
print(f"Cutoff: {result['cutoff_freq']} Hz")
print(f"Is corrupted: {result['is_corrupted']}")
print(f"Partial analysis: {result.get('is_partial_analysis', 'N/A')}")
print(f"Corruption error: {result.get('corruption_error', 'N/A')}")
print()

print("=" * 80)
print("RESULTAT")
print("=" * 80)
if result['verdict'] == 'ERROR':
    print("ECHEC: Le fichier est toujours marque comme ERROR/CORRUPT")
elif result['verdict'] in ['FAKE_CERTAIN', 'SUSPICIOUS']:
    print("SUCCES: Le fichier est correctement detecte comme FAKE/SUSPICIOUS")
    if result.get('is_partial_analysis'):
        print("BONUS: L'analyse partielle est active")
else:
    print(f"INATTENDU: Verdict = {result['verdict']}")
