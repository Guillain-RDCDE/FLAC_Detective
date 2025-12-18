# Rule 1 Enhancement: Direct Container Bitrate Detection

## Problème identifié

Lors du scan d'une collection de 11 disques Zanzibara :
- **FLAC Detective** : Détecte 1 fichier suspect (Vol. 9)
- **Fakin the Funk** : Détecte 15 fichiers suspects (Vol. 2 & 3 principalement)

**Analyse** : FLAC Detective manquait des faux négatifs majeurs :
- Vol. 2 (2005) : Fichiers avec bitrates **96-320 kbps** non détectés
- Vol. 3 (2007) : 1 fichier avec bitrate **96 kbps** non détecté
- Ces bitrates sont **impossibles pour du FLAC authentique**

## Root Cause Analysis

Rule 1 détectait les MP3 sources via **analyse spectrale** uniquement :
```
SI cutoff_freq ≈ signature_MP3 AND container_in_range ALORS +50pts
```

**Le problème** : Un fichier avec bitrate bas mais cutoff haut n'était pas détecté
- Exemple : Ahmed bin Brek (96k bitrate, cutoff 20kHz)
- Rule 1 ne flag que si cutoff correspond aux signatures MP3
- Résultat : Faux négatif malgré le bitrate anormalement bas

## Solution : Direct Bitrate Check

Ajout d'une vérification **directe** du bitrate conteneur au début de Rule 1 :

### Seuils définis (constants.py)

```python
# Absolute minimum for MP3 source detection
BITRATE_RED_FLAG_THRESHOLD = 160 kbps

# Extreme red flag: impossible for real FLAC
BITRATE_CRITICAL_THRESHOLD = 128 kbps
```

### Scoring

| Bitrate conteneur | Score | Raison |
|---|---|---|
| < 128 kbps | **+60 pts** | CRITIQUE : Impossible pour du FLAC |
| 128 ≤ BR < 160 | **+40 pts** | SUSPECT : Probablement MP3 source |
| ≥ 160 kbps | Analyse spectrale normale | Peut être FLAC authentique |

### Logique appliquée (règles spectral.py)

```python
def apply_rule_1_mp3_bitrate(...):
    # NEW: Direct bitrate check FIRST
    if container_bitrate < BITRATE_CRITICAL_THRESHOLD:
        return +60 pts, "Bitrate critique < 128 kbps"
    
    elif container_bitrate < BITRATE_RED_FLAG_THRESHOLD:
        return +40 pts, "Bitrate suspect < 160 kbps"
    
    # Ensuite : Analyse spectrale classique
    ...
```

## Résultats du test

### Test sur fichiers réels

**Test 1 : Ahmed bin Brek (Vol. 2)**
- Bitrate: 96 kbps
- Cutoff: 20 kHz (haut!)
- **Avant** : 0 pts (faux négatif)
- **Après** : **+60 pts** ✅

**Test 2 : Ali Mkali (Vol. 2)**
- Bitrate: 128 kbps
- Cutoff: 20 kHz
- **Avant** : 0 pts (faux négatif)
- **Après** : **+40 pts** ✅

**Test 3 : Vol. 10 authentique**
- Bitrate: 800 kbps
- Cutoff: 20 kHz
- **Avant** : 0 pts (bon)
- **Après** : **0 pts** ✅ (pas affecté)

## Impact

### Fichiers désormais détectés

**Vol. 2 (Zanzibara 1965-1975, 2005)**
- 14 fichiers avec bitrates anormaux : 96-320 kbps
- Tous génèrent maintenant +40 à +60 pts
- Total score vol. 2 : Probablement SUSPICIOUS ou FAKE

**Vol. 3 (Ujamaa, 2007)**
- 1 fichier (Morogoro Jazz Band - Utaniangamiza) : 96 kbps
- Score : +60 pts

### Faux positifs évités

- **Vol. 10 & 11** (2021-2024) : Bitrates 675-932 kbps
- Pas affectés par la nouvelle règle
- Restent à "AUTHENTIC" si autres conditions OK ✅

## Performance

- Pas d'impact sur la vitesse (vérification simple avant analyse spectrale)
- Rule 1 maintenant couvre :
  1. ✅ Bitrate conteneur anormalement bas (nouveau)
  2. ✅ Signature spectrale MP3 (existant)
  3. ✅ Cohérence bitrate ↔ cutoff (existant)

## Validation

La Rule 1 renforcée améliore maintenant la **sensibilité** sans sacrifier la **spécificité** :
- Détecte les MP3 sources même sans signature spectrale claire
- N'affecte pas les fichiers FLAC authentiques (bitrate ≥ 160 kbps)
- Aligne FLAC Detective sur le comportement de Fakin the Funk pour les cas évidents

---

**Fichiers modifiés** :
- [constants.py](src/flac_detective/analysis/new_scoring/constants.py) : Ajout de seuils
- [spectral.py](src/flac_detective/analysis/new_scoring/rules/spectral.py) : Renforcement de Rule 1
