# 🔐 Guide pas à pas : Configurer le secret PyPI sur GitHub

## ⚠️ PROBLÈME ACTUEL

L'erreur `403 Forbidden` signifie que GitHub Actions ne peut pas s'authentifier sur PyPI.

**Cause** : Le secret `PYPI_API_TOKEN` est soit :
- ❌ Mal configuré
- ❌ Invalide
- ❌ Manquant

---

## ✅ SOLUTION EN 3 ÉTAPES

### ÉTAPE 1 : Créer une nouvelle clé API sur PyPI (5 min)

#### 1.1 Connectez-vous à PyPI

🔗 **Allez sur** : https://pypi.org/manage/account/token/

#### 1.2 Créez un nouveau token

1. Cliquez sur le bouton **"Add API token"**

2. Remplissez le formulaire :

   **Token name** :
   ```
   flac-detective-github-actions
   ```

   **Scope** (Portée) :
   - Sélectionnez : **"Project: flac-detective"**
   - ⚠️ Si le projet n'existe pas encore, sélectionnez **"Entire account"**

3. Cliquez sur **"Add token"**

4. **COPIEZ LA CLÉ IMMÉDIATEMENT** ⚠️
   - Elle commence par `pypi-`
   - Elle ressemble à : `pypi-AgEIcHlwaS5vcmcCJD...`
   - **Elle ne sera PLUS JAMAIS affichée !**

---

### ÉTAPE 2 : Configurer le secret sur GitHub (2 min)

#### 2.1 Ouvrez la page des secrets

🔗 **Lien direct** : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions

Ou manuellement :
1. Allez sur https://github.com/GuillainM/FLAC_Detective
2. Cliquez sur **"Settings"**
3. Menu gauche : **"Secrets and variables"** → **"Actions"**

#### 2.2 Vérifiez si le secret existe déjà

- Si vous voyez `PYPI_API_TOKEN` dans la liste :
  1. Cliquez sur **"Update"** à côté
  2. Collez la nouvelle clé
  3. Cliquez sur **"Update secret"**

- Si le secret n'existe pas :
  1. Cliquez sur **"New repository secret"**
  2. Continuez à l'étape 2.3

#### 2.3 Créez le secret

**Name** (EXACTEMENT comme ceci) :
```
PYPI_API_TOKEN
```
⚠️ **Attention** : 
- Tout en MAJUSCULES
- Pas d'espaces
- Exactement ce nom

**Secret** (collez votre clé PyPI) :
```
pypi-AgEIcHlwaS5vcmcCJD...
```
⚠️ **Attention** :
- Collez la clé COMPLÈTE
- Elle doit commencer par `pypi-`
- Ne modifiez rien

Cliquez sur **"Add secret"** ou **"Update secret"**

---

### ÉTAPE 3 : Relancer la publication (1 min)

#### Option A : Via GitHub Actions (RECOMMANDÉ)

1. 🔗 **Allez sur** : https://github.com/GuillainM/FLAC_Detective/actions

2. Cliquez sur **"Publish to PyPI"** dans la liste des workflows

3. Cliquez sur le bouton **"Run workflow"** (en haut à droite)

4. Sélectionnez la branche **"main"**

5. Cliquez sur **"Run workflow"**

6. **Attendez 2-3 minutes** et vérifiez que ça fonctionne

#### Option B : Recréer le tag

Si l'option A ne fonctionne pas, recréez le tag :

```bash
# Supprimer le tag local et distant
git tag -d v0.6.6
git push origin :refs/tags/v0.6.6

# Recréer et pousser le tag
git tag -a v0.6.6 -m "Release v0.6.6"
git push origin v0.6.6
```

---

## ✅ Vérification

### 1. Le secret est-il bien configuré ?

Allez sur : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions

Vous devriez voir :
```
✅ PYPI_API_TOKEN
   Updated X minutes ago
```

### 2. La publication a-t-elle réussi ?

Allez sur : https://github.com/GuillainM/FLAC_Detective/actions

Vous devriez voir :
```
✅ Publish to PyPI
   Completed successfully
```

### 3. Le package est-il sur PyPI ?

Allez sur : https://pypi.org/project/flac-detective/

Vous devriez voir :
```
flac-detective 0.6.6
```

---

## 🧪 Test final

Testez l'installation depuis PyPI :

```bash
# Créer un environnement de test
python -m venv test_pypi
test_pypi\Scripts\activate  # Windows

# Installer depuis PyPI
pip install --upgrade flac-detective

# Vérifier la version
flac-detective --version
# Devrait afficher : 0.6.6

# Tester la commande
flac-detective --help
```

---

## ❓ Questions fréquentes

### Q : J'ai perdu ma clé API PyPI, que faire ?

**R** : Créez-en une nouvelle sur https://pypi.org/manage/account/token/

### Q : Le secret est bien configuré mais ça ne fonctionne toujours pas

**R** : Vérifiez que :
1. Le nom est exactement `PYPI_API_TOKEN` (majuscules)
2. La clé commence par `pypi-`
3. La clé a les permissions pour `flac-detective`
4. Vous avez bien cliqué sur "Update secret"

### Q : Comment savoir si ma clé API est valide ?

**R** : Testez-la localement :
```bash
pip install twine
python -m build
twine upload dist/* --username __token__ --password pypi-VOTRE_CLE
```

---

## 📞 Besoin d'aide ?

Si le problème persiste après avoir suivi ce guide :

1. Vérifiez les logs détaillés : https://github.com/GuillainM/FLAC_Detective/actions
2. Consultez la documentation PyPI : https://pypi.org/help/#invalid-auth
3. Vérifiez que le projet existe : https://pypi.org/project/flac-detective/

---

**Date** : 12 décembre 2025  
**Version** : 0.6.6  
**Objectif** : Publier sur PyPI avec succès ✅
