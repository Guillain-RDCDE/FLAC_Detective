# 📋 Guide d'Accueil pour Nouveaux Utilisateurs

## Bienvenue! 👋

Vous avez cloné FLAC Detective. Voici comment commencer selon votre profil:

---

## 🚀 Je veux JUSTE l'utiliser rapidement!

**Aucune expérience Python?**
1. Lire: [QUICKSTART.md](QUICKSTART.md) (3 minutes)
2. Vous avez fini? Bravo! 🎉

---

## 👤 Je veux installer et comprendre comment ça fonctionne

1. Lire: [QUICKSTART.md](QUICKSTART.md) - Installation rapide
2. Puis: [README.md](README.md#-installation-guide) - Section "Installation Simple"
3. Puis: [docs/EXAMPLES.md](docs/EXAMPLES.md) - Exemples d'utilisation
4. Puis: [docs/RULES.md](docs/RULES.md) - Comment fonctionne la détection

---

## 👨‍💻 Je veux contribuer / développer

1. Lire: [docs/development/CONTRIBUTING.md](docs/development/CONTRIBUTING.md)
2. Puis: [docs/development/DEVELOPMENT_SETUP.md](docs/development/DEVELOPMENT_SETUP.md)
3. Puis: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Design système
4. Puis: [docs/development/TESTING.md](docs/development/TESTING.md)

---

## 📚 Je veux comprendre les détails techniques

1. Lire: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. Puis: [docs/RULE_SPECIFICATIONS.md](docs/RULE_SPECIFICATIONS.md)
3. Puis: [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md)
4. Puis: [docs/LOGIC_FLOW.md](docs/LOGIC_FLOW.md)

---

## 🆘 Ça ne marche pas!

**Installation:** [README.md#-dépannage-pour-débutants](README.md#-dépannage-pour-débutants)

**Utilisation:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

**Bug?** [GitHub Issues](https://github.com/GuillainM/FLAC_Detective/issues)

---

## 📂 Structure du Projet

```
FLAC_Detective/
├── 📄 QUICKSTART.md          ← START HERE (débutants)
├── 📄 README.md              ← Vue d'ensemble + installation
├── 📄 WELCOME.md             ← Orientation par profil
├── 📄 CHANGELOG.md           ← Historique des versions
│
├── 📁 docs/                  ← Documentation complète
│   ├── 📄 README.md          ← Index des docs
│   ├── 📄 GETTING_STARTED.md ← Installation détaillée
│   ├── 📄 EXAMPLES.md        ← Exemples d'utilisation
│   ├── 📄 RULES.md           ← Règles de détection
│   ├── 📄 TROUBLESHOOTING.md ← Problèmes courants
│   ├── 📄 ARCHITECTURE.md    ← Design système
│   └── 📁 development/       ← Pour contributeurs
│
├── 📁 src/                   ← Code source (implementation)
├── 📁 tests/                 ← Tests unitaires
├── 📁 examples/              ← Exemples de code
└── 📁 scripts/               ← Outils d'exécution
```

---

## ✨ Points d'Entrée Recommandés

| Profil | Point de départ | Temps | Objectif |
|--------|-----------------|-------|----------|
| **Débutant Python** | [QUICKSTART.md](QUICKSTART.md) | 3 min | Installer et utiliser |
| **Utilisateur** | [README.md](README.md) | 10 min | Comprendre avant utiliser |
| **Développeur** | [docs/development/](docs/development/) | 30 min | Setup dev + contribuer |
| **Chercheur** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 1h | Comprendre les algos |

---

## 🎯 Checklist de Premier Lancement

- [ ] Lire [QUICKSTART.md](QUICKSTART.md)
- [ ] Installer Python (si besoin)
- [ ] Installer FLAC Detective (`pip install flac-detective`)
- [ ] Tester: `flac-detective --help`
- [ ] Analyser un dossier: `flac-detective .`
- [ ] Voir les résultats! ✅

---

**Vous êtes prêt! Bon courage! 🎵**
