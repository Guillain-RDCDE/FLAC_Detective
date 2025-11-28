# 🎵 FLAC Detective

**Advanced FLAC Authenticity Analyzer & Repair Tool**

> "Every FLAC file tells a story... I find the truth."

FLAC Detective est un outil professionnel pour analyser l'authenticité de vos fichiers FLAC. Il détecte les fichiers "Fake FLAC" (MP3 transcodés) en analysant leur spectre de fréquences et vérifie l'intégrité des métadonnées et de la durée.

## ✨ Fonctionnalités

- **🕵️ Analyse Spectrale Avancée** : Détection de coupures de fréquences (cutoff) typiques des encodeurs MP3 (16kHz, 18kHz, 20kHz).
- **📊 Scoring Intelligent** : Score de confiance (0-100%) basé sur plusieurs critères (spectre, énergie haute fréquence, métadonnées).
- **🔧 Réparation Automatique** : Correction des problèmes de durée (critère "Fakin' The Funk") par ré-encodage sans perte de métadonnées.
- **📑 Rapports Détaillés** : Génération de rapports Excel professionnels avec code couleur et statistiques.
- **🚀 Performance** : Analyse multi-threadée pour traiter rapidement de grandes bibliothèques.

## 🛠️ Installation

### Prérequis
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) (pour l'analyse et la réparation)
- [FLAC](https://xiph.org/flac/) (pour la réparation)

### Installation (Développement)

```bash
# Cloner le repo
git clone https://github.com/votre-repo/flac-detective.git
cd flac-detective

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Installer les dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Pour les tests et le linting
```

## 🚀 Utilisation

### Analyseur (Scanner)

```bash
# Analyser le dossier courant
python -m flac_detective.main

# Le rapport Excel sera généré dans le même dossier.
```

### Réparateur (Fixer)

```bash
# Réparer un fichier spécifique
python -m flac_detective.repair "chemin/vers/fichier.flac"

# Réparer tout un dossier récursivement
python -m flac_detective.repair "chemin/vers/dossier" --recursive

# Simulation (sans modification)
python -m flac_detective.repair "chemin/vers/fichier.flac" --dry-run
```

## 🏗️ Architecture du Code

Le projet suit une architecture modulaire moderne :

- `src/flac_detective/analysis/` : Moteur d'analyse spectrale et scoring.
- `src/flac_detective/repair/` : Module de réparation et ré-encodage.
- `src/flac_detective/reporting/` : Génération des rapports Excel.
- `src/flac_detective/tracker.py` : Gestion de la reprise après interruption.

## 🧪 Qualité et Tests

Le projet respecte les standards de qualité Python :
- **Formatage** : Black & Isort
- **Linting** : Flake8 (0 erreurs)
- **Typage** : Mypy (Strict)
- **Tests** : Pytest (Couverture complète)

Pour lancer les tests :
```bash
pytest tests -v
```

## 📝 Licence

MIT License.
