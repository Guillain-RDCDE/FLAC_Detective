# CHANGELOG Automation avec Commitizen

Ce document explique comment utiliser Commitizen pour automatiser la génération du CHANGELOG et gérer les versions.

## Table des matières

- [Introduction](#introduction)
- [Installation](#installation)
- [Conventional Commits](#conventional-commits)
- [Utilisation](#utilisation)
- [Workflow de release](#workflow-de-release)
- [Configuration](#configuration)

## Introduction

FLAC Detective utilise [Commitizen](https://commitizen-tools.github.io/commitizen/) pour:
- Générer automatiquement le CHANGELOG à partir des commits
- Gérer les versions selon le Semantic Versioning
- Enforcer les Conventional Commits via pre-commit hooks

## Installation

```bash
# Installer les dépendances de développement (inclut Commitizen)
pip install -e ".[dev]"

# Installer les pre-commit hooks
pre-commit install --hook-type commit-msg
```

## Conventional Commits

Tous les commits doivent suivre le format [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types de commits

- **feat**: Nouvelle fonctionnalité (bump MINOR)
- **fix**: Correction de bug (bump PATCH)
- **docs**: Documentation uniquement
- **style**: Formatage, espaces, etc. (pas de changement de code)
- **refactor**: Refactoring du code (bump PATCH)
- **perf**: Amélioration de performance (bump PATCH)
- **test**: Ajout ou correction de tests
- **build**: Changements du système de build
- **ci**: Changements de CI/CD
- **chore**: Tâches de maintenance
- **revert**: Annulation d'un commit précédent

### Scopes suggérés

- **analysis**: Système d'analyse FLAC
- **repair**: Fonctionnalité de réparation
- **cli**: Interface en ligne de commande
- **tests**: Tests unitaires/intégration
- **docs**: Documentation
- **rules**: Règles de détection (rule1, rule2, etc.)
- **scoring**: Système de scoring
- **logging**: Système de logs

### Exemples de commits

```bash
# Nouvelle fonctionnalité
git commit -m "feat(analysis): Add support for 24-bit FLAC files"

# Correction de bug
git commit -m "fix(repair): Preserve original file permissions during repair"

# Documentation
git commit -m "docs: Update installation instructions in README"

# Breaking change
git commit -m "feat(cli)!: Change default output format to JSON

BREAKING CHANGE: The default output format is now JSON instead of text.
Use --format=text to get the old behavior."
```

### Aide interactive

Commitizen fournit un assistant interactif pour créer des commits:

```bash
cz commit
```

Cette commande vous guidera à travers toutes les étapes.

## Utilisation

### Générer/Mettre à jour le CHANGELOG

```bash
# Générer le CHANGELOG complet
cz changelog

# Prévisualiser sans créer le fichier
cz changelog --dry-run

# Générer seulement pour les versions non publiées
cz changelog --incremental
```

### Bumper la version

```bash
# Bump automatique basé sur les commits (recommandé)
cz bump

# Bump vers une version spécifique
cz bump --increment MAJOR  # 0.8.0 -> 1.0.0
cz bump --increment MINOR  # 0.8.0 -> 0.9.0
cz bump --increment PATCH  # 0.8.0 -> 0.8.1

# Prévisualiser sans appliquer
cz bump --dry-run
```

La commande `cz bump`:
1. Analyse les commits depuis le dernier tag
2. Détermine le type de bump (MAJOR/MINOR/PATCH)
3. Met à jour les fichiers de version:
   - `pyproject.toml`
   - `src/flac_detective/__init__.py`
4. Génère/met à jour le CHANGELOG
5. Crée un commit de version
6. Crée un tag git

### Créer un commit avec bump et tag

```bash
# Bump + commit + tag + changelog en une seule commande
cz bump --changelog
```

## Workflow de release

### Processus recommandé

1. **Développer et commiter** avec des conventional commits:
   ```bash
   git commit -m "feat(analysis): Add new detection rule"
   git commit -m "fix(cli): Correct output formatting"
   ```

2. **Bumper la version** quand prêt pour une release:
   ```bash
   # Prévisualiser le changelog
   cz changelog --dry-run

   # Bumper la version et générer le changelog
   cz bump --changelog
   ```

3. **Pousser vers GitHub**:
   ```bash
   # Pousser le commit et les tags
   git push && git push --tags
   ```

4. **Le workflow CI/CD se déclenche automatiquement**:
   - Valide que le CHANGELOG contient une entrée pour la version
   - Build le package
   - Teste sur multiple OS/Python versions
   - Publie sur PyPI
   - Crée une GitHub Release avec les notes du CHANGELOG

### Release manuelle (alternative)

Si vous préférez contrôler manuellement:

```bash
# 1. Bumper la version
cz bump --changelog

# 2. Vérifier les changements
git log -1
cat CHANGELOG.md

# 3. Pousser (sans tags)
git push

# 4. Créer le tag manuellement quand prêt
git tag v0.9.0
git push origin v0.9.0
```

## Configuration

### Fichiers de configuration

#### .cz.toml

Configuration détaillée de Commitizen avec:
- Format des tags
- Fichiers de version à mettre à jour
- Structure du changelog
- Règles de validation des commits

#### pyproject.toml

Configuration minimale de Commitizen:
```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.8.0"
tag_format = "v$version"
update_changelog_on_bump = true
version_files = [
    "pyproject.toml:version",
    "src/flac_detective/__init__.py:__version__"
]
```

#### .pre-commit-config.yaml

Le hook Commitizen vérifie automatiquement que tous les commits respectent le format conventional:

```yaml
- repo: https://github.com/commitizen-tools/commitizen
  rev: v4.10.1
  hooks:
    - id: commitizen
      stages: [commit-msg]
```

### Désactiver temporairement le hook

Si vous devez faire un commit qui ne suit pas le format (non recommandé):

```bash
git commit --no-verify -m "Quick fix"
```

## Commandes utiles

```bash
# Vérifier la configuration
cz version

# Voir la version actuelle
cz version --project

# Lister tous les commits depuis le dernier tag
cz changelog --dry-run --unreleased-version "Next"

# Vérifier qu'un message de commit est valide
echo "feat: new feature" | cz check --commit-msg-file -

# Voir l'aide
cz --help
cz bump --help
cz changelog --help
```

## Troubleshooting

### Le hook commitizen rejette mon commit

Assurez-vous que votre message suit le format:
```
type(scope): description courte
```

Types valides: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

### Le CHANGELOG ne contient pas mes commits

Vérifiez que vos commits:
1. Suivent le format conventional
2. Sont entre le dernier tag et HEAD
3. Utilisent des types reconnus (feat, fix, etc.)

### Les versions ne se mettent pas à jour

Vérifiez que les chemins dans `version_files` sont corrects:
```bash
cz bump --dry-run
```

## Ressources

- [Commitizen Documentation](https://commitizen-tools.github.io/commitizen/)
- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
