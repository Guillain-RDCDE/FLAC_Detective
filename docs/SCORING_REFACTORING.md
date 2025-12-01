# Refactorisation du Système de Scoring

## Vue d'ensemble

Ce document décrit la refactorisation effectuée sur le module `new_scoring.py` pour améliorer sa maintenabilité, sa lisibilité et sa testabilité.

## Objectifs de la refactorisation

1. **Modularité** : Décomposer la fonction principale en sous-fonctions spécialisées
2. **Lisibilité** : Améliorer la documentation et la clarté du code
3. **Maintenabilité** : Faciliter les modifications futures
4. **Testabilité** : Rendre le code plus facile à tester unitairement

## Changements principaux

### 1. Introduction de structures de données typées

**Avant** : Les données étaient manipulées comme des dictionnaires et des variables locales dispersées.

**Après** : Utilisation de `NamedTuple` pour structurer les données :

```python
class BitrateMetrics(NamedTuple):
    """Container for bitrate-related metrics."""
    real_bitrate: float
    apparent_bitrate: int
    minimum_expected_bitrate: int
    variance: float

class AudioMetadata(NamedTuple):
    """Container for parsed audio metadata."""
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float
```

**Avantages** :
- Type safety améliorée
- Auto-complétion dans les IDE
- Code plus explicite et auto-documenté
- Immutabilité garantie

### 2. Extraction de fonctions spécialisées

#### a) Parsing des métadonnées

**Nouvelle fonction** : `_parse_metadata(metadata: Dict) -> AudioMetadata`

- Centralise la validation et la conversion des métadonnées
- Gère les cas d'erreur de manière cohérente
- Ajoute des logs d'avertissement pour les valeurs invalides

#### b) Calcul des métriques de bitrate

**Nouvelle fonction** : `_calculate_bitrate_metrics(filepath: Path, audio_meta: AudioMetadata) -> BitrateMetrics`

- Regroupe tous les calculs de bitrate en un seul endroit
- Retourne une structure de données typée
- Facilite le debugging avec des logs détaillés

#### c) Application des règles de scoring

**Nouvelle fonction** : `_apply_scoring_rules(cutoff_freq: float, audio_meta: AudioMetadata, bitrate_metrics: BitrateMetrics) -> Tuple[int, List[str]]`

- Applique les 6 règles de manière structurée
- Agrège les scores et les raisons
- Garantit que le score final est non-négatif

### 3. Amélioration de la documentation

Chaque règle de scoring a maintenant une documentation détaillée :

```python
def _apply_rule_1_mp3_bitrate(real_bitrate: float) -> Tuple[int, List[str]]:
    """Apply Rule 1: Constant MP3 Bitrate Detection.
    
    Detects if the file's real bitrate matches a standard MP3 bitrate (96, 128, 160,
    192, 224, 256, 320 kbps). This is a strong indicator of a transcoded file.
    
    Scoring:
        +50 points if bitrate matches any standard MP3 bitrate (within tolerance)
    
    Args:
        real_bitrate: Actual file bitrate in kbps
        
    Returns:
        Tuple of (score_delta, list_of_reasons)
    """
```

**Avantages** :
- Explication claire de ce que chaque règle détecte
- Documentation du système de scoring
- Facilite la compréhension pour les nouveaux contributeurs

### 4. Ajout de constantes nommées

**Avant** : Valeurs magiques dispersées dans le code (ex: `400`, `500`, `1000`)

**Après** : Constantes nommées et documentées

```python
# Default number of segments for variance calculation
DEFAULT_VARIANCE_SEGMENTS = 10

# Minimum segments for variance calculation
MIN_VARIANCE_SEGMENTS = 1
```

Dans les fonctions de règles :
```python
# Low real bitrate threshold
LOW_BITRATE_THRESHOLD = 400

# Minimum expected bitrate for 24-bit files
MIN_24BIT_BITRATE = 500
```

**Avantages** :
- Code auto-documenté
- Facilite les ajustements futurs
- Évite les erreurs de frappe

### 5. Amélioration de la clarté des conditions

**Avant** :
```python
if real_bitrate < 400 and apparent_bitrate > minimum_expected_bitrate:
```

**Après** :
```python
is_real_too_low = real_bitrate < LOW_BITRATE_THRESHOLD
is_apparent_high = apparent_bitrate > minimum_expected_bitrate

if is_real_too_low and is_apparent_high:
```

**Avantages** :
- Conditions plus lisibles
- Intention du code plus claire
- Facilite le debugging

### 6. Amélioration des logs

**Avant** :
```python
logger.debug(f"RULE 1: +50 points (bitrate = {mp3_bitrate} kbps)")
```

**Après** :
```python
logger.debug(
    f"RULE 1: +50 points (bitrate {real_bitrate:.1f} ≈ {mp3_bitrate} kbps)"
)
```

**Avantages** :
- Logs plus informatifs
- Facilite le debugging
- Meilleure traçabilité des décisions

### 7. Documentation de la fonction de variance

Ajout d'une note importante sur les limitations de l'implémentation actuelle :

```python
"""
Note: This is an approximation. Since FLAC uses variable-length encoding, we cannot
accurately determine segment boundaries without decoding the entire file. This method
assumes uniform distribution of data across the file, which is good enough for
detecting constant vs variable bitrate patterns.
"""
```

**Avantages** :
- Transparence sur les limitations
- Guide pour les améliorations futures
- Évite les malentendus

## Structure finale de `new_calculate_score()`

La fonction principale est maintenant beaucoup plus simple et lisible :

```python
def new_calculate_score(
    cutoff_freq: float,
    metadata: Dict,
    duration_check: Dict,
    filepath: Path
) -> Tuple[int, str, str, str]:
    # Parse and validate metadata
    audio_meta = _parse_metadata(metadata)
    
    # Calculate all bitrate metrics
    bitrate_metrics = _calculate_bitrate_metrics(filepath, audio_meta)
    
    # Apply scoring rules
    score, reasons = _apply_scoring_rules(cutoff_freq, audio_meta, bitrate_metrics)
    
    # Determine verdict and confidence
    verdict, confidence = _determine_verdict(score)
    
    # Format reasons for output
    reasons_str = " | ".join(reasons) if reasons else "No anomaly detected"
    
    logger.info(
        f"Final score: {score}/100 - Verdict: {verdict} - Confidence: {confidence}"
    )
    
    return score, verdict, confidence, reasons_str
```

## Tests

Tous les tests existants passent sans modification, confirmant que la refactorisation :
- ✅ Préserve le comportement existant
- ✅ N'introduit pas de régressions
- ✅ Maintient la compatibilité avec le code existant

```
================ 21 passed in 25.00s =================
```

## Bénéfices de la refactorisation

1. **Maintenabilité** : Le code est plus facile à comprendre et à modifier
2. **Testabilité** : Chaque fonction peut être testée indépendamment
3. **Lisibilité** : Le code est auto-documenté et plus clair
4. **Évolutivité** : Facile d'ajouter de nouvelles règles ou de modifier les existantes
5. **Debugging** : Les logs sont plus informatifs et la structure facilite le débogage

## Prochaines étapes possibles

1. **Améliorer le calcul de variance** : Implémenter une vraie analyse par segments en décodant le fichier
2. **Ajouter des tests unitaires** pour chaque fonction helper
3. **Externaliser les constantes** dans un fichier de configuration
4. **Ajouter des métriques** de performance pour chaque règle
5. **Créer des visualisations** du processus de scoring

## Conclusion

Cette refactorisation améliore significativement la qualité du code sans changer son comportement. Le système de scoring est maintenant plus transparent, plus facile à maintenir et prêt pour de futures améliorations.
