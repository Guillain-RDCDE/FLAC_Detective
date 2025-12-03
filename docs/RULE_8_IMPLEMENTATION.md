# Implémentation de la Règle 8 : Exception Nyquist

## ✅ Problème résolu

Les fichiers authentiques avec cutoff élevé (proche de Nyquist) étaient parfois pénalisés par la Règle 2 (déficit de fréquence). La Règle 8 protège ces fichiers en accordant un bonus basé sur la proximité du cutoff avec la fréquence de Nyquist.

## 📋 Changements effectués

### 1. Nouveau fichier: `rules.py` (mis à jour)
Ajout de la fonction `apply_rule_8_nyquist_exception()` qui:
- Calcule le ratio `cutoff_freq / (sample_rate / 2)`
- Accorde un bonus si le ratio est >= 95%
- Bloque le bonus si une signature MP3 est détectée (sauf si l'analyse des silences confirme l'authenticité)

### 2. Fichier modifié: `calculator.py`
- Import de `apply_rule_8_nyquist_exception`
- Ajout de l'appel à la Règle 8 dans `_apply_scoring_rules()`
- Passage du `silence_ratio` de la Règle 7 à la Règle 8
- Mise à jour de la docstring (système à 8 règles)

### 3. Nouveau fichier de tests: `test_rule8.py`
Tests couvrant:
- Bonus fort (cutoff >= 98% de Nyquist): -50 points
- Bonus modéré (95% <= cutoff < 98%): -30 points
- Pas de bonus (cutoff < 95%): 0 point
- Blocage par signature MP3
- Override par analyse des silences
- Différents sample rates (44.1, 48, 96 kHz)

### 4. Documentation mise à jour: `TECHNICAL_RULES_SUMMARY.md`
- Version passée de v0.2 à v0.3
- Ajout de la Règle 8 avec exemples

## 🎯 Scoring de la Règle 8

| Condition | Score | Explication |
|-----------|-------|-------------|
| cutoff >= 98% Nyquist | **-50 pts** | Bonus fort (fichier authentique) |
| 95% <= cutoff < 98% Nyquist | **-30 pts** | Bonus modéré (probablement authentique) |
| cutoff < 95% Nyquist | **0 pt** | Pas de bonus |

**Blocage du bonus:**
- Si signature MP3 détectée (Règle 1) ET (pas d'analyse silence OU silence_ratio >= 0.15)
- Le bonus est autorisé si signature MP3 détectée MAIS silence_ratio < 0.15

## 📊 Exemples concrets

### Fichier avec cutoff 21878 Hz @ 44.1 kHz
- Nyquist = 22050 Hz
- Ratio = 21878 / 22050 = 99.2%
- **Bonus: -50 points** (authentique)

### Fichier avec cutoff 21000 Hz @ 44.1 kHz
- Nyquist = 22050 Hz
- Ratio = 21000 / 22050 = 95.2%
- **Bonus: -30 points** (probablement authentique)

### Fichier avec cutoff 20000 Hz @ 44.1 kHz
- Nyquist = 22050 Hz
- Ratio = 20000 / 22050 = 90.7%
- **Bonus: 0 point** (pas de protection)

## ✅ Tests

Tous les tests passent:
- `test_rule8.py`: 6/6 tests ✓
- `test_new_scoring.py`: Tous les tests existants passent ✓

## 🎯 Impact attendu

Cette règle devrait **éliminer les faux positifs** pour les fichiers authentiques de haute qualité avec cutoff proche de Nyquist (comme les 12 fichiers mentionnés avec cutoff à 21878 Hz).
