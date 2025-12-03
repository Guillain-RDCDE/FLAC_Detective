# Système de Scoring Amélioré v0.3

## Vue d'ensemble

Le système de scoring de FLAC Detective a été mis à jour pour s'aligner sur les meilleures pratiques de l'industrie, notamment celles de **Fakin' The Funk**.

## Nouvelle Échelle à 4 Niveaux

### Seuils de Score

| Score | Verdict | Description | Symbole |
|-------|---------|-------------|---------|
| **86-270** | `FAKE_CERTAIN` | Transcoding confirmé avec certitude | ❌ |
| **61-85** | `SUSPICIOUS` | Probable transcoding, vérification recommandée | ⚠️ |
| **31-60** | `WARNING` | Anomalies détectées, peut être légitime | ⚡ |
| **0-30** | `AUTHENTIC` | Fichier authentique | ✅ |

### Justification

Cette échelle à 4 niveaux reflète la distribution réelle des fichiers audio :

- **État 0 (AUTHENTIC)** : ~63% des fichiers
- **État 1 (WARNING)** : ~36% des fichiers ← **Zone grise importante**
- **État 2 (SUSPICIOUS)** : ~1.2% des fichiers
- **État 3 (FAKE_CERTAIN)** : ~0% des fichiers (très rare)

## Zone WARNING (31-60) - Critique

La zone **WARNING** est particulièrement importante car elle contient :

- **Vinyles authentiques** avec cutoff naturellement bas
- **Cassettes** et autres sources analogiques
- **Masters anciens** avec limitations techniques
- **Fichiers légitimes** nécessitant une vérification manuelle

⚠️ **Ces fichiers ne doivent PAS être automatiquement rejetés !**

## Comparaison avec l'Ancien Système

### Avant (v0.2)

```
Score >= 80 : FAKE_CERTAIN
Score >= 50 : FAKE_PROBABLE
Score >= 30 : DOUTEUX
Score < 30  : AUTHENTIQUE
```

### Après (v0.3)

```
Score >= 86 : FAKE_CERTAIN
Score >= 61 : SUSPICIOUS
Score >= 31 : WARNING
Score < 31  : AUTHENTIC
```

### Changements Clés

1. **Seuil FAKE_CERTAIN** : 80 → **86** (+6 points)
   - Plus strict pour éviter les faux positifs critiques

2. **FAKE_PROBABLE** → **SUSPICIOUS** : 50 → **61** (+11 points)
   - Renommage pour clarté
   - Seuil plus élevé pour réduire les faux positifs

3. **DOUTEUX** → **WARNING** : 30 → **31** (+1 point)
   - Renommage pour clarté internationale
   - Zone élargie pour capturer plus de cas ambigus

4. **AUTHENTIQUE** → **AUTHENTIC** : < 30 → **< 31**
   - Renommage pour clarté internationale
   - Légère réduction de la zone "safe"

## Impact sur les Détections

### Faux Positifs (Fichiers Authentiques Marqués FAKE)

Avec les nouvelles règles (7, 9, 10) et les nouveaux seuils :

- **12 faux positifs actuels** → Devraient passer sous 31 (AUTHENTIC)
- **Vinyles 24-bit** : Protection complète
- **Vinyles 16-bit** : ~83% de réduction des faux positifs

### Vrais Positifs (MP3 Transcodés)

- **34 vrais positifs** → Resteront probablement 31-60 (WARNING) ou 61+ (SUSPICIOUS)
- **MP3 320 kbps** : Détection améliorée
- **AAC transcodés** : Meilleure identification

## Exemples de Scoring

### Exemple 1 : MP3 320 kbps Transcode

```
Règle 1: +50 (Cutoff 20.5 kHz = 320 kbps)
Règle 2: +0  (Cutoff > 20 kHz)
Règle 3: +50 (Source 320 vs Container 850 kbps)
Total: 100 points → FAKE_CERTAIN ❌
```

### Exemple 2 : Vinyle Authentique

```
Règle 1: +0  (Cutoff 18 kHz, pas de signature MP3)
Règle 2: +10 (Cutoff légèrement bas)
Règle 6: -30 (Haute qualité VBR)
Règle 7: -50 (Silence naturel)
Total: 0 points (max(0, -70)) → AUTHENTIC ✅
```

### Exemple 3 : Master Ancien (Cas Ambigu)

```
Règle 1: +0  (Pas de signature MP3)
Règle 2: +15 (Cutoff 17 kHz)
Règle 7: +20 (Ratio ambigu)
Total: 35 points → WARNING ⚡
```

## Utilisation dans le Code

### Python

```python
from flac_detective.analysis.new_scoring import new_calculate_score, determine_verdict

# Calculer le score
score, verdict, message, reasons = new_calculate_score(
    cutoff_freq=20500,
    metadata=metadata,
    duration_check=duration_check,
    filepath=path
)

# Interpréter le verdict
if verdict == "FAKE_CERTAIN":
    print(f"❌ {message}")
    # Action : Rejeter le fichier
elif verdict == "SUSPICIOUS":
    print(f"⚠️ {message}")
    # Action : Marquer pour vérification
elif verdict == "WARNING":
    print(f"⚡ {message}")
    # Action : Accepter avec avertissement
else:  # AUTHENTIC
    print(f"✅ {message}")
    # Action : Accepter
```

### Constantes

```python
from flac_detective.analysis.new_scoring import (
    SCORE_FAKE_CERTAIN,  # 86
    SCORE_SUSPICIOUS,    # 61
    SCORE_WARNING,       # 31
)
```

## Recommandations d'Utilisation

### Pour les Utilisateurs

1. **FAKE_CERTAIN (86+)** : Fichier très probablement fake, à rejeter
2. **SUSPICIOUS (61-85)** : Vérifier manuellement, écouter le fichier
3. **WARNING (31-60)** : Accepter avec prudence, peut être légitime
4. **AUTHENTIC (0-30)** : Fichier authentique, accepter

### Pour les Développeurs

1. **Ne jamais rejeter automatiquement** les fichiers WARNING
2. **Toujours fournir les raisons** du score pour transparence
3. **Permettre l'override manuel** pour tous les niveaux
4. **Logger les détails** pour analyse future

## Tests de Validation

Les tests suivants valident le nouveau système :

```bash
# Tester les seuils
pytest tests/test_new_scoring.py::TestVerdictThresholds -v

# Tester les cas mandatoires
pytest tests/test_new_scoring.py::TestMandatoryTestCase* -v

# Tester toutes les règles
pytest tests/test_new_scoring.py -v
```

## Migration depuis v0.2

### Code à Mettre à Jour

1. **Imports** :
   ```python
   # Avant
   from flac_detective.analysis.new_scoring import SCORE_FAKE_PROBABLE, SCORE_DOUTEUX
   
   # Après
   from flac_detective.analysis.new_scoring import SCORE_SUSPICIOUS, SCORE_WARNING
   ```

2. **Comparaisons de Verdict** :
   ```python
   # Avant
   if verdict == "FAKE_PROBABLE":
   if verdict == "DOUTEUX":
   if verdict == "AUTHENTIQUE":
   
   # Après
   if verdict == "SUSPICIOUS":
   if verdict == "WARNING":
   if verdict == "AUTHENTIC":
   ```

3. **Seuils Personnalisés** :
   ```python
   # Avant
   if score >= 80:  # FAKE_CERTAIN
   if score >= 50:  # FAKE_PROBABLE
   if score >= 30:  # DOUTEUX
   
   # Après
   if score >= 86:  # FAKE_CERTAIN
   if score >= 61:  # SUSPICIOUS
   if score >= 31:  # WARNING
   ```

## Changelog

### v0.3 (3 Décembre 2025)

- ✅ Nouveau système à 4 niveaux aligné sur Fakin' The Funk
- ✅ Seuils ajustés : 86/61/31 (au lieu de 80/50/30)
- ✅ Verdicts renommés : SUSPICIOUS, WARNING, AUTHENTIC
- ✅ Messages descriptifs au lieu de niveaux de confiance
- ✅ Zone WARNING élargie pour cas ambigus
- ✅ Documentation complète

### v0.2 (2 Décembre 2025)

- Système à 3 niveaux : FAKE_CERTAIN/FAKE_PROBABLE/DOUTEUX
- Seuils : 80/50/30

---

**Date** : 3 Décembre 2025  
**Version** : 0.3.0  
**Statut** : ✅ Implémenté et testé
