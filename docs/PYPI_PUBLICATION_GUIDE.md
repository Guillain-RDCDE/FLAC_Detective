# Guide de publication sur PyPI - FLAC Detective v0.6.6

## 🔐 Configuration du secret GitHub (À FAIRE UNE SEULE FOIS)

### Étape 1 : Ajouter le secret PYPI_API_TOKEN sur GitHub

1. **Allez sur votre dépôt GitHub** :
   https://github.com/GuillainM/FLAC_Detective

2. **Cliquez sur "Settings"** (Paramètres)

3. **Dans le menu de gauche, cliquez sur "Secrets and variables" → "Actions"**

4. **Cliquez sur "New repository secret"**

5. **Remplissez les champs** :
   - **Name** : `PYPI_API_TOKEN`
   - **Secret** : Collez votre clé API PyPI complète
   
   ```
   pypi-AgEIcHlwaS5vcmcCJDlmMmI0OGY4LTkwZTItNDAzNS04NGYxLWNmYWIwMWRjZGU4ZQACKlszLCI0OGFhOTVhZC01NjFmLTQ4OTUtOGQyOS0yOWNhMzI0OTEyOTkiXQAABiCbVoVEYkYGBOoRTQBhKtbJ
   ```

6. **Cliquez sur "Add secret"**

✅ **Le secret est maintenant stocké de manière sécurisée sur GitHub !**

---

## 📦 Publication sur PyPI

### Méthode 1 : Publication automatique via tag Git (RECOMMANDÉ)

Cette méthode utilise GitHub Actions pour publier automatiquement.

```bash
# 1. Assurez-vous que tous les changements sont commités
git status

# 2. Créez un tag de version
git tag -a v0.6.6 -m "Release v0.6.6 - Automatic retry for FLAC decoder errors"

# 3. Poussez le tag sur GitHub
git push origin v0.6.6
```

**Ce qui se passe ensuite :**
- GitHub Actions détecte le nouveau tag
- Le workflow `publish-pypi.yml` se déclenche automatiquement
- Le package est construit et publié sur PyPI
- Vous pouvez suivre la progression dans l'onglet "Actions" de GitHub

---

### Méthode 2 : Publication manuelle depuis GitHub Actions

1. Allez sur : https://github.com/GuillainM/FLAC_Detective/actions
2. Cliquez sur "Publish to PyPI" dans la liste des workflows
3. Cliquez sur "Run workflow"
4. Sélectionnez la branche `main`
5. Cliquez sur "Run workflow"

---

### Méthode 3 : Publication manuelle locale (si nécessaire)

Si vous préférez publier manuellement depuis votre machine :

```bash
# 1. Installer les outils de build
pip install build twine

# 2. Nettoyer les anciennes distributions
rm -rf dist/ build/ *.egg-info

# 3. Construire le package
python -m build

# 4. Vérifier le package
twine check dist/*

# 5. Publier sur PyPI
twine upload dist/*
```

Quand demandé :
- **Username** : `__token__`
- **Password** : Votre clé API PyPI complète

---

## ✅ Vérification de la publication

### 1. Vérifier sur PyPI

Après quelques minutes, vérifiez que le package est disponible :
- **Page du projet** : https://pypi.org/project/flac-detective/
- **Version 0.6.6** : https://pypi.org/project/flac-detective/0.6.6/

### 2. Tester l'installation

```bash
# Créer un environnement virtuel de test
python -m venv test_env
source test_env/bin/activate  # Sur Windows : test_env\Scripts\activate

# Installer depuis PyPI
pip install flac-detective==0.6.6

# Vérifier la version
flac-detective --version

# Tester la commande
flac-detective --help
```

---

## 📋 Checklist avant publication

- [x] Version mise à jour dans `pyproject.toml` (0.6.6)
- [x] CHANGELOG.md mis à jour avec les notes de version
- [x] Documentation complète (README, docs/)
- [x] Tests passent (`pytest`)
- [x] Code committé et poussé sur GitHub
- [x] Secret `PYPI_API_TOKEN` configuré sur GitHub
- [x] Workflow GitHub Actions créé (`.github/workflows/publish-pypi.yml`)
- [ ] Tag de version créé et poussé
- [ ] Publication réussie sur PyPI
- [ ] Installation testée depuis PyPI

---

## 🔧 Dépannage

### Erreur : "Invalid or non-existent authentication information"

**Cause** : Le secret `PYPI_API_TOKEN` n'est pas configuré ou est incorrect.

**Solution** :
1. Vérifiez que le secret est bien nommé `PYPI_API_TOKEN` (sensible à la casse)
2. Vérifiez que la clé API est complète et valide
3. Recréez le secret si nécessaire

### Erreur : "File already exists"

**Cause** : La version 0.6.6 existe déjà sur PyPI.

**Solution** :
1. Incrémentez la version (ex: 0.6.2)
2. Mettez à jour `pyproject.toml`
3. Créez un nouveau tag

### Le workflow ne se déclenche pas

**Cause** : Le tag n'a pas été poussé correctement.

**Solution** :
```bash
# Vérifier les tags locaux
git tag

# Vérifier les tags distants
git ls-remote --tags origin

# Pousser le tag si manquant
git push origin v0.6.6
```

---

## 📚 Ressources

- **Documentation PyPI** : https://packaging.python.org/
- **GitHub Actions** : https://docs.github.com/en/actions
- **Twine** : https://twine.readthedocs.io/

---

## 🎯 Commandes rapides

### Publier une nouvelle version

```bash
# 1. Mettre à jour la version dans pyproject.toml
# 2. Mettre à jour CHANGELOG.md
# 3. Commiter les changements
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Bump version to 0.6.6"
git push

# 4. Créer et pousser le tag
git tag -a v0.6.6 -m "Release v0.6.6"
git push origin v0.6.6

# 5. Attendre que GitHub Actions publie automatiquement
# Suivre sur : https://github.com/GuillainM/FLAC_Detective/actions
```

---

**Date de création** : 12 décembre 2025  
**Version** : 0.6.6  
**Auteur** : Guillain Méjane
