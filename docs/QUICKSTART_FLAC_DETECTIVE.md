# 🚀 FLAC Detective - Quick Start Guide

```
🔍 FLAC DETECTIVE v4.0
"Every FLAC file tells a story... I find the truth"
```

---

## ⚡ Installation Rapide (2 minutes)

### 1. Téléchargez les 4 fichiers essentiels

- ✅ **flac_detective.py** (analyseur principal)
- ✅ **flac_detective_test.py** (test unitaire)
- ✅ **flac_detective_repair.py** (réparateur)
- ✅ **flac_detective_helper.py** (assistant interactif)

### 2. Installez l'outil FLAC officiel

**Windows:**
- Téléchargez depuis https://xiph.org/flac/download.html
- Décompressez et ajoutez au PATH

**Linux/Ubuntu:**
```bash
sudo apt install flac
```

**macOS:**
```bash
brew install flac
```

### 3. Vérifiez l'installation

```bash
flac --version
```

✅ Si vous voyez la version → C'est bon !

---

## 🎯 Premier Test (30 secondes)

### Testez sur UN fichier

```bash
python3 flac_detective_test.py "E:\Music\votre_fichier.flac"
```

**Vous verrez :**
```
🔍 FLAC DETECTIVE v4.0

🎵 ANALYSE DÉTAILLÉE : votre_fichier.flac
================================================================================

📋 MÉTADONNÉES
  Sample Rate    : 44100 Hz
  Bit Depth      : 16 bits
  Duration       : 249.1 secondes

⏱️  VÉRIFICATION DURÉE
  Statut         : ✅ OK (tolérance normale)

🔬 ANALYSE SPECTRALE (3 échantillons)
  Coupure        : 22050 Hz
  Énergie >16kHz : 0.000009

🎯 VERDICT
  Score: 95% 🟢
  Raison: Spectre complet jusqu'à 22050 Hz | Contenu ultra-aigu minimal
  
  ✅ FLAC AUTHENTIQUE - Très probablement lossless d'origine
```

**Score ≥90% ?** → Votre fichier est authentique ! ✅

---

## 📊 Analyse Complète (pour 80 000 fichiers)

### Lancez l'analyse

```bash
cd E:\Music
python3 flac_detective.py
```

**Ce qui se passe :**
1. 🔍 Scan de tous les fichiers .flac
2. 📊 Analyse de 4 critères par fichier
3. 💾 Sauvegarde tous les 50 fichiers
4. 📄 Génération du rapport texte final

**Temps estimé :** 8-15 heures pour 80 000 fichiers

### Interruption possible !

- **Interrompre :** `Ctrl+C`
- **Reprendre :** Relancez simplement le script
- **Tout recommencer :** `del progress.json` puis relancez

---

## 📈 Rapport Texte Généré

**Fichier :** `rapport_flac_YYYYMMDD_HHMMSS.txt`

### Section "Résumé"

```
RAPPORT D'ANALYSE FLAC
================================================================================
Fichiers analysés:                  80,000
Authentiques (90-100%):             74,200  (92.8%)
Probablement authentiques (70-89%):  1,100  (1.4%)
Suspects (50-69%):                   3,850  (4.8%)
Très suspects (<50%):                  850  (1.1%)

PROBLÈMES DE DURÉE
Fichiers avec décalage durée:        1,280  (1.6%)
Décalage critique (>1 seconde):        160  (0.2%)
```

### Section "Fichiers Suspects"

Contient UNIQUEMENT les fichiers < 90% avec :
- Chemin complet
- Score avec code couleur 🟢🟡🟠🔴
- Raison détaillée
- Fréquence de coupure
- **Problème Durée** (nouveau !)
- Métadonnées complètes

---

## 🔧 Réparation des Problèmes

### Réparer un fichier

**1. Test en simulation :**
```bash
python3 flac_detective_repair.py "fichier.flac" --dry-run
```

**2. Réparation réelle :**
```bash
python3 flac_detective_repair.py "fichier.flac"
```

**Résultat :**
- ✅ Fichier réparé
- 💾 Backup créé (`.bak`)
- 📋 Toutes les métadonnées préservées
- 🖼️ Tous les artworks préservés

### Réparer un album complet

```bash
python3 flac_detective_repair.py "E:\Music\Album\" --recursive
```

---

## 🎓 Interprétation des Scores

| Score | Signification | Action |
|-------|--------------|--------|
| **95-100%** | Excellent, authentique | ✅ Rien à faire |
| **90-94%** | Authentique | ✅ OK |
| **70-89%** | Probablement authentique | ⚠️ Vérifier si critique |
| **50-69%** | Suspect | 🔍 Vérification manuelle |
| **0-49%** | Très suspect | ❌ Supprimer/remplacer |

### Exemples Courants

**Score 95% - Musique électronique**
```
Raison: Spectre complet 22kHz | Contenu ultra-aigu minimal (mastering)
→ ✅ NORMAL pour ce style musical
```

**Score 20% - MP3 transcodé**
```
Raison: Coupure 18kHz (MP3 192k) | Absence énergie >16kHz
→ ❌ FAUX FLAC, c'est un MP3 déguisé
```

**Score 80% - Métadonnées corrompues**
```
Raison: Spectre complet | Durée incohérente (2000ms)
→ ⚠️ RÉPARABLE avec flac_detective_repair.py
```

---

## 🎯 Workflow Complet (3 Étapes)

### ÉTAPE 1 : ANALYSE
```bash
python3 flac_detective.py
```
→ Génère rapport texte

### ÉTAPE 2 : TRIER
1. Ouvrez le rapport texte
2. Recherchez les fichiers avec un score faible
3. Repérez "Problème Durée" ≠ "✓ OK"
4. Notez les fichiers à traiter

### ÉTAPE 3 : ACTIONS

**Pour les scores < 50% :**
```bash
# Supprimer les faux FLAC
del "fichier_fake.flac"
```

**Pour les problèmes de durée :**
```bash
# Réparer
python3 flac_detective_repair.py "fichier.flac"
```

**Pour les scores 50-89% :**
```bash
# Vérifier manuellement avec
python3 flac_detective_test.py "fichier.flac"
```

---

## 💡 Assistant Interactif

**Pour les débutants, utilisez l'assistant :**

```bash
python3 flac_detective_helper.py
```

**Menu guidé :**
1. 📖 Workflow complet
2. 💡 Exemples pratiques
3. ⚠️ Notes importantes
4. 🔧 Lancer l'analyse
5. 🛠️ Réparer un fichier
6. 📁 Réparer un dossier

---

## ⚠️ Points Importants

### Backups Automatiques

Lors de la réparation, un fichier `.bak` est créé :
```
fichier.flac
fichier.flac.bak  ← Backup automatique
```

**Après vérification :**
```bash
# Supprimer les backups
del *.bak
```

### Temps de Traitement

**Analyse :**
- 1 fichier : ~3-7 secondes
- 1 000 fichiers : ~1-2 heures
- 80 000 fichiers : ~8-15 heures

**Réparation :**
- 1 fichier : ~5-15 secondes
- 1 album (10 tracks) : ~2-3 minutes

### Espace Disque

**Pendant la réparation :**
- Backup = taille originale
- Fichier temporaire WAV = ~10x la taille FLAC

**Exemple :** Fichier FLAC 30 MB
- Backup : 30 MB
- Temporaire : 300 MB (supprimé après)

---

## 🆘 Problèmes Courants

**Erreur "flac not found"**
→ Installez l'outil FLAC (voir Étape 2)

**Le script trouve 0 fichiers**
→ Vérifiez que vous êtes dans le bon dossier

**Tous les fichiers à 100%**
→ Bonne nouvelle, votre bibliothèque est propre !

**Musique électronique à 75%**
→ Normal ! Le script v4.0 est intelligent et adapte les scores

**Erreur Python**
→ Vérifiez Python 3.7+ : `python3 --version`

---

## 📚 Documentation Complète

**Fichiers disponibles :**

- **README_FLAC_DETECTIVE.md** - Documentation complète (EN)
- **README_FINAL.md** - Guide d'utilisation (FR)
- **GUIDE_REPARATION.md** - Guide réparation détaillé
- **CHANGELOG_v4.md** - Détails techniques v4

---

## 🎯 Checklist Rapide

- [ ] Outil `flac` installé (`flac --version`)
- [ ] 4 fichiers Python téléchargés
- [ ] Test sur 1 fichier réussi
- [ ] Analyse complète lancée
- [ ] Rapport texte généré
- [ ] Fichiers suspects identifiés
- [ ] Réparations effectuées (si nécessaire)
- [ ] Vérification finale OK

---

## 🏆 Résultat Final

**Après analyse + réparation :**

✅ Bibliothèque nettoyée des faux FLAC  
✅ Problèmes de durée réparés  
✅ Rapport professionnel généré  
✅ Métadonnées préservées à 100%  

**Votre bibliothèque musicale est maintenant certifiée authentique !** 🎵

---

```
🔍 FLAC DETECTIVE v4.0
"Every FLAC file tells a story... I find the truth"

Version 4.0 - November 2025
Hunting Down Fake FLACs Since 2025
```
