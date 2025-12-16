"""Script de test pour diagnostiquer le problème avec Banda lobourou.flac"""

import sys
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flac_detective.analysis.new_scoring.audio_loader import sf_blocks_partial, load_audio_with_retry
from flac_detective.analysis.audio_cache import AudioCache
from flac_detective.analysis.analyzer import FLACAnalyzer
import logging

# Configuration du logging pour voir tous les détails
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Fichier problématique
file_path = Path(r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac")

print("=" * 80)
print("TEST 1: Tentative de lecture complète avec load_audio_with_retry()")
print("=" * 80)
audio_data, sr = load_audio_with_retry(str(file_path))
print(f"Résultat: audio_data={'NONE' if audio_data is None else f'{len(audio_data)} samples'}, sr={sr}")
print()

print("=" * 80)
print("TEST 2: Tentative de lecture partielle avec sf_blocks_partial()")
print("=" * 80)
audio_data, sr, is_complete = sf_blocks_partial(str(file_path))
print(f"Résultat: audio_data={'NONE' if audio_data is None else f'{len(audio_data)} samples'}, sr={sr}, is_complete={is_complete}")
print()

print("=" * 80)
print("TEST 3: Tentative de création d'AudioCache")
print("=" * 80)
try:
    cache = AudioCache(file_path)
    print(f"✅ AudioCache créé avec succès!")
    print(f"   Audio: {len(cache._audio)} samples")
    print(f"   Sample rate: {cache._sample_rate}")
except Exception as e:
    print(f"❌ AudioCache a échoué: {e}")
    print()
    print("=" * 80)
    print("TEST 3b: Création manuelle de cache partiel")
    print("=" * 80)
    audio_data, sr, is_complete = sf_blocks_partial(str(file_path))
    if audio_data is not None:
        cache = AudioCache.__new__(AudioCache)
        cache.filepath = file_path
        cache._audio = audio_data
        cache._sample_rate = sr
        print(f"✅ Cache partiel créé manuellement!")
        print(f"   Audio: {len(cache._audio)} samples")
        print(f"   Sample rate: {cache._sample_rate}")
        print(f"   Complet: {is_complete}")
    else:
        print(f"❌ Impossible de créer un cache partiel")
        cache = None
print()

print("=" * 80)
print("TEST 4: Analyse complète avec FLACAnalyzer")
print("=" * 80)
analyzer = FLACAnalyzer()
result = analyzer.analyze_file(file_path)
print(f"Verdict: {result['verdict']}")
print(f"Score: {result['score']}")
print(f"Raison: {result['reason']}")
print(f"Cutoff: {result['cutoff_freq']}")
print(f"Is corrupted: {result['is_corrupted']}")
print(f"Partial analysis: {result.get('is_partial_analysis', 'N/A')}")
print(f"Corruption error: {result.get('corruption_error', 'N/A')}")
print()

print("=" * 80)
print("RÉSUMÉ")
print("=" * 80)
if result['verdict'] == 'ERROR':
    print("❌ ÉCHEC: Le fichier est toujours marqué comme ERROR/CORRUPT")
elif result['verdict'] in ['FAKE_CERTAIN', 'SUSPICIOUS']:
    print("✅ SUCCÈS: Le fichier est correctement détecté comme FAKE/SUSPICIOUS")
    if result.get('is_partial_analysis'):
        print("✅ BONUS: L'analyse partielle est active")
else:
    print(f"⚠️  INATTENDU: Verdict = {result['verdict']}")
