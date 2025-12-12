# 📦 Préparation PyPI - FLAC Detective v0.6.6

## ✅ Étapes complétées

### 1. Configuration du projet ✅
- [x] Version mise à jour : `0.6.6` dans `pyproject.toml`
- [x] `MANIFEST.in` créé pour inclure tous les fichiers nécessaires
- [x] Workflow GitHub Actions créé : `.github/workflows/publish-pypi.yml`
- [x] Guides de publication créés :
  - `PYPI_SECRET_SETUP.md` - Guide rapide pour configurer le secret
  - `docs/PYPI_PUBLICATION_GUIDE.md` - Guide complet de publication

### 2. Fichiers poussés sur GitHub ✅
- [x] Commit créé : `e6501f9`
- [x] Poussé sur `origin/main`
- [x] Tous les fichiers de configuration disponibles sur GitHub

---

## 🔐 PROCHAINE ÉTAPE CRITIQUE : Configurer le secret GitHub

**⚠️ VOUS DEVEZ FAIRE CECI MAINTENANT pour pouvoir publier sur PyPI**

### Option 1 : Lien direct (RAPIDE)

Cliquez sur ce lien et suivez les instructions :
👉 **https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions/new**

### Option 2 : Navigation manuelle

1. Allez sur https://github.com/GuillainM/FLAC_Detective
2. Cliquez sur **"Settings"**
3. Menu gauche : **"Secrets and variables"** → **"Actions"**
4. Cliquez sur **"New repository secret"**

### Configuration du secret

**Name (Nom)** :
```
PYPI_API_TOKEN
```

**Secret (Valeur)** :
```
pypi-AgEIcHlwaS5vcmcCJDlmMmI0OGY4LTkwZTItNDAzNS04NGYxLWNmYWIwMWRjZGU4ZQACKlszLCI0OGFhOTVhZC01NjFmLTQ4OTUtOGQyOS0yOWNhMzI0OTEyOTkiXQAABiCbVoVEYkYGBOoRTQBhKtbJ
```

Cliquez sur **"Add secret"**

✅ **Fait !** Le secret est maintenant stocké de manière sécurisée.

---

## 🚀 Publication sur PyPI

Une fois le secret configuré, vous avez 2 options :

### Option A : Publication automatique via tag (RECOMMANDÉ)

```bash
# Créer le tag de version
git tag -a v0.6.6 -m "Release v0.6.6 - Automatic retry for FLAC decoder errors"

# Pousser le tag sur GitHub
git push origin v0.6.6
```

**Résultat** :
- GitHub Actions détecte le tag
- Le workflow `publish-pypi.yml` se déclenche automatiquement
- Le package est construit et publié sur PyPI
- Suivez la progression : https://github.com/GuillainM/FLAC_Detective/actions

### Option B : Publication manuelle via GitHub Actions

1. Allez sur https://github.com/GuillainM/FLAC_Detective/actions
2. Cliquez sur **"Publish to PyPI"**
3. Cliquez sur **"Run workflow"**
4. Sélectionnez la branche `main`
5. Cliquez sur **"Run workflow"**

---

## 📊 Vérification après publication

### 1. Vérifier sur PyPI (après quelques minutes)

- **Page du projet** : https://pypi.org/project/flac-detective/
- **Version 0.6.6** : https://pypi.org/project/flac-detective/0.6.6/

### 2. Tester l'installation

```bash
# Créer un environnement de test
python -m venv test_env
test_env\Scripts\activate  # Windows

# Installer depuis PyPI
pip install flac-detective==0.6.6

# Vérifier
flac-detective --version
```

---

## 📋 Checklist complète

### Préparation (FAIT ✅)
- [x] Version 0.6.6 dans pyproject.toml
- [x] CHANGELOG.md à jour
- [x] Documentation complète
- [x] Tests passent
- [x] Code committé et poussé
- [x] Workflow GitHub Actions créé
- [x] Guides de publication créés

### Configuration GitHub (À FAIRE 🔴)
- [ ] Secret `PYPI_API_TOKEN` configuré sur GitHub
  - Nom : `PYPI_API_TOKEN`
  - Valeur : Votre clé API PyPI
  - Lien : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions/new

### Publication (À FAIRE APRÈS LE SECRET 🔴)
- [ ] Tag v0.6.6 créé et poussé
- [ ] Workflow GitHub Actions exécuté avec succès
- [ ] Package visible sur PyPI
- [ ] Installation testée depuis PyPI

---

## 🎯 Commandes rapides

### Après avoir configuré le secret GitHub

```bash
# 1. Créer et pousser le tag
git tag -a v0.6.6 -m "Release v0.6.6 - Automatic retry for FLAC decoder errors"
git push origin v0.6.6

# 2. Suivre la publication
# Ouvrir : https://github.com/GuillainM/FLAC_Detective/actions

# 3. Vérifier sur PyPI (après 2-3 minutes)
# Ouvrir : https://pypi.org/project/flac-detective/0.6.6/

# 4. Tester l'installation
pip install --upgrade flac-detective
flac-detective --version
```

---

## 📚 Documentation

- **Guide rapide** : `PYPI_SECRET_SETUP.md`
- **Guide complet** : `docs/PYPI_PUBLICATION_GUIDE.md`
- **Workflow** : `.github/workflows/publish-pypi.yml`

---

## 🔒 Sécurité

✅ **Votre clé API est en sécurité** :
- Stockée de manière chiffrée sur GitHub
- Jamais visible dans les logs
- Accessible uniquement aux workflows autorisés
- Ne sera JAMAIS committée dans le code

⚠️ **Important** : Ne partagez JAMAIS votre clé API PyPI publiquement ou dans le code source.

---

## ❓ Besoin d'aide ?

### Le workflow échoue ?

1. Vérifiez que le secret est bien nommé `PYPI_API_TOKEN` (sensible à la casse)
2. Vérifiez que la clé API est complète (commence par `pypi-`)
3. Consultez les logs : https://github.com/GuillainM/FLAC_Detective/actions

### Le package n'apparaît pas sur PyPI ?

1. Attendez 2-3 minutes après la fin du workflow
2. Vérifiez qu'il n'y a pas d'erreurs dans les logs GitHub Actions
3. Vérifiez que la version 0.6.6 n'existe pas déjà sur PyPI

---

**Date de préparation** : 12 décembre 2025  
**Version** : 0.6.6  
**Statut** : ✅ Prêt pour publication (après configuration du secret)

---

## 🎉 Résumé

**CE QUI A ÉTÉ FAIT** :
- ✅ Projet configuré pour PyPI
- ✅ Workflow automatique créé
- ✅ Documentation complète
- ✅ Code poussé sur GitHub

**CE QU'IL RESTE À FAIRE** :
1. 🔴 Configurer le secret `PYPI_API_TOKEN` sur GitHub (5 minutes)
2. 🔴 Créer et pousser le tag `v0.6.6` (1 minute)
3. ✅ Attendre que GitHub Actions publie automatiquement (2-3 minutes)

**TEMPS TOTAL ESTIMÉ** : 10 minutes
