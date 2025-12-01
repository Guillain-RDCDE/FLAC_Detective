# PROCHAINES ÉTAPES POUR LES BONNES PRATIQUES PYTHON

Bien que le code ait été considérablement nettoyé et amélioré, voici les étapes restantes pour atteindre un niveau "State of the Art" en matière de développement Python.

## 1. Intégration Continue (CI/CD)

Mettre en place un pipeline automatisé (GitHub Actions) pour vérifier le code à chaque push.

**À implémenter :** `.github/workflows/ci.yml`
- Exécution automatique des tests (`pytest`)
- Vérification du style (`flake8`)
- Vérification des types (`mypy`)
- Vérification de la sécurité (`bandit`)

## 2. Réduction de la Complexité (Refactoring)

Certaines fonctions sont encore trop complexes (Cyclomatic Complexity > 15).

**Cibles prioritaires :**
- `src/flac_detective/analysis/new_scoring.py`: `new_calculate_score` (Complexité: 17) -> Diviser en sous-fonctions par règle.
- `src/flac_detective/reporting/text_reporter.py`: `generate_report` (Complexité: 18) -> Extraire la logique de formatage.
- `src/flac_detective/main.py`: `main` (Complexité: 16) -> Déplacer la logique d'initialisation et de boucle.

## 3. Couverture de Tests (Code Coverage)

Actuellement, seul le nouveau système de scoring est bien testé.

**À faire :**
- Viser > 80% de couverture globale.
- Ajouter des tests pour :
  - `src/flac_detective/analysis/spectrum.py` (Analyse spectrale)
  - `src/flac_detective/analysis/quality.py` (Détection de clipping, silence, etc.)
  - `src/flac_detective/repair/encoding.py` (Réparation de fichiers)

## 4. Documentation Automatisée

Générer un site de documentation à partir des docstrings.

**Outils recommandés :**
- **MkDocs** avec `mkdocs-material` (moderne et simple)
- **Sphinx** (standard industriel)

## 5. Hooks de Pré-commit

Empêcher les commits de code non conforme.

**À configurer :** `.pre-commit-config.yaml`
- `black` ou `ruff` pour le formatage automatique
- `flake8` pour le linting
- `mypy` pour les types
- `isort` pour l'ordre des imports

## 6. Gestion des Dépendances Moderne

Migrer vers un gestionnaire de dépendances plus robuste.

**Suggestion :**
- Utiliser **Poetry** ou **uv** au lieu de `requirements.txt` / `setup.py` pour une gestion déterministe des versions et des environnements virtuels.

---

## ✅ Ce qui a déjà été fait (État actuel)

- [x] **Type Hinting** : Mypy ne signale plus d'erreurs (100% compliant).
- [x] **Structure du Projet** : Dossiers `src/`, `tests/`, `docs/` conformes.
- [x] **Configuration** : `pyproject.toml` présent.
- [x] **Internationalisation** : Code entièrement en anglais (commentaires, logs, docstrings).
- [x] **Linting de base** : Nettoyage des imports inutilisés et des erreurs de formatage majeures.
