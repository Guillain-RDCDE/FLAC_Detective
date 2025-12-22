# 🎵 WAV to FLAC Converter - Guide d'Utilisation

## 🚀 Utilisation Simple

### Conversion Basique

```bash
# Convertir tous les WAV du dossier actuel
python3 wav_to_flac.py .

# Convertir tous les WAV d'un dossier spécifique
python3 wav_to_flac.py /chemin/vers/dossier

# Windows
python3 wav_to_flac.py "C:\Music\Album"
```

### Avec Options

```bash
# Recherche récursive (sous-dossiers inclus)
python3 wav_to_flac.py /chemin/vers/music --recursive

# Compression maximale (plus lent, fichiers plus petits)
python3 wav_to_flac.py /chemin/vers/music --level 8

# Supprimer les WAV après conversion
python3 wav_to_flac.py /chemin/vers/music --delete-wav

# Sans vérification d'intégrité (plus rapide)
python3 wav_to_flac.py /chemin/vers/music --no-verify

# Combinaison d'options
python3 wav_to_flac.py /music --recursive --level 8 --delete-wav
```

## 📋 Options Disponibles

| Option | Description | Défaut |
|--------|-------------|--------|
| `directory` | Répertoire contenant les WAV | *Requis* |
| `-r, --recursive` | Chercher dans les sous-dossiers | Non |
| `-l, --level` | Niveau compression (0-8) | 5 |
| `--no-verify` | Ne pas vérifier l'intégrité | Vérification activée |
| `--delete-wav` | Supprimer les WAV après conversion | Non |

## 🔧 Niveaux de Compression

| Niveau | Vitesse | Taille | Utilisation |
|--------|---------|--------|-------------|
| **0** | ⚡⚡⚡ Très rapide | 📦📦📦 Plus gros | Tests rapides |
| **5** | ⚡⚡ Rapide | 📦📦 Moyen | **Recommandé** ✅ |
| **8** | ⚡ Lent | 📦 Plus petit | Archivage |

**Note :** Tous les niveaux produisent du FLAC **lossless** (qualité identique).

## 📊 Exemple de Sortie

```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              🎵 WAV → FLAC Converter 🎵                   ║
║                                                           ║
║          Simple batch converter using official           ║
║                    FLAC encoder                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

✅ flac 1.4.3

🔍 Recherche des fichiers WAV dans: /music/album

✅ 12 fichier(s) WAV trouvé(s)

📋 Paramètres de conversion:
   • Niveau compression: 5
   • Vérification intégrité: Oui
   • Supprimer WAV: Non

================================================================================
🔄 DÉBUT DE LA CONVERSION
================================================================================

[1/12] Track 01.wav
        Taille WAV: 45.2 MB
        ✅ Converti
        Taille FLAC: 28.3 MB (62.6% du WAV)

[2/12] Track 02.wav
        Taille WAV: 52.1 MB
        ✅ Converti
        Taille FLAC: 32.7 MB (62.8% du WAV)

...

================================================================================
✅ CONVERSION TERMINÉE
================================================================================

📊 Statistiques:
   • Fichiers convertis: 12
   • Fichiers ignorés: 0
   • Erreurs: 0
   • Temps total: 45.3 secondes

💾 Taille totale:
   • WAV:  512.4 MB
   • FLAC: 321.8 MB
   • Ratio: 62.8%
   • Économie: 190.6 MB (37.2%)

⚡ Temps moyen par fichier: 3.8s
```

## ⚠️ Sécurité

### Fichiers Protégés

- ✅ Le script **ne modifie jamais** les fichiers WAV originaux (sauf si `--delete-wav`)
- ✅ Si un fichier FLAC existe déjà, il est **ignoré** (pas d'écrasement)
- ✅ Chaque conversion inclut une **vérification d'intégrité** par défaut

### Option --delete-wav

**ATTENTION** : Cette option supprime définitivement les WAV !

```bash
python3 wav_to_flac.py /music --delete-wav
```

**Le script demande confirmation :**
```
⚠️  ATTENTION: Les fichiers WAV seront SUPPRIMÉS après conversion !
   Continuer ? (oui/non):
```

**Recommandation :** Testez d'abord **sans** `--delete-wav`, vérifiez les FLAC, puis relancez avec cette option si tout est OK.

## 🎯 Cas d'Usage Typiques

### 1. Album CD Rippé

```bash
# Vous avez rippé un CD en WAV
cd "/music/Nouvel Album (WAV)"
python3 wav_to_flac.py . --level 8

# Vérifier les FLAC générés
# Puis supprimer les WAV manuellement si OK
```

### 2. Bibliothèque Complète

```bash
# Convertir toute une arborescence
python3 wav_to_flac.py /music/collection --recursive --level 5

# Économie d'espace typique: 30-40%
```

### 3. Conversion + Nettoyage

```bash
# Convertir et supprimer les WAV en une passe
# ⚠️ SEULEMENT si vous êtes sûr !
python3 wav_to_flac.py /music/temp --recursive --delete-wav
```

### 4. Conversion Rapide (Tests)

```bash
# Pour tester rapidement
python3 wav_to_flac.py /music/test --level 0 --no-verify
```

## 🐛 Dépannage

### Erreur "flac not found"

```bash
# Linux/Ubuntu
sudo apt install flac

# macOS
brew install flac

# Windows
# Télécharger depuis https://xiph.org/flac/download.html
# Ajouter au PATH
```

### Vérifier l'installation

```bash
flac --version
# Doit afficher: flac 1.x.x
```

### Conversion très lente

```bash
# Utiliser niveau de compression plus bas
python3 wav_to_flac.py /music --level 3

# Ou sans vérification
python3 wav_to_flac.py /music --no-verify
```

### "Permission denied"

```bash
# Vérifier les permissions du dossier
ls -la /music

# Ou exécuter avec sudo (Linux/macOS)
sudo python3 wav_to_flac.py /music
```

## 📈 Performances Attendues

### Vitesse de Conversion

**Sur un ordinateur moderne (CPU i5/i7) :**

| Niveau | MB/seconde | Fichier 50 MB |
|--------|------------|---------------|
| 0 | ~40 MB/s | ~1.3s |
| 5 | ~15 MB/s | ~3.3s |
| 8 | ~8 MB/s | ~6.3s |

### Taille des Fichiers

**Ratio FLAC/WAV typique :**

| Type de Musique | Ratio | Exemple WAV→FLAC |
|-----------------|-------|------------------|
| Classique/Jazz | 55-65% | 50 MB → 28-32 MB |
| Rock/Pop | 60-70% | 50 MB → 30-35 MB |
| Électronique | 65-75% | 50 MB → 32-37 MB |

**Économie d'espace :** 25-45% en moyenne

## 🔍 Vérification Post-Conversion

### Tester l'intégrité

```bash
# Tester un fichier FLAC
flac -t fichier.flac

# Tester tous les FLAC d'un dossier
flac -t *.flac
```

### Comparer avec l'original

```bash
# Décoder le FLAC en WAV temporaire
flac -d fichier.flac -o temp.wav

# Comparer les MD5
md5sum original.wav temp.wav

# Nettoyer
rm temp.wav
```

### Avec FLAC Detective

```bash
# Analyser les FLAC générés
python3 flac_detective_v4.1.py

# Les fichiers convertis depuis WAV doivent avoir:
# • Score: 100% ✅
# • Raison: "Spectre complet jusqu'à 22050 Hz"
# • Aucun problème détecté
```

## 💡 Astuces

### Conversion Progressive

```bash
# Convertir album par album
for dir in /music/*/; do
    echo "Conversion: $dir"
    python3 wav_to_flac.py "$dir"
done
```

### Statistiques Uniquement

```bash
# Voir combien de WAV sans convertir
python3 wav_to_flac.py /music --recursive
# Puis Ctrl+C avant la confirmation
```

### Backup Avant Suppression

```bash
# 1. Convertir
python3 wav_to_flac.py /music --recursive

# 2. Vérifier les FLAC
flac -t /music/**/*.flac

# 3. Backup des WAV
tar -czf backup_wav.tar.gz /music/**/*.wav

# 4. Reconvertir avec suppression
python3 wav_to_flac.py /music --recursive --delete-wav
```

## 📝 Notes Techniques

### Format WAV Supporté

- ✅ PCM 16 bits (CD quality)
- ✅ PCM 24 bits (HD audio)
- ✅ 44.1 kHz, 48 kHz, 96 kHz, 192 kHz
- ✅ Mono et Stéréo

### Format FLAC Généré

- ✅ **Lossless** (qualité identique au WAV)
- ✅ Métadonnées préservées (si présentes dans WAV)
- ✅ Vérification MD5 intégrée
- ✅ Compatible tous lecteurs FLAC

### Différence avec Transcodage MP3→FLAC

**WAV→FLAC (ce script) :**
```
WAV (lossless) → FLAC (lossless)
✅ Qualité préservée à 100%
✅ Score FLAC Detective: 100%
```

**MP3→FLAC (à éviter) :**
```
MP3 (lossy) → FLAC (lossy dans conteneur lossless)
❌ Qualité limitée au MP3 original
❌ Score FLAC Detective: 20-60% (détecté comme fake)
```

## 🎓 Exemples Complets

### Exemple 1 : Album Simple

```bash
cd "/music/Pink Floyd - Dark Side of the Moon (WAV)"

python3 wav_to_flac.py . --level 5

# Résultat attendu:
# 10 fichiers WAV → 10 fichiers FLAC
# ~40% d'économie d'espace
# Qualité identique (lossless)
```

### Exemple 2 : Collection Complète

```bash
python3 wav_to_flac.py "/music/FLAC Masters" --recursive --level 8

# Peut prendre plusieurs heures selon la taille
# Utilise le niveau 8 pour archivage long terme
```

### Exemple 3 : Workflow Professionnel

```bash
# 1. Ripper le CD en WAV (avec EAC, dBpoweramp, etc.)
# 2. Convertir en FLAC
python3 wav_to_flac.py /rip/cd --level 8

# 3. Vérifier avec FLAC Detective
python3 flac_detective_v4.1.py

# 4. Si tout est OK, supprimer les WAV
rm /rip/cd/*.wav
```

## 🆚 Comparaison Outils

| Outil | GUI | Batch | Vérification | Gratuit |
|-------|-----|-------|--------------|---------|
| **Ce script** | ❌ | ✅ | ✅ | ✅ |
| dBpoweramp | ✅ | ✅ | ✅ | ❌ ($) |
| foobar2000 | ✅ | ✅ | ⚪ | ✅ |
| Audacity | ✅ | ❌ | ❌ | ✅ |

**Avantage de ce script :** Simple, rapide, automatisé, 100% gratuit.

## ✅ Checklist

Avant de lancer la conversion :

- [ ] Outil `flac` installé (`flac --version`)
- [ ] Fichiers WAV disponibles
- [ ] Espace disque suffisant (~60% de la taille WAV)
- [ ] Niveau de compression choisi
- [ ] Décidé si supprimer WAV ou non
- [ ] Backup fait si `--delete-wav`

---

**WAV to FLAC Converter**
*Simple, rapide, fiable - Conversion lossless garantie*
