# 🔐 Configuration du Secret PyPI sur GitHub - Guide Rapide

## ⚠️ IMPORTANT : À FAIRE IMMÉDIATEMENT

Votre clé API PyPI doit être stockée de manière sécurisée sur GitHub avant de pouvoir publier le package.

---

## 📋 Étapes à suivre (5 minutes)

### 1. Ouvrez les paramètres de votre dépôt GitHub

🔗 **Lien direct** : https://github.com/GuillainM/FLAC_Detective/settings/secrets/actions

Ou manuellement :
1. Allez sur https://github.com/GuillainM/FLAC_Detective
2. Cliquez sur **"Settings"** (en haut à droite)
3. Dans le menu de gauche, cliquez sur **"Secrets and variables"** → **"Actions"**

---

### 2. Créez un nouveau secret

1. Cliquez sur le bouton vert **"New repository secret"**

2. Remplissez le formulaire :

   **Name (Nom)** :
   ```
   PYPI_API_TOKEN
   ```
   ⚠️ Le nom doit être EXACTEMENT celui-ci (sensible à la casse)

   **Secret (Valeur)** :
   ```
   pypi-AgEIcHlwaS5vcmcCJDlmMmI0OGY4LTkwZTItNDAzNS04NGYxLWNmYWIwMWRjZGU4ZQACKlszLCI0OGFhOTVhZC01NjFmLTQ4OTUtOGQyOS0yOWNhMzI0OTEyOTkiXQAABiCbVoVEYkYGBOoRTQBhKtbJ
   ```
   ⚠️ Copiez-collez la clé COMPLÈTE (commence par `pypi-`)

3. Cliquez sur **"Add secret"**

---

### 3. Vérification

Vous devriez voir :
```
✅ PYPI_API_TOKEN
   Updated X seconds ago
```

---

## 🚀 Après la configuration

Une fois le secret configuré, vous pourrez publier sur PyPI de deux façons :

### Option 1 : Publication automatique (RECOMMANDÉ)

```bash
# Créer et pousser un tag de version
git tag -a v0.6.6 -m "Release v0.6.6"
git push origin v0.6.6
```

GitHub Actions publiera automatiquement le package sur PyPI.

### Option 2 : Publication manuelle via GitHub Actions

1. Allez sur https://github.com/GuillainM/FLAC_Detective/actions
2. Cliquez sur "Publish to PyPI"
3. Cliquez sur "Run workflow"
4. Sélectionnez la branche `main`
5. Cliquez sur "Run workflow"

---

## 🔒 Sécurité

✅ **Le secret est chiffré** : GitHub chiffre automatiquement votre clé API  
✅ **Invisible dans les logs** : La clé ne sera jamais affichée dans les logs  
✅ **Accessible uniquement aux workflows** : Seuls vos workflows GitHub Actions peuvent l'utiliser  

⚠️ **Ne commitez JAMAIS la clé dans le code** : Elle doit rester uniquement dans les secrets GitHub

---

## 📚 Documentation complète

Pour plus de détails, consultez :
- `docs/PYPI_PUBLICATION_GUIDE.md` - Guide complet de publication
- `.github/workflows/publish-pypi.yml` - Workflow GitHub Actions

---

## ❓ Besoin d'aide ?

Si vous rencontrez des problèmes :
1. Vérifiez que le nom du secret est exactement `PYPI_API_TOKEN`
2. Vérifiez que la clé API est complète (commence par `pypi-`)
3. Consultez la documentation PyPI : https://pypi.org/help/

---

**Date** : 12 décembre 2025  
**Version** : 0.6.6
