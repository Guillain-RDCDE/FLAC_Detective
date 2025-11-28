# Rapport d'Audit Flake8 - Flac Detective

**Date**: 27 novembre 2025
**Total d'erreurs**: 80

## 📊 Résumé par Catégorie

### 1. Docstrings (D***) - 68 erreurs
- **D100** (4): Docstring manquante au niveau module
  - `analyzer.py`, `repair.py`, `reporter.py`, `tracker.py`, `utils.py`
- **D107** (2): Docstring manquante dans `__init__`
  - `reporter.py:15`, `tracker.py:13`
- **D200** (1): Docstring sur une ligne doit tenir sur une seule ligne
- **D202** (3): Pas de ligne vide après docstring de fonction
- **D205** (3): 1 ligne vide requise entre résumé et description
- **D212** (21): Résumé multi-ligne doit commencer sur la première ligne
- **D415** (34): Première ligne doit se terminer par un point

### 2. F-strings sans placeholders (F541) - 12 erreurs
- `main.py:70`
- `repair.py`: lignes 139, 264, 273, 277, 296, 298, 305, 307, 316, 328, 332

### 3. Espaces blancs (W293) - 3 erreurs
- `repair.py`: lignes 418, 421, 424

### 4. Complexité (C901) - 1 erreur
- `analyzer.py:320` - `_calculate_score` est trop complexe (17 > 10)

### 5. Bugbear (B008) - 1 erreur
- `tracker.py:13` - Appel de fonction dans valeur par défaut (`Path('progress.json')`)

## 🎯 Plan de Correction Prioritaire

### Priorité 1 - Corrections Automatiques (5 min)

#### A. F-strings inutiles (F541)
Remplacer les f-strings sans placeholders par des strings normaux.

**Fichiers à corriger**:
- `main.py`: ligne 70
- `repair.py`: 11 occurrences

**Exemple**:
```python
# Avant
logger.info(f"Début de l'analyse")

# Après
logger.info("Début de l'analyse")
```

#### B. Espaces blancs (W293)
Nettoyer les lignes blanches avec espaces dans `repair.py`.

**Commande**: Black a déjà dû corriger cela, vérifier manuellement.

### Priorité 2 - Corrections Simples (15 min)

#### A. Docstrings - Points manquants (D415)
Ajouter un point à la fin de chaque première ligne de docstring.

**34 occurrences** dans tous les fichiers.

**Exemple**:
```python
# Avant
"""Analyse un fichier FLAC"""

# Après
"""Analyse un fichier FLAC."""
```

#### B. Docstrings de modules (D100)
Ajouter une docstring en haut de chaque module.

**Fichiers**:
- `analyzer.py`
- `repair.py`
- `reporter.py`
- `tracker.py`
- `utils.py`

**Exemple**:
```python
"""Module d'analyse de fichiers FLAC.

Ce module fournit des outils pour analyser la qualité
des fichiers FLAC et détecter les problèmes potentiels.
"""
```

### Priorité 3 - Corrections Moyennes (30 min)

#### A. Format des docstrings multi-lignes (D212, D205)
Reformater les docstrings multi-lignes selon le style Google.

**24 occurrences**

**Exemple**:
```python
# Avant
def analyze(self, filepath):
    """
    Analyse un fichier FLAC
    Retourne un dictionnaire de résultats
    """

# Après
def analyze(self, filepath):
    """Analyse un fichier FLAC.

    Args:
        filepath: Chemin vers le fichier FLAC.

    Returns:
        Dictionnaire contenant les résultats d'analyse.
    """
```

#### B. Docstrings __init__ (D107)
Ajouter des docstrings aux méthodes `__init__`.

**Fichiers**:
- `reporter.py:15`
- `tracker.py:13`

#### C. Lignes vides après docstring (D202)
Supprimer les lignes vides après les docstrings.

**3 occurrences**

### Priorité 4 - Refactoring (1-2h)

#### A. Complexité cyclomatique (C901)
Refactoriser `FLACAnalyzer._calculate_score` (complexité 17 → <10).

**Stratégies**:
1. Extraire des sous-fonctions
2. Utiliser un dictionnaire de dispatch
3. Simplifier les conditions imbriquées

**Exemple**:
```python
def _calculate_score(self, ...):
    """Calcule le score de qualité."""
    score = self._calculate_base_score(...)
    score = self._apply_format_penalties(score, ...)
    score = self._apply_bitrate_penalties(score, ...)
    return score
```

#### B. Bugbear B008 (tracker.py)
Éviter l'appel de fonction dans les valeurs par défaut.

**Avant**:
```python
def __init__(self, progress_file: Path = Path('progress.json')):
```

**Après**:
```python
def __init__(self, progress_file: Path | None = None):
    if progress_file is None:
        progress_file = Path('progress.json')
```

## 📝 Scripts de Correction Automatique

### Script 1: Corriger les f-strings (F541)
```python
# scripts/fix_fstrings.py
import re
from pathlib import Path

def fix_fstrings(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer f"..." par "..." si pas de {}
    pattern = r'f"([^"]*)"'
    def replace(match):
        text = match.group(1)
        if '{' not in text:
            return f'"{text}"'
        return match.group(0)
    
    content = re.sub(pattern, replace, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Utilisation
for file in ['src/flac_detective/main.py', 'src/flac_detective/repair.py']:
    fix_fstrings(file)
```

### Script 2: Ajouter des points aux docstrings (D415)
```python
# scripts/fix_docstring_periods.py
import re
from pathlib import Path

def fix_docstring_periods(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_docstring = False
    for i, line in enumerate(lines):
        if '"""' in line or "'''" in line:
            if not in_docstring:
                # Première ligne de docstring
                if line.strip().endswith('"""') or line.strip().endswith("'''"):
                    if not line.strip()[-4] in '.?!':
                        lines[i] = line.replace('"""', '."""').replace("'''", ".'''")
                in_docstring = not in_docstring
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
```

## ✅ Checklist de Progression

- [ ] Corriger F541 (f-strings) - 12 occurrences
- [ ] Corriger W293 (espaces blancs) - 3 occurrences
- [ ] Ajouter D100 (docstrings modules) - 5 fichiers
- [ ] Ajouter D107 (docstrings __init__) - 2 occurrences
- [ ] Corriger D415 (points manquants) - 34 occurrences
- [ ] Reformater D212/D205 (format multi-ligne) - 24 occurrences
- [ ] Corriger D202 (lignes vides) - 3 occurrences
- [ ] Refactoriser C901 (complexité) - 1 fonction
- [ ] Corriger B008 (default mutable) - 1 occurrence

## 🎯 Objectif Final
**0 erreurs Flake8** avec configuration stricte.
