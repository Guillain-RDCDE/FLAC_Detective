# Guide d'utilisation - Gestion améliorée des erreurs de décodage FLAC

## Vue d'ensemble

FLAC Detective intègre maintenant un système de retry automatique pour gérer les erreurs temporaires de décodage FLAC (comme "flac decoder lost sync"). Cette amélioration permet d'analyser correctement des fichiers FLAC valides qui génèrent occasionnellement des erreurs de synchronisation.

## Fonctionnement automatique

Le système de retry est **entièrement automatique** et transparent pour l'utilisateur. Aucune configuration n'est nécessaire.

### Comportement par défaut

Lorsqu'une erreur temporaire est détectée lors du chargement d'un fichier audio :

1. **Première tentative** : Chargement normal du fichier
2. **Si échec avec erreur temporaire** : Attente de 0.2s puis nouvelle tentative
3. **Deuxième tentative** : Attente de 0.3s si échec (backoff exponentiel ×1.5)
4. **Troisième tentative** : Dernière tentative
5. **Si échec final** : Le fichier n'est PAS marqué comme corrompu, mais les règles concernées (R9, R11) contribuent 0 points

### Erreurs temporaires détectées

Le système reconnaît automatiquement les erreurs suivantes comme temporaires :
- `lost sync`
- `decoder error`
- `sync error`
- `invalid frame`
- `unexpected end`

Ces erreurs déclenchent le mécanisme de retry. Les autres erreurs (fichier introuvable, permissions, etc.) ne déclenchent pas de retry.

## Logs et débogage

### Logs en mode normal

Lors d'une analyse réussie après retry, vous verrez dans les logs :

```
⚠️  Temporary error on attempt 1: flac decoder lost sync
Retrying in 0.2s...
✅ Audio loaded successfully on attempt 2
```

### Logs en cas d'échec après 3 tentatives

```
⚠️  Temporary error on attempt 1: flac decoder lost sync
Retrying in 0.2s...
⚠️  Temporary error on attempt 2: flac decoder lost sync
Retrying in 0.3s...
❌ Failed after 3 attempts: flac decoder lost sync
RULE 9: Failed to load audio after retries. Returning 0 points (no penalty for temporary decoder issues).
```

### Activer les logs détaillés

Pour voir tous les détails du processus de retry, activez le niveau de log DEBUG :

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Ou en ligne de commande :

```bash
python -m flac_detective --log-level DEBUG [autres options]
```

## Impact sur les résultats d'analyse

### Fichier avec erreur temporaire résolue par retry

- ✅ Analyse complète effectuée
- ✅ Score calculé normalement
- ✅ Verdict basé sur toutes les règles (R1-R11)
- ✅ Pas de flag `partial_analysis`

### Fichier avec erreur temporaire persistante (3 échecs)

- ⚠️ Analyse partielle effectuée
- ⚠️ Règles R9 et R11 contribuent 0 points
- ⚠️ Verdict basé sur R1-R8 uniquement
- ⚠️ Flag `partial_analysis: True` dans les résultats
- ✅ **Fichier NON marqué comme CORRUPTED** (sauf si R1-R8 détectent une vraie corruption)

### Fichier réellement corrompu

- ❌ Détection immédiate de la corruption
- ❌ Fichier marqué CORRUPTED
- ❌ Analyse arrêtée

## Exemples d'utilisation

### Exemple 1 : Analyse d'un fichier avec erreur temporaire

```python
from pathlib import Path
from flac_detective.analysis.analyzer import FLACAnalyzer

analyzer = FLACAnalyzer()
result = analyzer.analyze_file(Path("fichier_avec_lost_sync.flac"))

print(f"Verdict: {result['verdict']}")
print(f"Score: {result['score']}")
print(f"Analyse partielle: {result.get('partial_analysis', False)}")
```

**Résultat attendu :**
```
Verdict: AUTHENTIC
Score: 30
Analyse partielle: False  # Si le retry a réussi
```

### Exemple 2 : Vérifier si une analyse est partielle

```python
if result.get('partial_analysis', False):
    print("⚠️ Attention : Analyse partielle (R9/R11 ont échoué)")
    print(f"Raison : {result.get('corruption_error', 'N/A')}")
else:
    print("✅ Analyse complète effectuée")
```

### Exemple 3 : Utilisation directe de load_audio_with_retry

Si vous développez de nouvelles fonctionnalités nécessitant le chargement audio :

```python
from flac_detective.analysis.new_scoring.audio_loader import load_audio_with_retry

# Chargement avec retry automatique
audio_data, sample_rate = load_audio_with_retry("fichier.flac")

if audio_data is not None:
    # Traitement de l'audio
    print(f"Audio chargé : {audio_data.shape} @ {sample_rate} Hz")
else:
    # Échec après 3 tentatives
    print("Impossible de charger le fichier après 3 tentatives")
```

### Exemple 4 : Personnaliser les paramètres de retry

```python
from flac_detective.analysis.new_scoring.audio_loader import load_audio_with_retry

# Retry avec paramètres personnalisés
audio_data, sample_rate = load_audio_with_retry(
    "fichier.flac",
    max_attempts=5,           # 5 tentatives au lieu de 3
    initial_delay=0.5,        # Délai initial de 0.5s
    backoff_multiplier=2.0    # Doublement du délai à chaque tentative
)
```

## Performances

### Impact sur le temps d'analyse

- **Fichier sans erreur** : Aucun impact (pas de retry)
- **Fichier avec erreur temporaire résolue** : +0.2s à +1s selon le nombre de tentatives
- **Fichier avec erreur persistante** : +1s maximum (3 tentatives avec backoff)

### Optimisations

Le système de retry est optimisé pour :
- Ne pas ralentir l'analyse des fichiers normaux
- Détecter rapidement les vraies corruptions (pas de retry)
- Minimiser les délais avec un backoff exponentiel intelligent

## Questions fréquentes

### Q : Pourquoi 3 tentatives ?

**R :** Les tests montrent que la plupart des erreurs temporaires sont résolues en 1-2 tentatives. 3 tentatives offrent un bon équilibre entre robustesse et performance.

### Q : Puis-je désactiver le retry ?

**R :** Non, le retry est intégré au système. Cependant, il n'est activé que sur les erreurs temporaires et n'impacte pas les performances normales.

### Q : Un fichier avec `partial_analysis: True` est-il fiable ?

**R :** Oui, si le verdict est basé sur les règles critiques (R1-R8). Seules les règles optionnelles (R9, R11) ont échoué. Le fichier n'est pas corrompu, mais l'analyse est moins complète.

### Q : Comment distinguer une erreur temporaire d'une vraie corruption ?

**R :** Le système le fait automatiquement. Les erreurs temporaires (lost sync, etc.) déclenchent le retry. Les vraies corruptions (NaN, Inf, fichier illisible) sont détectées immédiatement sans retry.

### Q : Le retry fonctionne-t-il avec librosa ?

**R :** Non, le système utilise `soundfile` qui est plus fiable. Si vous utilisez `librosa.load()` directement, remplacez-le par `load_audio_with_retry()`.

## Support et contribution

Pour signaler un problème ou suggérer une amélioration :
1. Vérifiez les logs en mode DEBUG
2. Notez le message d'erreur exact
3. Ouvrez une issue sur GitHub avec les détails

## Références

- Documentation complète : `docs/FLAC_DECODER_ERROR_HANDLING.md`
- Tests : `tests/test_audio_loader_retry.py`
- Code source : `src/flac_detective/analysis/new_scoring/audio_loader.py`
