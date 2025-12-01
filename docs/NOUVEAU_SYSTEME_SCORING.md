# NOUVEAU SYSTÈME DE DÉTECTION DES FAUX FLAC

## Vue d'ensemble

Le nouveau système de scoring utilise une approche à **6 règles** avec un score de **0 à 100 points**, où :
- **Score élevé = Plus susceptible d'être un faux**
- **Score faible = Plus susceptible d'être authentique**

## Système de Scoring (0-100 points)

### Seuils de Décision

| Score | Verdict | Confiance | Action Recommandée |
|-------|---------|-----------|-------------------|
| ≥ 80 | **FAKE_CERTAIN** | TRÈS ÉLEVÉE | SUPPRIMER |
| 50-79 | **FAKE_PROBABLE** | ÉLEVÉE | MARQUER_SUSPECT |
| 30-49 | **DOUTEUX** | MOYENNE | VÉRIFICATION_MANUELLE |
| < 30 | **AUTHENTIQUE** | ÉLEVÉE | CONSERVER |

## Les 6 Règles de Détection

### RÈGLE 1 : Bitrate Constant MP3 (50 POINTS)

**Principe** : Un fichier FLAC authentique a un bitrate variable. Si le bitrate réel correspond exactement à un standard MP3, c'est un transcode.

**Calcul** :
```
bitrate_réel = (taille_fichier_octets × 8) / (durée_secondes × 1000)
```

**Bitrates MP3 Standards** : 96, 128, 160, 192, 224, 256, 320 kbps

**Tolérance** : ±10 kbps

**Points** : +50 si le bitrate réel = bitrate MP3 standard (±10 kbps)

**Justification** : Un bitrate exactement égal à un standard MP3 indique une compression avec perte préalable.

---

### RÈGLE 2 : Cutoff Fréquence vs Taux d'Échantillonnage (0-30 POINTS)

**Principe** : La fréquence maximale théorique est ~45% du sample rate (théorème de Nyquist). Un cutoff significativement inférieur indique une compression.

**Seuils de Cutoff** :

| Sample Rate | Seuil Cutoff |
|-------------|--------------|
| 44100 Hz | 20000 Hz |
| 48000 Hz | 22000 Hz |
| 88200 Hz | 40000 Hz |
| 96000 Hz | 44000 Hz |
| 176400 Hz | 80000 Hz |
| 192000 Hz | 88000 Hz |
| Autre | sample_rate × 0.45 |

**Calcul** :
```
Si cutoff_freq < seuil :
    points = min((seuil - cutoff_freq) / 200, 30)
```

**Justification** : Un cutoff bas révèle une compression MP3 antérieure qui a éliminé les hautes fréquences.

---

### RÈGLE 3 : Bitrate Réel vs Bitrate Attendu (50 POINTS)

**Principe** : Un FLAC authentique a un bitrate cohérent avec son format. Un écart important indique une source compressée.

**Bitrates Minimums Attendus** :

| Format | Bitrate Minimum |
|--------|----------------|
| 44100 Hz 16-bit | 600 kbps |
| 48000 Hz 16-bit | 650 kbps |
| 44100 Hz 24-bit | 900 kbps |
| 48000 Hz 24-bit | 1000 kbps |
| 88200 Hz 24-bit | 1800 kbps |
| 96000 Hz 24-bit | 2000 kbps |

**Calcul** :
```
bitrate_apparent = sample_rate × bit_depth × channels / 1000

Si bitrate_réel < 400 kbps ET bitrate_apparent > bitrate_minimum_attendu :
    points = +50
```

**Justification** : Un fichier avec metadata 24-bit/96kHz mais bitrate de 320 kbps est forcément un upscale.

---

### RÈGLE 4 : Exception Fichiers 24-bit Suspects (30 POINTS)

**Principe** : Un fichier 24-bit authentique a nécessairement un bitrate > 500 kbps. En dessous, c'est forcément un upscale.

**Calcul** :
```
Si bit_depth = 24 ET bitrate_réel < 500 kbps :
    points = +30
```

**Justification** : Physiquement impossible d'avoir un vrai 24-bit avec si peu de données.

---

### RÈGLE 5 : Éviter Faux Positifs - Bitrate Variable Élevé (-40 POINTS)

**Principe** : Un FLAC authentique avec bitrate variable élevé est probablement légitime, même si le cutoff est légèrement bas (mauvais équipement d'enregistrement).

**Seuils** :
- Seuil variance : 100 kbps
- Seuil bitrate élevé : 1000 kbps

**Calcul** :
```
Si bitrate_réel > 1000 kbps ET variance_bitrate > 100 kbps :
    points = -40 (minimum 0)
```

**Justification** : Un bitrate élevé et variable indique un vrai FLAC avec contenu riche.

---

### RÈGLE 6 : Éviter Faux Positifs - Cohérence Bitrate (-30 POINTS)

**Principe** : Si bitrate réel ≈ bitrate apparent et tous deux élevés, le fichier est cohérent, donc probablement authentique.

**Seuils** :
- Seuil cohérence : 800 kbps
- Tolérance : 100 kbps

**Calcul** :
```
Si |bitrate_réel - bitrate_apparent| < 100 kbps ET bitrate_réel > 800 kbps :
    points = -30 (minimum 0)
```

**Justification** : La cohérence entre bitrate réel et théorique indique un fichier non-modifié.

---

## Ordre d'Exécution

1. Extraire métadonnées : sample_rate, bits_per_sample, durée, taille, cutoff_fréquence
2. Calculer bitrate_réel et bitrate_apparent
3. Calculer variance_bitrate
4. Initialiser score à 0
5. Appliquer RÈGLE 1 (bitrate MP3 constant)
6. Appliquer RÈGLE 2 (cutoff fréquence)
7. Appliquer RÈGLE 3 (bitrate réel vs attendu)
8. Appliquer RÈGLE 4 (exception 24-bit)
9. Appliquer RÈGLE 5 (réduction pour variance élevée)
10. Appliquer RÈGLE 6 (réduction pour cohérence)
11. Déterminer le verdict selon les seuils
12. Retourner résultat avec verdict, score, confiance et raisons

## Tests de Validation Obligatoires

### TEST 1 : MP3 320 kbps avec fréquence élevée ✅

**Fichier** : `02 - Dalton - Soul brother.flac`

**Paramètres** :
- Sample rate: 44100 Hz
- Bit depth: 16 bits
- Cutoff: 21166 Hz
- Bitrate réel: 320 kbps
- Bitrate apparent: 851 kbps

**Score Attendu** :
- Règle 1: +50 points (bitrate = 320)
- Règle 2: +0 points (cutoff > 20000)
- Règle 3: +50 points (320 < 400 et 851 > 600)
- **Total: 100 points**

**Verdict Attendu** : **FAKE_CERTAIN** ✅

---

### TEST 2 : MP3 256 kbps en 24-bit ✅

**Fichier** : `01 - Ara Kekedjian - Mini, midi, maxi.flac`

**Paramètres** :
- Sample rate: 48000 Hz
- Bit depth: 24 bits
- Cutoff: 19143 Hz
- Bitrate réel: 256 kbps
- Bitrate apparent: 1663 kbps

**Score Attendu** :
- Règle 1: +50 points (bitrate = 256)
- Règle 2: +14 points ((22000-19143)/200)
- Règle 3: +50 points (256 < 400 et 1663 > 1000)
- Règle 4: +30 points (24-bit avec bitrate < 500)
- **Total: 144 points**

**Verdict Attendu** : **FAKE_CERTAIN** ✅

---

### TEST 3 : FLAC authentique de mauvaise qualité ✅

**Fichier** : Vieux vinyle numérisé

**Paramètres** :
- Sample rate: 44100 Hz
- Bit depth: 16 bits
- Cutoff: 18000 Hz
- Bitrate réel: 850 kbps
- Bitrate apparent: 850 kbps
- Variance: 150 kbps

**Score Attendu** :
- Règle 1: +0 points (850 n'est pas un standard MP3)
- Règle 2: +10 points ((20000-18000)/200)
- Règle 3: +0 points (850 > 400)
- Règle 6: -30 points (cohérent et > 800)
- **Total: -20 → 0 points (minimum)**

**Verdict Attendu** : **AUTHENTIQUE** ✅

---

### TEST 4 : FLAC authentique haute qualité ✅

**Fichier** : `01 - Hamid El Shaeri - Tew'idni dom.flac`

**Paramètres** :
- Sample rate: 44100 Hz
- Bit depth: 16 bits
- Cutoff: 21878 Hz
- Bitrate réel: 1580 kbps
- Bitrate apparent: 1580 kbps
- Variance: 200 kbps

**Score Attendu** :
- Règle 1: +0 points
- Règle 2: +0 points (cutoff > 20000)
- Règle 3: +0 points
- Règle 5: -40 points (bitrate > 1000 et variance > 100)
- **Total: -40 → 0 points (minimum)**

**Verdict Attendu** : **AUTHENTIQUE** ✅

---

## Fichiers à NE JAMAIS Marquer comme Fakes

### Condition 1 : Bitrate Variable Élevé
```
bitrate_réel > 1000 kbps ET variance_bitrate > 100 kbps
```

### Condition 2 : Cohérence Bitrate
```
|bitrate_réel - bitrate_apparent| < 100 kbps ET bitrate_réel > 800 kbps
```

Ces conditions indiquent des FLAC authentiques de haute qualité avec bitrate variable naturel.

---

## Paramètres Fixes (IMMUABLES)

| Paramètre | Valeur | Note |
|-----------|--------|------|
| Bitrates MP3 standard | [96, 128, 160, 192, 224, 256, 320] | Liste immuable |
| Tolérance bitrate | 10 kbps | Ne pas descendre sous 5, ne pas dépasser 15 |
| Seuil FAKE_CERTAIN | 80 points | |
| Seuil FAKE_PROBABLE | 50 points | |
| Seuil DOUTEUX | 30 points | |
| Seuil variance authenticité | 100 kbps | |
| Seuil bitrate élevé | 1000 kbps | |
| Seuil bitrate cohérent | 800 kbps | |
| Tolérance cohérence | 100 kbps | |

---

## Métriques de Performance Attendues

Sur un dataset de 164 fichiers suspects connus :

- **Taux de détection (rappel)** : minimum 95% (≥156/164 fichiers détectés)
- **Taux de précision** : minimum 95% (≤8 faux positifs)
- **F1-Score** : minimum 95%

---

## Changements par Rapport à l'Ancien Système

### Ancien Système
- Score 0-100% où **plus élevé = plus authentique**
- Basé principalement sur cutoff fréquence
- Pas de détection de bitrate constant
- Pas de variance analysis

### Nouveau Système
- Score 0-100 points où **plus élevé = plus fake**
- 6 règles complémentaires
- Détection précise des bitrates MP3 constants
- Analyse de variance pour éviter faux positifs
- 4 niveaux de verdict au lieu de 2

---

## Utilisation

Le nouveau système est automatiquement utilisé dans `analyzer.py` :

```python
from .new_scoring import new_calculate_score

score, verdict, confidence, reason = new_calculate_score(
    cutoff_freq, metadata, duration_check, filepath
)
```

Les résultats incluent maintenant :
- `score` : 0-100 points (plus élevé = plus fake)
- `verdict` : FAKE_CERTAIN / FAKE_PROBABLE / DOUTEUX / AUTHENTIQUE
- `confidence` : TRÈS ÉLEVÉE / ÉLEVÉE / MOYENNE
- `reason` : Explication détaillée des règles appliquées
