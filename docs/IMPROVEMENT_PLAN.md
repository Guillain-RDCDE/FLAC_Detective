# 🎯 Plan d'Amélioration - Best Practices Python

## 📊 Audit Actuel (28/11/2025 - 12:41)

### ✅ Points Forts
- ✅ **Architecture modulaire** : Code bien organisé en packages (`analysis/`, `repair/`, `reporting/`)
- ✅ **Typage strict** : 0 erreurs Mypy
- ✅ **Tests** : 15 tests passent, couverture ~42%
- ✅ **Documentation** : Docstrings complètes (Google style)
- ✅ **Qualité** : Flake8 quasi-propre (2 warnings mineurs)

---

## 🔧 Améliorations Recommandées

### 1. **Complexité Cyclomatique** (Priorité: MOYENNE)
**Problème détecté :**
- `get_user_input_path()` : Complexité = 13 (seuil recommandé : 10)

**Solution :**
```python
# Extraire la logique de parsing en fonctions séparées
def _parse_multiple_paths(user_input: str) -> list[str]:
    """Parse une entrée utilisateur contenant plusieurs chemins."""
    if ";" in user_input:
        return [p.strip() for p in user_input.split(";")]
    elif "," in user_input:
        return [p.strip() for p in user_input.split(",")]
    return [user_input]

def _clean_path_string(path_str: str) -> str:
    """Nettoie les guillemets d'un chemin."""
    if path_str.startswith('"') and path_str.endswith('"'):
        return path_str[1:-1]
    elif path_str.startswith("'") and path_str.endswith("'"):
        return path_str[1:-1]
    return path_str
```

### 2. **Couverture de Tests** (Priorité: HAUTE)
**État actuel :** 42% → **Objectif :** 80%+

**Modules à tester en priorité :**
- `main.py` : 0% couvert (fonction `main()` et `get_user_input_path()`)
- `analysis/metadata.py` : ~23% couvert
- `analysis/scoring.py` : ~8% couvert
- `repair/encoding.py` : ~11% couvert

**Actions :**
- Créer `tests/test_main.py` avec mocks pour `input()` et `sys.argv`
- Augmenter les tests pour `scoring.py` (cas limites : 0Hz, 22kHz, etc.)
- Tester `encoding.py` avec mocks de `subprocess`

### 3. **Gestion d'Erreurs** (Priorité: HAUTE)
**Améliorations possibles :**

```python
# Créer des exceptions personnalisées
class FLACDetectiveError(Exception):
    """Exception de base pour FLAC Detective."""
    pass

class AnalysisError(FLACDetectiveError):
    """Erreur lors de l'analyse."""
    pass

class RepairError(FLACDetectiveError):
    """Erreur lors de la réparation."""
    pass

# Utiliser dans le code
try:
    result = analyzer.analyze_file(filepath)
except AnalysisError as e:
    logger.error(f"Impossible d'analyser {filepath}: {e}")
    # Continuer avec le fichier suivant
```

### 4. **Configuration Centralisée** (Priorité: MOYENNE)
**Problème :** Valeurs magiques dispersées dans le code
- `sample_duration=30.0`
- `max_workers=4`
- `compression_level=5`

**Solution :**
```python
# src/flac_detective/config.py
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration globale de l'application."""
    # Analyse
    SAMPLE_DURATION: float = 30.0
    MAX_WORKERS: int = 4
    SAVE_INTERVAL: int = 50
    
    # Scoring
    AUTHENTIC_THRESHOLD: int = 90
    SUSPECT_THRESHOLD: int = 70
    
    # Repair
    FLAC_COMPRESSION_LEVEL: int = 5
    BACKUP_ENABLED: bool = True
    
    # Spectral
    REFERENCE_FREQ_LOW: int = 10000
    REFERENCE_FREQ_HIGH: int = 14000
```

### 5. **Logging Amélioré** (Priorité: BASSE)
**Améliorations :**
- Ajouter des niveaux de verbosité (`-v`, `-vv`)
- Logger dans un fichier en plus de la console
- Utiliser `structlog` pour des logs structurés (JSON)

```python
# Exemple avec rotation de logs
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    "flac_detective.log",
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
```

### 6. **Performance** (Priorité: BASSE)
**Optimisations possibles :**
- Utiliser `multiprocessing` au lieu de `threading` (GIL Python)
- Ajouter une barre de progression avec `tqdm`
- Cache des résultats spectraux (si même fichier analysé 2x)

### 7. **Interface CLI Professionnelle** (Priorité: BASSE)
**Utiliser `click` ou `typer` :**
```python
import click

@click.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
@click.option('--workers', default=4, help='Nombre de threads')
@click.option('--verbose', '-v', count=True, help='Verbosité')
def main(paths, workers, verbose):
    """Analyse l'authenticité de fichiers FLAC."""
    ...
```

### 8. **Documentation** (Priorité: MOYENNE)
**À ajouter :**
- `CHANGELOG.md` : Historique des versions
- `CONTRIBUTING.md` : Guide pour les contributeurs
- Documentation API avec Sphinx
- Exemples d'utilisation dans `docs/examples/`

---

## 📋 Plan d'Action Recommandé

### Phase 1 : Qualité (1-2h)
1. ✅ Réduire complexité de `get_user_input_path()`
2. ✅ Corriger warnings Flake8
3. ✅ Créer `config.py` centralisé

### Phase 2 : Tests (2-3h)
4. Augmenter couverture à 60%+ (`main.py`, `scoring.py`)
5. Ajouter tests d'intégration end-to-end

### Phase 3 : Robustesse (1-2h)
6. Exceptions personnalisées
7. Gestion d'erreurs améliorée

### Phase 4 : Polish (optionnel)
8. CLI avec `click`
9. Barre de progression
10. Documentation Sphinx

---

## 🎯 Quelle phase vous intéresse ?
Je peux commencer par **Phase 1** (qualité immédiate) si vous voulez maintenir le code au top niveau ?
