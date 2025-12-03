# SPÉCIFICATIONS TECHNIQUES DES RÈGLES DE DÉTECTION (v0.3)

## Vue d'ensemble
Système de scoring additif sur 100 points.
- **Score >= 80** : FAKE_CERTAIN
- **Score >= 50** : FAKE_PROBABLE
- **Score >= 30** : DOUTEUX
- **Score < 30** : AUTHENTIQUE

## Règle 1 : Signature Spectrale MP3 (CBR)
**Objectif** : Détecter les MP3 CBR convertis en FLAC.
- **Condition** :
  1. `cutoff_freq` correspond à une signature MP3 connue (± tolérance).
  2. `cutoff_freq` < 21 kHz.
  3. Variance spectrale faible (`cutoff_std` < 100 Hz).
  4. `bitrate_container` compatible avec le bitrate MP3 estimé (ex: 700-950 kbps pour MP3 320).
- **Action** :
  - **+50 points** si toutes conditions réunies.

## Règle 2 : Déficit de Fréquence (Cutoff)
**Objectif** : Pénaliser les fichiers dont le contenu fréquentiel est inférieur au maximum théorique.
- **Seuil** : Dépend du sample rate (ex: 20 kHz pour 44.1 kHz, 22 kHz pour 48 kHz).
- **Calcul** : `deficit = seuil_theorique - cutoff_freq`
- **Action** :
  - **+1 pt** par tranche de 200 Hz de déficit.
  - **Plafond** : +30 points max.

## Règle 3 : Incohérence Source vs Conteneur
**Objectif** : Détecter les fichiers "gonflés" (source basse qualité dans conteneur lourd).
- **Condition** :
  1. Source MP3 détectée (via Règle 1).
  2. `bitrate_container` > 600 kbps.
- **Action** :
  - **+50 points**.

## Règle 4 : Upscaling 24-bit Suspect
**Objectif** : Identifier les faux fichiers High-Res.
- **Condition** :
  1. Profondeur de bits = 24 bits.
  2. Source MP3 détectée avec bitrate estimé < 500 kbps.
- **Action** :
  - **+30 points**.

## Règle 5 : Haute Variance (Indicateur d'Authenticité)
**Objectif** : Identifier les caractéristiques naturelles du FLAC (VBR).
- **Condition** :
  1. `bitrate_real` > 1000 kbps.
  2. `bitrate_variance` > 100 kbps.
- **Action** :
  - **-40 points** (Bonus d'authenticité).

## Règle 6 : Protection Haute Qualité (RENFORCÉE)
**Objectif** : Protéger les FLACs authentiques avec caractéristiques de haute qualité.
- **Conditions** (TOUTES doivent être vraies) :
  1. Aucune signature MP3 détectée.
  2. `bitrate_container` > 700 kbps (augmenté de 600).
  3. `cutoff_freq` >= 19000 Hz (contenu HF substantiel).
  4. `bitrate_variance` > 50 kbps (VBR naturel).
- **Action** :
  - **-30 points** (Bonus d'authenticité).
- **Justification** : Cette combinaison de critères est difficile à falsifier et caractérise un FLAC authentique de haute qualité.

## Règle 7 : Analyse des Silences (Dither)
**Objectif** : Lever l'ambiguïté pour les cutoffs entre 19 kHz et 21.5 kHz.
- **Condition d'activation** : 19 kHz <= `cutoff_freq` <= 21.5 kHz.
- **Analyse** : Ratio énergie HF (16-22 kHz) Silence / Musique.
- **Action** :
  - **Ratio > 0.3** : **+50 points** (Présence de dither artificiel = Transcode).
  - **Ratio < 0.15** : **-50 points** (Silence naturel = Authentique).
  - **Entre 0.15 et 0.3** : **0 point** (Incertain).

## Règle 8 : Exception Nyquist (NOUVELLE)
**Objectif** : Protéger les fichiers avec cutoff proche de la limite théorique (Nyquist = sample_rate / 2).
- **Calcul** : `ratio_nyquist = cutoff_freq / (sample_rate / 2)`
- **Condition de blocage** :
  - Bonus bloqué si signature MP3 détectée (Règle 1) ET (silence_ratio >= 0.15 OU absence d'analyse silence).
  - Bonus autorisé si signature MP3 détectée MAIS silence_ratio < 0.15 (authentique confirmé).
- **Action** :
  - **ratio_nyquist >= 0.98** : **-50 points** (Bonus fort - cutoff à 98%+ de Nyquist).
  - **0.95 <= ratio_nyquist < 0.98** : **-30 points** (Bonus modéré - cutoff à 95-98% de Nyquist).
  - **ratio_nyquist < 0.95** : **0 point** (Pas de bonus).

### Exemples pour 44.1 kHz (Nyquist = 22050 Hz)
- Cutoff 21878 Hz → 99.2% → **-50 points**
- Cutoff 21000 Hz → 95.2% → **-30 points**
- Cutoff 20000 Hz → 90.7% → **0 point**
