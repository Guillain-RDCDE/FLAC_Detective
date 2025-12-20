# 🎯 Système de gestion de version centralisée

## ✅ Problème résolu

Avant, la version était éparpillée dans de nombreux fichiers :
- `pyproject.toml`
- `README.md`
- `CHANGELOG.md`
- `docs/README.md`
- `docs/TECHNICAL_DOCUMENTATION.md`
- `docs/RULE_SPECIFICATIONS.md`
- Et bien d'autres...

**Résultat** : Risque d'oubli, incohérences, mises à jour fastidieuses.

---

## 🎯 Solution : Source unique de vérité

### Fichier central : `src/flac_detective/__version__.py`

Ce fichier contient **TOUTE** l'information de version :

```python
__version__ = "0.6.6"
__version_info__ = (0, 6, 6)
__release_date__ = "2025-12-12"
__release_name__ = "Automatic Retry for FLAC Decoder Errors"
```

**C'est le SEUL endroit où vous devez changer la version !**

---

## 🚀 Comment mettre à jour la version

### Méthode simple (3 étapes)

#### 1. Modifier le fichier de version

Éditez `src/flac_detective/__version__.py` :

```python
__version__ = "0.7.0"  # ← Changez ici
__release_date__ = "2025-12-15"  # ← Et ici
__release_name__ = "Nouvelle fonctionnalité"  # ← Et ici
```

#### 2. Exécuter le script de mise à jour

```bash
python scripts/update_version.py
```

**Ce script va automatiquement** :
- ✅ Mettre à jour `pyproject.toml`
- ✅ Mettre à jour `README.md`
- ✅ Mettre à jour tous les fichiers de documentation
- ✅ Afficher un résumé des changements

#### 3. Vérifier et commiter

```bash
# Vérifier les changements
git diff

# Commiter
git add .
git commit -m "chore: Bump version to 0.7.0"

# Créer le tag
git tag -a v0.7.0 -m "Release v0.7.0"

# Pousser
git push && git push --tags
```

---

## 📋 Fichiers mis à jour automatiquement

Le script `scripts/update_version.py` met à jour :

| Fichier | Pattern mis à jour |
|---------|-------------------|
| `pyproject.toml` | `version = "X.X.X"` |
| `README.md` | `v0.X.X`, `Version: 0.X.X` |
| `docs/README.md` | `v0.X.X` |
| `docs/TECHNICAL_DOCUMENTATION.md` | `v0.X.X`, date |
| `docs/RULE_SPECIFICATIONS.md` | `v0.X.X` |

---

## 🔧 Utilisation dans le code Python

Vous pouvez importer la version dans votre code :

```python
from flac_detective.__version__ import __version__, __release_date__

print(f"FLAC Detective v{__version__}")
print(f"Released: {__release_date__}")
```

---

## 📝 CHANGELOG.md

**⚠️ Important** : Le `CHANGELOG.md` doit être mis à jour **manuellement**.

Le script ne le modifie PAS automatiquement car il nécessite :
- Description des changements
- Catégorisation (Added, Changed, Fixed, etc.)
- Contexte et détails

**Template pour CHANGELOG.md** :

```markdown
## [0.7.0] - 2025-12-15

### Added
- Nouvelle fonctionnalité X
- Nouvelle fonctionnalité Y

### Changed
- Amélioration de Z

### Fixed
- Correction du bug W
```

---

## 🎯 Workflow complet de release

### 1. Développement terminé

```bash
# Tous les changements sont committés
git status  # Doit être propre
```

### 2. Mettre à jour la version

```bash
# Éditer src/flac_detective/__version__.py
# Changer __version__, __release_date__, __release_name__

# Exécuter le script
python scripts/update_version.py
```

### 3. Mettre à jour le CHANGELOG

Éditez `CHANGELOG.md` manuellement :

```markdown
## [0.7.0] - 2025-12-15

### Added
- Liste des nouvelles fonctionnalités

### Changed
- Liste des modifications

### Fixed
- Liste des corrections
```

### 4. Commiter et tagger

```bash
# Ajouter tous les changements
git add .

# Commiter
git commit -m "chore: Release v0.7.0"

# Créer le tag
git tag -a v0.7.0 -m "Release v0.7.0 - Description"

# Pousser
git push origin main
git push origin v0.7.0
```

### 5. Publication PyPI (automatique)

Le push du tag déclenche automatiquement GitHub Actions qui :
- ✅ Construit le package
- ✅ Publie sur PyPI
- ✅ Crée une release GitHub

---

## 🔍 Vérification

### Vérifier que tout est cohérent

```bash
# Chercher toutes les occurrences de version
python -c "from flac_detective.__version__ import __version__; print(__version__)"

# Vérifier dans pyproject.toml
grep "version" pyproject.toml

# Vérifier dans README.md
grep -E "v[0-9]+\.[0-9]+\.[0-9]+" README.md
```

Toutes les versions doivent être identiques !

---

## 📚 Avantages du système

### ✅ Avant (problématique)

```
Développeur : "Je veux passer à la version 0.7.0"
→ Modifier pyproject.toml
→ Modifier README.md (ligne 3)
→ Modifier README.md (ligne 265)
→ Modifier README.md (ligne 276)
→ Modifier docs/README.md
→ Modifier docs/TECHNICAL_DOCUMENTATION.md
→ Modifier docs/RULE_SPECIFICATIONS.md
→ Oublier un fichier...
→ Incohérences !
```

### ✅ Après (solution)

```
Développeur : "Je veux passer à la version 0.7.0"
→ Modifier src/flac_detective/__version__.py
→ Exécuter python scripts/update_version.py
→ Terminé ! Tout est cohérent ✅
```

---

## 🛠️ Personnalisation du script

Si vous voulez ajouter d'autres fichiers à mettre à jour, éditez `scripts/update_version.py` :

```python
FILES_TO_UPDATE = {
    "votre_fichier.md": [
        (r'Version: [0-9.]+', f'Version: {__version__}'),
    ],
}
```

---

## 📊 Résumé

| Élément | Emplacement | Action |
|---------|-------------|--------|
| **Version source** | `src/flac_detective/__version__.py` | ✏️ Modifier manuellement |
| **Script de mise à jour** | `scripts/update_version.py` | ▶️ Exécuter |
| **CHANGELOG** | `CHANGELOG.md` | ✏️ Modifier manuellement |
| **Autres fichiers** | Divers | ✅ Mis à jour automatiquement |

---

## 🎉 Résultat

**Une seule source de vérité** → **Cohérence garantie** → **Gain de temps**

Plus besoin de chercher dans tous les fichiers !

---

**Date de création** : 12 décembre 2025  
**Version actuelle** : 0.6.6  
**Statut** : ✅ Opérationnel
