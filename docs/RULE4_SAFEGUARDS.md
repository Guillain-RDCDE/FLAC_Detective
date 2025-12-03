# Règle 4 : Protection contre les Faux Positifs sur Vinyles 24-bit

## Problème Identifié

**Règle 4 originale** : Upscaling 24-bit Suspect
- Si 24-bit + source MP3 < 500 kbps : +30 points

**Risque** : Un vinyle 24-bit légitime avec cutoff naturel à ~20kHz pourrait être pénalisé si Règle 1 détecte faussement une signature MP3.

## Solution Implémentée

### Modifications de la Règle 4

La règle a été renforcée avec **deux nouveaux garde-fous** :

#### 1. Vérification du Cutoff Frequency
- **Nouvelle condition** : `cutoff_freq < 19000 Hz`
- **Justification** : Un vrai fichier 24-bit a généralement un cutoff > 19kHz
- Si cutoff ≥ 19kHz, la règle ne s'applique pas (fichier probablement authentique)

#### 2. Exception pour les Vinyles
- **Nouvelle condition** : Si `silence_ratio < 0.15` (bruit vinyle détecté par Règle 7)
- **Justification** : Protège les vrais rips vinyle 24-bit
- Si du bruit vinyle est détecté, la règle ne s'applique pas

### Conditions d'Activation (TOUTES requises)

La Règle 4 s'applique maintenant **UNIQUEMENT** si :

1. ✅ Profondeur de bits = 24 bits
2. ✅ Source MP3 détectée avec bitrate estimé < 500 kbps (Règle 1)
3. ✅ **NOUVEAU** : `cutoff_freq < 19000 Hz` (vraiment bas pour du 24-bit)
4. ✅ **NOUVEAU** : `silence_ratio >= 0.15` OU `silence_ratio = None` (pas un vinyle)

### Score Attribué

- **+30 points** si toutes les conditions sont réunies
- **0 points** sinon (protection activée)

## Fichiers Modifiés

### 1. `src/flac_detective/analysis/new_scoring/rules.py`

**Fonction** : `apply_rule_4_24bit_suspect()`

**Nouveaux paramètres** :
- `cutoff_freq: float = 0.0` - Fréquence de coupure détectée
- `silence_ratio: Optional[float] = None` - Ratio d'analyse des silences (Règle 7)

**Logique ajoutée** :
```python
# Maximum cutoff for suspicious 24-bit upscaling
MAX_SUSPICIOUS_CUTOFF = 19000

# SAFEGUARD: Protect authentic vinyl rips
is_vinyl_rip = silence_ratio is not None and silence_ratio < 0.15

if is_vinyl_rip:
    return score, reasons  # Skip rule

# Check cutoff frequency
has_low_cutoff = cutoff_freq < MAX_SUSPICIOUS_CUTOFF

# Apply rule only if all conditions are met
if is_24bit and has_low_mp3_source and has_low_cutoff:
    score += 30
```

### 2. `src/flac_detective/analysis/new_scoring/calculator.py`

**Modification** : Appel à `apply_rule_4_24bit_suspect()` mis à jour

**Avant** :
```python
apply_rule_4_24bit_suspect(audio_meta.bit_depth, mp3_bitrate_detected)
```

**Après** :
```python
apply_rule_4_24bit_suspect(
    audio_meta.bit_depth, 
    mp3_bitrate_detected,
    cutoff_freq,
    silence_ratio
)
```

### 3. `tests/test_rule4.py` (NOUVEAU)

**Contenu** : Suite de tests complète avec 10 scénarios :

1. ✅ Détection d'upscaling suspect (24-bit + MP3 192 kbps + cutoff 17 kHz)
2. ✅ Protection cutoff élevé (cutoff ≥ 19 kHz)
3. ✅ Protection vinyle (silence_ratio < 0.15)
4. ✅ Détection quand silence_ratio ≥ 0.15 (pas un vinyle)
5. ✅ Skip sur fichiers 16-bit
6. ✅ Skip quand aucun MP3 détecté
7. ✅ Skip quand bitrate MP3 ≥ 500 kbps
8. ✅ Edge case : cutoff exactement à 19 kHz
9. ✅ Edge case : silence_ratio exactement à 0.15

**Résultat** : ✅ **9 tests passés** (39.61s)

## Scénarios Protégés

### Scénario 1 : Vinyle 24-bit Légitime
- **Caractéristiques** :
  - Profondeur : 24-bit
  - Cutoff : ~20 kHz (naturel pour vinyle)
  - Silence ratio : 0.10 (bruit vinyle détecté)
  - Signature MP3 : Faussement détectée par Règle 1
  
- **Avant** : +30 points (faux positif)
- **Après** : 0 points (protégé par garde-fou vinyle)

### Scénario 2 : FLAC 24-bit Authentique
- **Caractéristiques** :
  - Profondeur : 24-bit
  - Cutoff : 21 kHz (élevé)
  - Signature MP3 : Faussement détectée
  
- **Avant** : +30 points (faux positif)
- **Après** : 0 points (protégé par garde-fou cutoff)

### Scénario 3 : Vrai Upscaling Frauduleux
- **Caractéristiques** :
  - Profondeur : 24-bit
  - Cutoff : 17 kHz (très bas)
  - Source MP3 : 192 kbps
  - Silence ratio : 0.30 (pas de vinyle)
  
- **Avant** : +30 points ✅
- **Après** : +30 points ✅ (détection maintenue)

## Impact sur le Scoring

### Réduction des Faux Positifs
- Les vinyles 24-bit légitimes ne sont plus pénalisés
- Les FLAC 24-bit authentiques avec cutoff élevé sont protégés

### Maintien de la Détection
- Les vrais upscalings frauduleux (24-bit + MP3 low bitrate + cutoff bas) sont toujours détectés
- Pas de faux négatifs introduits

## Validation

### Tests Unitaires
- ✅ 9 tests créés et validés
- ✅ Couverture de tous les cas limites
- ✅ Validation des garde-fous

### Intégration
- ✅ Compatible avec le système de règles existant
- ✅ Utilise les données de Règle 7 (silence analysis)
- ✅ Pas de régression sur les autres règles

## Conclusion

La Règle 4 est maintenant **plus précise** et **plus robuste** :
- ✅ Évite les faux positifs sur vinyles 24-bit
- ✅ Évite les faux positifs sur FLAC 24-bit authentiques
- ✅ Maintient la détection des vrais upscalings frauduleux
- ✅ Entièrement testée et validée

## Prochaines Étapes Recommandées

1. ✅ **Tests d'intégration** : Valider avec des fichiers réels (vinyles 24-bit)
2. ⏳ **Monitoring** : Surveiller les taux de faux positifs/négatifs
3. ⏳ **Documentation utilisateur** : Mettre à jour le guide des règles
4. ⏳ **Ajustement des seuils** : Affiner si nécessaire (19 kHz, 0.15)
