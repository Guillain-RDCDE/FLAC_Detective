# Plan d'Optimisation Technique - FLAC Detective

## 📊 Analyse des Goulots d'Étranglement

### Problèmes Identifiés

#### 1. **Lectures Multiples de Fichiers** (Impact: 🔴 CRITIQUE)
- `analyze_spectrum()`: Lit 3 segments du fichier (début, milieu, fin)
- `analyze_segment_consistency()`: Lit 2 à 5 segments supplémentaires
- `detect_vinyl_noise()`: Relit le fichier complet
- `analyze_audio_quality()`: Relit le fichier complet
- **Total**: Jusqu'à **10+ lectures** du même fichier!

#### 2. **Calculs FFT Redondants** (Impact: 🟠 ÉLEVÉ)
- Chaque segment analysé recalcule sa FFT
- Pas de réutilisation des spectres déjà calculés
- FFT sur 30 secondes d'audio = ~1.3M samples = coûteux

#### 3. **Conversions Mono Répétées** (Impact: 🟡 MOYEN)
- Chaque fonction convertit stéréo → mono indépendamment
- Pas de cache de la version mono

#### 4. **Windowing Répété** (Impact: 🟡 MOYEN)
- Fenêtre de Hann recalculée à chaque analyse
- Peut être précalculée et réutilisée

---

## 🎯 Plan d'Optimisation en 4 Phases

### **Phase 1: Optimisation du Cache de Fichiers** ⚡ (Gain estimé: 60-70%)

#### Problème
Le système de cache existe mais n'est pas utilisé partout.

#### Solution
```python
# 1. Utiliser AudioCache systématiquement
# Au lieu de:
data, sr = sf.read(filepath, start=start, frames=frames)

# Utiliser:
from .audio_cache import AudioCache
cache = AudioCache(filepath)
data, sr = cache.get_segment(start, frames)
```

#### Fichiers à Modifier
1. ✅ `src/flac_detective/analysis/spectrum.py`
   - `analyze_spectrum()`: Utiliser cache pour les 3 segments
   - `analyze_segment_consistency()`: Utiliser cache pour les 2-5 segments

2. ✅ `src/flac_detective/analysis/new_scoring/silence.py`
   - `detect_vinyl_noise()`: Utiliser cache au lieu de `sf.read()`

3. ✅ `src/flac_detective/analysis/quality.py`
   - `AudioQualityAnalyzer.analyze()`: Utiliser cache

#### Impact Estimé
- **Temps de lecture fichier**: -80% (1 lecture au lieu de 10)
- **Temps total**: -60% à -70%

---

### **Phase 2: Pool de Fenêtres Précalculées** 🔧 (Gain estimé: 5-10%)

#### Problème
```python
# Recalculé à chaque fois:
window = signal.windows.hann(len(data))
```

#### Solution
```python
# Créer un cache de fenêtres
_window_cache = {}

def get_hann_window(size: int) -> np.ndarray:
    """Get cached Hann window."""
    if size not in _window_cache:
        _window_cache[size] = signal.windows.hann(size)
    return _window_cache[size]
```

#### Fichiers à Modifier
1. `src/flac_detective/analysis/spectrum.py`
2. `src/flac_detective/analysis/new_scoring/silence_utils.py`

#### Impact Estimé
- **Temps de windowing**: -90%
- **Temps total**: -5% à -10%

---

### **Phase 3: Optimisation FFT avec NumPy** 🚀 (Gain estimé: 10-15%)

#### Problème
FFT calculée segment par segment sans optimisation.

#### Solution
```python
# 1. Utiliser scipy.fft.rfft avec workers=-1 (parallélisation)
from scipy.fft import rfft, rfftfreq, set_workers

# Au début du programme:
set_workers(-1)  # Utilise tous les CPU disponibles

# 2. Pré-allouer les arrays pour éviter allocations mémoire
def analyze_spectrum_optimized(data, samplerate):
    n = len(data)
    # Pré-allocation
    fft_vals = np.empty(n // 2 + 1, dtype=np.complex128)
    magnitude = np.empty(n // 2 + 1, dtype=np.float64)
    
    # FFT avec plan optimisé
    fft_vals = rfft(data, workers=-1)
    np.abs(fft_vals, out=magnitude)
    
    return magnitude
```

#### Impact Estimé
- **Temps FFT**: -15% à -20%
- **Temps total**: -10% à -15%

---

### **Phase 4: Analyse Progressive Intelligente** 🧠 (Gain estimé: 20-30%)

#### Problème
Certaines analyses sont lancées même si inutiles.

#### Solution: Short-Circuit Intelligent

```python
# 1. Dans new_calculate_score(), ajouter des courts-circuits:

def _apply_scoring_rules(context: ScoringContext) -> Tuple[int, List[str]]:
    # ... existing code ...
    
    # SHORT-CIRCUIT 1: Si score >= 86 après R1+R2+R3
    if context.current_score >= 86:
        logger.info("⚡ FAKE_CERTAIN détecté - Skip R7, R9, R10")
        return context.current_score, context.reasons
    
    # SHORT-CIRCUIT 2: Si score < 0 et pas de MP3 détecté
    if context.current_score < 0 and context.mp3_bitrate_detected is None:
        logger.info("⚡ AUTHENTIC évident - Skip R7, R9, R10")
        return context.current_score, context.reasons
    
    # Continuer avec R7, R9, R10 seulement si nécessaire
```

#### Impact Estimé
- **Fichiers évidents (60%)**: -40% temps (skip R7, R9, R10)
- **Temps total moyen**: -20% à -30%

---

## 📈 Résumé des Gains Estimés

| Phase | Optimisation | Gain Temps | Difficulté | Priorité |
|-------|--------------|------------|------------|----------|
| **1** | Cache Fichiers | **60-70%** | 🟢 Facile | ⭐⭐⭐⭐⭐ |
| **2** | Pool Fenêtres | 5-10% | 🟢 Facile | ⭐⭐⭐ |
| **3** | FFT Optimisée | 10-15% | 🟡 Moyen | ⭐⭐⭐⭐ |
| **4** | Short-Circuits | 20-30% | 🟡 Moyen | ⭐⭐⭐⭐ |
| **TOTAL** | **Cumulé** | **75-85%** | - | - |

### Temps de Traitement Estimé (pour 1000 fichiers)

| Scénario | Avant | Après Phase 1 | Après Toutes Phases |
|----------|-------|---------------|---------------------|
| **Temps/fichier** | 3.0s | 1.0s | 0.5s |
| **Total 1000 fichiers** | 50 min | 17 min | **8 min** |
| **Gain** | - | **-66%** | **-84%** |

---

## 🛠️ Plan d'Implémentation Recommandé

### Semaine 1: Phase 1 (Priorité MAXIMALE)
**Objectif**: Implémenter le cache systématique
- Jour 1-2: Modifier `spectrum.py` pour utiliser `AudioCache`
- Jour 3: Modifier `silence.py` pour utiliser `AudioCache`
- Jour 4: Modifier `quality.py` pour utiliser `AudioCache`
- Jour 5: Tests et validation

**Gain attendu**: **60-70% de réduction du temps**

### Semaine 2: Phases 2 + 3
**Objectif**: Optimisations FFT et windowing
- Jour 1-2: Implémenter pool de fenêtres
- Jour 3-4: Optimiser FFT avec parallélisation
- Jour 5: Tests et validation

**Gain attendu**: **+15-25% supplémentaire**

### Semaine 3: Phase 4
**Objectif**: Short-circuits intelligents
- Jour 1-3: Implémenter logique de court-circuit
- Jour 4-5: Tests et validation

**Gain attendu**: **+20-30% supplémentaire**

---

## 🔍 Optimisations Supplémentaires (Optionnel)

### A. Utiliser `numba` pour les Boucles Critiques
```python
from numba import jit

@jit(nopython=True)
def detect_cutoff_fast(frequencies, magnitude_db):
    # Version compilée JIT = 10x plus rapide
    ...
```
**Gain**: +10-20% sur les calculs intensifs

### B. Batch Processing avec `multiprocessing`
```python
# Analyser plusieurs fichiers en parallèle
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(analyze_file, file_list)
```
**Gain**: 3-4x sur machines multi-core

### C. Utiliser `mmap` pour Gros Fichiers
```python
import mmap

# Pour fichiers > 100 MB
with open(filepath, 'rb') as f:
    with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped:
        # Lecture ultra-rapide
        ...
```
**Gain**: +30-40% sur gros fichiers

---

## ✅ Checklist de Validation

Après chaque phase:
- [ ] Tests unitaires passent
- [ ] Résultats identiques à la version précédente
- [ ] Mesure du temps d'exécution (avant/après)
- [ ] Profiling mémoire (pas d'augmentation)
- [ ] Tests sur 100 fichiers variés

---

## 📊 Métriques à Suivre

```python
# Ajouter un système de profiling
import time
import functools

def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        logger.info(f"⏱️ {func.__name__}: {end-start:.3f}s")
        return result
    return wrapper

# Utiliser sur fonctions critiques:
@profile
def analyze_spectrum(filepath, sample_duration):
    ...
```

---

## 🎯 Objectif Final

**Réduire le temps de traitement de 75-85% sans perte de qualité**

- ✅ Même précision de détection
- ✅ Même qualité de résultats
- ✅ Code plus maintenable
- ✅ Utilisation mémoire contrôlée

**Temps cible**: **< 0.5 seconde par fichier** (vs 3 secondes actuellement)
