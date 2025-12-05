# Plan d'Optimisation - FLAC Detective

Ce document détaille la stratégie d'optimisation pour maximiser les performances de l'outil, en se concentrant sur la parallélisation, la gestion mémoire et l'efficacité algorithmique.

## 1. Architecture Multiprocessus (CPU-Bound)
**Impact : Élevé (vitesse globale)**

Le traitement audio (FFT, filtrage) est intensif pour le CPU. Le *Global Interpreter Lock* (GIL) de Python limite l'efficacité du multithreading actuel (`ThreadPoolExecutor`) pour ces tâches.

* **Problème** : Les threads partagent le même coeur CPU pour l'exécution Python, ne profitant pas pleinement des processeurs modernes.
* **Solution** : Migrer vers `ProcessPoolExecutor` (`multiprocessing`).
* **Implémentation** :
    * Remplacer le pool de threads dans `main.py`.
    * S'assurer que les objets passés aux workers sont sérialisables (pickle).
    * `scipy` gère déjà bien le bas niveau, mais le code glue Python bénéficiera du multiprocessing.

## 2. Optimisation Algorithmique : Silence Analysis
**Impact : Élevé (Règle 7)**

Le module `silence.py` effectue des opérations coûteuses sur l'ensemble des données audio.

* **Problème** : `20 * np.log10(amplitude)` est calculé sur chaque échantillon (des millions). Les fonctions logarithmiques sont lentes.
* **Solution** : Travailler dans le domaine linéaire ou quadratique (énergie).
* **Implémentation** :
    * Convertir le seuil dB en amplitude linéaire une seule fois : `threshold_lin = 10 ** (threshold_db / 20)`.
    * Comparer directement : `audio < threshold_lin`.
    * **Gain** : Suppression de millions d'appels à `log10`.

## 3. Gestion Mémoire (RAM)
**Impact : Moyen (Stabilité)**

L'`AudioCache` charge parfois le fichier entier en mémoire (`get_full_audio`), ce qui est dangereux avec le multiprocessing.

* **Problème** : 10 fichiers FLAC 24/192 décompressés en parallèle peuvent saturer 16+ Go de RAM.
* **Solution** :
    * Utiliser le "Memory Mapping" (`mmap`) supporté par certaines libs ou lire par blocs (streaming) pour la détection de silence.
    * Dans `AudioCache`, ne garder en cache que les segments nécessaires (déjà partiellement fait) et éviter le stockage persistant du fichier entier si non nécessaire.

## 4. Optimisation Vectorielle (Numpy)
**Impact : Faible/Moyen (Micro-optimisation)**

Certaines boucles dans `spectrum.py` (détection cutoff) itèrent manuellement sur des fréquences.

* **Solution** : Vectoriser la détection de cutoff.
* **Implémentation** : Utiliser les opérations matricielles de Numpy pour évaluer toutes les tranches de fréquences simultanément plutôt que dans une boucle `while`.

## 5. Profiling
* Intégrer un outil de profiling simple (decorateur timing) pour mesurer le temps réel passé dans chaque Règle (R1, R7, R11...) et cibler les futurs efforts.
