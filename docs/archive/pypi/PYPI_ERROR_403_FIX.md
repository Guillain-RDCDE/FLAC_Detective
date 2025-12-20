# 🔧 Résolution de l'erreur PyPI 403 Forbidden

## ❌ Erreur rencontrée

```
ERROR HTTPError: 403 Forbidden from https://upload.pypi.org/legacy/
Invalid or non-existent authentication information.
```

## 🔍 Causes possibles

1. **Le secret GitHub n'est pas configuré**
2. **Le nom du secret est incorrect** (sensible à la casse)
3. **La clé API PyPI est invalide ou expirée**
4. **La clé API n'a pas les permissions nécessaires**

---

## ✅ Solution : Vérifier et reconfigurer le secret

### Étape 1 : Vérifier le secret existant

1. Allez sur : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions
2. Vérifiez si le secret `PYPI_API_TOKEN` existe
3. Si oui, supprimez-le et recréez-le

### Étape 2 : Vérifier votre clé API PyPI

**⚠️ IMPORTANT** : Votre clé API doit :
- Commencer par `pypi-`
- Être une clé **d'upload** (pas une clé de lecture seule)
- Avoir les permissions pour le projet `flac-detective`

#### Option A : Utiliser la clé existante

Si vous êtes sûr que votre clé est correcte :
```
pypi-AgEIcHlwaS5vcmcCJDlmMmI0OGY4LTkwZTItNDAzNS04NGYxLWNmYWIwMWRjZGU4ZQACKlszLCI0OGFhOTVhZC01NjFmLTQ4OTUtOGQyOS0yOWNhMzI0OTEyOTkiXQAABiCbVoVEYkYGBOoRTQBhKtbJ
```

#### Option B : Créer une nouvelle clé API (RECOMMANDÉ)

1. Allez sur : https://pypi.org/manage/account/token/
2. Cliquez sur **"Add API token"**
3. Remplissez :
   - **Token name** : `flac-detective-github-actions`
   - **Scope** : 
     - ⚪ Entire account (toute permission)
     - OU
     - 🔘 Project: `flac-detective` (recommandé)
4. Cliquez sur **"Add token"**
5. **COPIEZ LA CLÉ IMMÉDIATEMENT** (elle ne sera plus affichée)

### Étape 3 : Configurer le secret sur GitHub

1. Allez sur : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions/new

2. Remplissez :
   
   **Name** (EXACTEMENT) :
   ```
   PYPI_API_TOKEN
   ```
   ⚠️ Sensible à la casse ! Doit être exactement `PYPI_API_TOKEN`

   **Secret** :
   ```
   pypi-VOTRE_NOUVELLE_CLE_ICI
   ```
   ⚠️ Collez la clé COMPLÈTE (commence par `pypi-`)

3. Cliquez sur **"Add secret"**

---

## 🔄 Relancer la publication

### Option 1 : Via GitHub Actions (RECOMMANDÉ)

1. Allez sur : https://github.com/GuillainM/FLAC_Detective/actions
2. Cliquez sur **"Publish to PyPI"**
3. Cliquez sur **"Run workflow"**
4. Sélectionnez la branche `main`
5. Cliquez sur **"Run workflow"**

### Option 2 : Supprimer et recréer le tag

```bash
# Supprimer le tag local
git tag -d v0.6.6

# Supprimer le tag distant
git push origin :refs/tags/v0.6.6

# Recréer le tag
git tag -a v0.6.6 -m "Release v0.6.6 - Automatic retry for FLAC decoder errors"

# Pousser le nouveau tag
git push origin v0.6.6
```

---

## 🧪 Test local (optionnel)

Pour tester la clé API localement avant de la mettre sur GitHub :

```bash
# Installer twine si nécessaire
pip install twine

# Construire le package
python -m build

# Tester l'upload (avec votre clé)
twine upload dist/* --username __token__ --password pypi-VOTRE_CLE_ICI
```

Si ça fonctionne localement, la clé est valide.

---

## ✅ Checklist de vérification

- [ ] La clé API commence bien par `pypi-`
- [ ] La clé API a les permissions d'upload
- [ ] Le secret GitHub est nommé exactement `PYPI_API_TOKEN`
- [ ] Le secret a été créé/mis à jour récemment
- [ ] Le workflow GitHub Actions utilise bien `${{ secrets.PYPI_API_TOKEN }}`

---

## 📚 Ressources

- **Créer une clé API PyPI** : https://pypi.org/manage/account/token/
- **Configurer les secrets GitHub** : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions
- **Documentation PyPI** : https://pypi.org/help/#invalid-auth

---

## 🆘 Si le problème persiste

### Vérifier le workflow

Le fichier `.github/workflows/publish-pypi.yml` doit contenir :

```yaml
- name: Publish to PyPI
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
  run: |
    twine upload dist/*
```

⚠️ Vérifiez que `TWINE_USERNAME` est bien `__token__` (avec deux underscores)

---

**Date** : 12 décembre 2025  
**Version** : 0.6.6  
**Statut** : En attente de configuration correcte du secret
