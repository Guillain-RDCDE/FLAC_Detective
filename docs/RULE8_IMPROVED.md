# Règle 8 Améliorée : Exception Nyquist avec Garde-Fous

## 📅 Date : 3 Décembre 2025

## 🎯 Objectif

Améliorer la Règle 8 pour qu'elle soit **toujours appliquée** avec des garde-fous intelligents, au lieu de bloquer complètement le bonus en présence d'une signature MP3.

## ❌ Ancien Comportement (Blocage Complet)

```python
if mp3_bitrate_detected is not None:
    if silence_ratio is None or silence_ratio >= 0.15:
        # BLOQUER COMPLÈTEMENT le bonus
        return 0, []
```

**Problème** : Des fichiers authentiques avec cutoff proche de Nyquist (21.5+ kHz) mais ayant une signature MP3-like ne recevaient AUCUN bonus, même s'ils étaient légitimes.

## ✅ Nouveau Comportement (Garde-Fous Intelligents)

### Étape 1 : Calcul du Bonus de Base

Le bonus est **TOUJOURS calculé** en fonction du ratio cutoff/Nyquist :

```python
if cutoff_ratio >= 0.98:  # 21.6+ kHz pour 44.1kHz
    base_bonus = -50  # Très proche limite
elif cutoff_ratio >= 0.95:  # 21.0+ kHz pour 44.1kHz
    base_bonus = -30  # Probablement authentique
else:
    base_bonus = 0  # Pas de bonus
```

### Étape 2 : Application des Garde-Fous

Si une signature MP3 est détectée, le bonus est ajusté selon le `silence_ratio` :

| Condition | Bonus Final | Raison |
|-----------|-------------|--------|
| **Pas de signature MP3** | Base bonus (-50 ou -30) | Authentique, bonus complet |
| **MP3 + ratio ≤ 0.15** | Base bonus (-50 ou -30) | Silence authentique malgré signature |
| **MP3 + 0.15 < ratio ≤ 0.2** | **-15 points** | Zone grise, bonus réduit |
| **MP3 + ratio > 0.2** | **0 points** | Dither suspect, bonus annulé |

## 📊 Exemples de Scoring

### Exemple 1 : Fichier Authentique HQ (Pas de MP3)

```
Cutoff: 21.8 kHz (98.9% de Nyquist à 44.1kHz)
MP3 détecté: Non
Silence ratio: N/A

→ Bonus: -50 points
→ Raison: "R8: Cutoff à 98.9% de Nyquist → Très proche limite (-50pts)"
```

### Exemple 2 : Vinyle avec Cutoff Élevé (MP3 + Silence Authentique)

```
Cutoff: 21.6 kHz (98.0% de Nyquist)
MP3 détecté: 320 kbps
Silence ratio: 0.05 (< 0.15, silence naturel)

→ Bonus: -50 points
→ Raison: "R8: Cutoff à 98.0% de Nyquist → Très proche limite 
          (-50pts, MP3 signature mais silence authentique)"
```

### Exemple 3 : Zone Grise (MP3 + Ratio Ambigu)

```
Cutoff: 21.6 kHz (98.0% de Nyquist)
MP3 détecté: 320 kbps
Silence ratio: 0.18 (0.15 < ratio ≤ 0.2, zone grise)

→ Bonus: -15 points (RÉDUIT)
→ Raison: "R8: Cutoff à 98.0% de Nyquist → Bonus réduit 
          (MP3 signature + zone grise) (-15pts)"
```

### Exemple 4 : Dither Suspect (MP3 + Ratio Élevé)

```
Cutoff: 21.6 kHz (98.0% de Nyquist)
MP3 détecté: 320 kbps
Silence ratio: 0.3 (> 0.2, dither artificiel)

→ Bonus: 0 points (ANNULÉ)
→ Raison: "R8: Bonus Nyquist annulé (MP3 signature 320 kbps + 
          dither suspect 0.30 > 0.2)"
```

## 🔍 Logique Détaillée

### Cas 1 : Pas de Signature MP3

```python
if mp3_bitrate_detected is None:
    # APPLIQUER le bonus sans condition
    final_bonus = base_bonus
```

**Fichiers concernés** : FLACs authentiques haute qualité

### Cas 2 : Signature MP3 + Silence Authentique

```python
if mp3_bitrate_detected and silence_ratio <= 0.15:
    # APPLIQUER le bonus (override)
    final_bonus = base_bonus
```

**Fichiers concernés** : Vinyles, cassettes avec cutoff naturellement élevé

### Cas 3 : Signature MP3 + Zone Grise

```python
if mp3_bitrate_detected and 0.15 < silence_ratio <= 0.2:
    # RÉDUIRE le bonus
    final_bonus = -15
```

**Fichiers concernés** : Cas ambigus nécessitant prudence

### Cas 4 : Signature MP3 + Dither Suspect

```python
if mp3_bitrate_detected and silence_ratio > 0.2:
    # ANNULER le bonus
    final_bonus = 0
```

**Fichiers concernés** : MP3 320 kbps transcodés avec dither artificiel

## 🧪 Tests

### Tests Mis à Jour

```python
def test_strong_bonus_98_percent():
    """Bonus fort pour cutoff >= 98% de Nyquist."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, None, None)
    assert score == -50

def test_applied_with_authentic_silence():
    """Bonus APPLIQUÉ malgré MP3 si silence authentique."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.05)
    assert score == -50
    assert "MP3 signature mais silence authentique" in reasons[0]

def test_reduced_in_grey_zone():
    """Bonus RÉDUIT si MP3 + zone grise."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.18)
    assert score == -15
    assert "Bonus réduit" in reasons[0]

def test_cancelled_by_mp3_signature_and_dither():
    """Bonus ANNULÉ si MP3 + dither suspect."""
    score, reasons = apply_rule_8_nyquist_exception(21800, 44100, 320, 0.3)
    assert score == 0
    assert "annulé" in reasons[0]
```

**Résultat** : ✅ **7/7 tests passants**

## 📈 Impact

### Avant (Blocage Complet)

| Fichier | Cutoff | MP3 | Ratio | Bonus Ancien |
|---------|--------|-----|-------|--------------|
| FLAC HQ | 21.8 kHz | Non | N/A | **-50** ✅ |
| Vinyle HQ | 21.6 kHz | 320 | 0.05 | **0** ❌ (bloqué) |
| Zone grise | 21.6 kHz | 320 | 0.18 | **0** ❌ (bloqué) |
| MP3 transcode | 21.6 kHz | 320 | 0.3 | **0** ✅ |

**Problème** : Vinyles légitimes pénalisés !

### Après (Garde-Fous Intelligents)

| Fichier | Cutoff | MP3 | Ratio | Bonus Nouveau |
|---------|--------|-----|-------|---------------|
| FLAC HQ | 21.8 kHz | Non | N/A | **-50** ✅ |
| Vinyle HQ | 21.6 kHz | 320 | 0.05 | **-50** ✅ (appliqué) |
| Zone grise | 21.6 kHz | 320 | 0.18 | **-15** ⚡ (réduit) |
| MP3 transcode | 21.6 kHz | 320 | 0.3 | **0** ✅ (annulé) |

**Amélioration** : Protection des vinyles tout en détectant les faux !

## 🎯 Avantages

1. **Toujours appliquée** : La règle calcule toujours le bonus de base
2. **Garde-fous intelligents** : Ajustement selon le contexte (MP3 + silence)
3. **Granularité** : 4 niveaux de bonus (-50, -30, -15, 0)
4. **Protection vinyles** : Fichiers authentiques avec signature MP3-like protégés
5. **Détection maintenue** : Vrais transcodes toujours détectés (ratio > 0.2)

## 📝 Code Modifié

### Fichiers

- `src/flac_detective/analysis/new_scoring/rules.py` : Fonction `apply_rule_8_nyquist_exception()`
- `tests/test_rule8.py` : Tests mis à jour

### Lignes Ajoutées/Modifiées

- **Ajouté** : ~30 lignes (logique garde-fous)
- **Modifié** : ~20 lignes (documentation, tests)
- **Supprimé** : ~15 lignes (ancien blocage)

## 🚀 Prochaines Étapes

1. ✅ Tests unitaires passants (7/7)
2. ⏳ Validation terrain sur fichiers réels
3. ⏳ Ajustement seuils si nécessaire (0.15, 0.2)
4. ⏳ Documentation utilisateur

---

**Version** : 0.3.1  
**Date** : 3 Décembre 2025  
**Statut** : ✅ Implémenté et testé  
**Tests** : 7/7 passants
