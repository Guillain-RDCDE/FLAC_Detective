# Amélioration de la gestion des erreurs de décodage FLAC

## Résumé des modifications

Ce document décrit les modifications apportées au projet FLAC Detective pour améliorer la gestion des erreurs temporaires de décodage FLAC (notamment "flac decoder lost sync").

## Problème résolu

Certains fichiers FLAC valides généraient des erreurs temporaires "flac decoder lost sync" lors de l'analyse par les Règles 9 et 11, qui utilisent `librosa.load()` ou `soundfile.read()`. Ces erreurs étaient temporaires et le fichier était en réalité valide (score AUTHENTIC, lecture OK après retry), mais il était incorrectement marqué comme CORRUPTED.

## Solution implémentée

### 1. Nouveau module utilitaire : `audio_loader.py`

**Fichier créé :** `src/flac_detective/analysis/new_scoring/audio_loader.py`

Ce module fournit :

- **`is_temporary_decoder_error(error_message: str) -> bool`**
  - Détecte si une erreur est temporaire (lost sync, decoder error, sync error, invalid frame, unexpected end)
  - Insensible à la casse

- **`load_audio_with_retry(file_path, max_attempts=3, initial_delay=0.2, backoff_multiplier=1.5)`**
  - Charge un fichier audio avec mécanisme de retry automatique
  - Maximum 3 tentatives par défaut
  - Délai initial de 0.2s avec exponential backoff (×1.5)
  - Logs détaillés pour chaque tentative
  - Retourne `(None, None)` après échec des 3 tentatives

### 2. Modifications de la Règle 9 (Détection d'artefacts)

**Fichier modifié :** `src/flac_detective/analysis/new_scoring/artifacts.py`

- Import de `load_audio_with_retry`
- Remplacement de `sf.read()` par `load_audio_with_retry()` dans `analyze_compression_artifacts()`
- En cas d'échec après retry : retourne 0 points (pas de pénalité) au lieu de crasher
- Logs explicites : "⚠️ Temporary error on attempt X", "✅ Audio loaded successfully on attempt X", "❌ Failed after 3 attempts"

### 3. Modifications de la Règle 11 (Détection cassette)

**Fichier modifié :** `src/flac_detective/analysis/new_scoring/rules/cassette.py`

- Import de `load_audio_with_retry`
- Remplacement de `sf.read()` par `load_audio_with_retry()` dans `apply_rule_11_cassette_detection()`
- En cas d'échec après retry : retourne 0 points (pas de pénalité)
- Logs explicites similaires à la Règle 9

### 4. Amélioration de la détection CORRUPTED

**Fichier modifié :** `src/flac_detective/analysis/quality.py`

- Import de `load_audio_with_retry` et `is_temporary_decoder_error`
- Modification du `CorruptionDetector` :
  - Utilise `load_audio_with_retry()` au lieu de `sf.read()`
  - Distingue les erreurs temporaires des vraies corruptions
  - Les erreurs temporaires ne marquent PAS le fichier comme corrompu
  - Ajoute un flag `partial_analysis: True` pour indiquer que certaines règles optionnelles ont échoué
  - Les vraies corruptions (NaN, Inf, fichiers illisibles) sont toujours détectées

### 5. Propagation du flag `partial_analysis`

**Fichier modifié :** `src/flac_detective/analysis/analyzer.py`

- Ajout du champ `partial_analysis` dans les résultats d'analyse
- Ce flag indique qu'une analyse partielle a été effectuée (R9/R11 ont échoué mais le fichier n'est pas corrompu)

## Comportement après modifications

### Cas 1 : Fichier avec erreur temporaire (ex: "lost sync")

**Avant :**
- Règle 9 ou 11 échoue
- Fichier marqué CORRUPTED
- Score invalide

**Après :**
1. Premier appel à `load_audio_with_retry()` échoue
2. Log : "⚠️ Temporary error on attempt 1: flac decoder lost sync"
3. Attente de 0.2s
4. Deuxième tentative réussit
5. Log : "✅ Audio loaded successfully on attempt 2"
6. Analyse continue normalement
7. Verdict basé sur toutes les règles (AUTHENTIC si score faible)

### Cas 2 : Échec après 3 tentatives

**Après :**
1. 3 tentatives échouent
2. Log : "❌ Failed after 3 attempts: flac decoder lost sync"
3. Règle 9/11 retourne 0 points (contribution neutre)
4. `CorruptionDetector` ne marque PAS comme corrompu (erreur temporaire)
5. Flag `partial_analysis: True` ajouté aux résultats
6. Verdict basé sur les règles critiques (R1-R8)
7. Fichier marqué CORRUPTED **uniquement** si les règles critiques échouent

### Cas 3 : Vraie corruption (NaN, fichier illisible)

**Après :**
- Détection immédiate de la vraie corruption
- Fichier marqué CORRUPTED
- Pas de retry inutile

## Tests

Un script de test a été créé : `tests/test_audio_loader_retry.py`

Pour l'exécuter :
```bash
python tests/test_audio_loader_retry.py
```

## Exemple de logs

### Succès après retry :
```
DEBUG: Loading audio (attempt 1/3): file.flac
WARNING: ⚠️  Temporary error on attempt 1: flac decoder lost sync
INFO: Retrying in 0.2s...
DEBUG: Loading audio (attempt 2/3): file.flac
INFO: ✅ Audio loaded successfully on attempt 2
INFO: RULE 9: Activation - Analyzing compression artifacts...
```

### Échec après 3 tentatives :
```
DEBUG: Loading audio (attempt 1/3): file.flac
WARNING: ⚠️  Temporary error on attempt 1: flac decoder lost sync
INFO: Retrying in 0.2s...
DEBUG: Loading audio (attempt 2/3): file.flac
WARNING: ⚠️  Temporary error on attempt 2: flac decoder lost sync
INFO: Retrying in 0.3s...
DEBUG: Loading audio (attempt 3/3): file.flac
ERROR: ❌ Failed after 3 attempts: flac decoder lost sync
ERROR: RULE 9: Failed to load audio after retries. Returning 0 points (no penalty for temporary decoder issues).
```

## Contraintes respectées

✅ Signatures des fonctions publiques préservées  
✅ Pas de modification des règles R1-R8 (non concernées)  
✅ Performance : retry uniquement sur erreurs temporaires  
✅ Compatibilité avec le reste du code maintenue  
✅ Logs détaillés pour le débogage  

## Fichiers modifiés

1. **Créé :** `src/flac_detective/analysis/new_scoring/audio_loader.py`
2. **Modifié :** `src/flac_detective/analysis/new_scoring/artifacts.py`
3. **Modifié :** `src/flac_detective/analysis/new_scoring/rules/cassette.py`
4. **Modifié :** `src/flac_detective/analysis/quality.py`
5. **Modifié :** `src/flac_detective/analysis/analyzer.py`
6. **Créé :** `tests/test_audio_loader_retry.py`

## Résultat attendu

Un fichier comme "04 - Bial Hclap; Sagrario - Danza coyote.flac" qui génère "lost sync" devrait maintenant :

✅ Être analysé avec succès après 1 ou 2 retries  
✅ Avoir un verdict AUTHENTIC (si score ≤ 30/100)  
✅ NE PAS être marqué CORRUPTED  
✅ Avoir des logs montrant le retry et le succès  

Si après 3 tentatives l'erreur persiste :

✅ Le fichier garde son verdict basé sur R1-R8  
✅ R9 et R11 contribuent 0 points  
✅ Le fichier n'est marqué CORRUPTED que si les règles critiques ont échoué  
✅ Flag `partial_analysis: True` présent dans les résultats  
