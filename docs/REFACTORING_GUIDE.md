# 🔧 Guide de Refactoring - Exemples Concrets

Ce document fournit des exemples de code concrets pour les refactorings prioritaires identifiés dans le rapport d'optimisation.

---

## 1. Refactoring `silence.py` - Extraire Utilitaires Mathématiques

### 📁 Structure Proposée

```
analysis/new_scoring/
├── silence.py              # Logique principale (< 250 lignes)
└── silence_utils.py        # Utilitaires mathématiques (nouveau)
```

### ✂️ Code à Extraire

**Créer `silence_utils.py`:**

```python
"""Mathematical utilities for silence analysis.

This module contains low-level mathematical functions used by the silence
analysis module to detect vinyl noise, clicks, and other audio artifacts.
"""

import numpy as np
from scipy import signal
from typing import Tuple


def filter_band(
    audio_mono: np.ndarray,
    sample_rate: int,
    cutoff_freq: float
) -> np.ndarray:
    """Apply bandpass filter above cutoff frequency.
    
    Args:
        audio_mono: Mono audio data
        sample_rate: Sample rate in Hz
        cutoff_freq: Cutoff frequency in Hz
        
    Returns:
        Filtered audio data
    """
    nyquist = sample_rate / 2
    low = cutoff_freq / nyquist
    high = min(0.99, (sample_rate / 2 - 1000) / nyquist)
    
    if low >= high or low <= 0:
        return np.zeros_like(audio_mono)
    
    sos = signal.butter(4, [low, high], btype='band', output='sos')
    return signal.sosfilt(sos, audio_mono)


def calculate_energy_db(audio_data: np.ndarray) -> float:
    """Calculate RMS energy in dB.
    
    Args:
        audio_data: Audio samples
        
    Returns:
        Energy in dB (relative to full scale)
    """
    rms = np.sqrt(np.mean(audio_data ** 2))
    if rms > 0:
        return 20 * np.log10(rms)
    return -np.inf


def calculate_autocorrelation(
    audio_data: np.ndarray, 
    sample_rate: int, 
    lag: int = 50
) -> float:
    """Calculate autocorrelation at specific lag.
    
    Used to detect random noise (low autocorrelation) vs periodic signals
    (high autocorrelation). Vinyl surface noise is typically random.
    
    Args:
        audio_data: Audio samples
        sample_rate: Sample rate in Hz
        lag: Lag in samples (default: 50)
        
    Returns:
        Autocorrelation coefficient (0.0 to 1.0)
    """
    if len(audio_data) < lag + 1:
        return 0.0
    
    # Normalize
    audio_norm = audio_data - np.mean(audio_data)
    
    # Calculate autocorrelation
    autocorr = np.correlate(audio_norm, audio_norm, mode='full')
    autocorr = autocorr[len(autocorr) // 2:]
    
    if autocorr[0] > 0:
        return autocorr[lag] / autocorr[0]
    return 0.0


def calculate_temporal_variance(
    audio_data: np.ndarray, 
    sample_rate: int
) -> float:
    """Calculate variance of energy across segments.
    
    Musical content has high temporal variance (loud/quiet sections).
    Constant noise has low temporal variance.
    
    Args:
        audio_data: Audio samples
        sample_rate: Sample rate in Hz
        
    Returns:
        Normalized variance (0.0 to 1.0+)
    """
    segment_duration = 0.1  # 100ms segments
    segment_samples = int(segment_duration * sample_rate)
    
    if len(audio_data) < segment_samples * 2:
        return 0.0
    
    # Calculate energy for each segment
    num_segments = len(audio_data) // segment_samples
    energies = []
    
    for i in range(num_segments):
        start = i * segment_samples
        end = start + segment_samples
        segment = audio_data[start:end]
        energy = np.sqrt(np.mean(segment ** 2))
        energies.append(energy)
    
    energies = np.array(energies)
    
    # Calculate normalized variance
    if np.mean(energies) > 0:
        return np.std(energies) / np.mean(energies)
    return 0.0


def detect_transients(
    audio_data: np.ndarray,
    sample_rate: int,
    threshold_factor: float = 3.0
) -> Tuple[int, float]:
    """Detect transient events (clicks, pops) in audio.
    
    Args:
        audio_data: Audio samples
        sample_rate: Sample rate in Hz
        threshold_factor: Multiplier for RMS threshold (default: 3.0)
        
    Returns:
        Tuple of (num_transients, transients_per_minute)
    """
    # Calculate envelope
    window_size = int(0.001 * sample_rate)  # 1ms window
    envelope = np.abs(audio_data)
    envelope = np.convolve(envelope, np.ones(window_size) / window_size, mode='same')
    
    # Calculate threshold
    rms = np.sqrt(np.mean(audio_data ** 2))
    threshold = rms * threshold_factor
    
    # Detect peaks above threshold
    peaks, _ = signal.find_peaks(envelope, height=threshold, distance=window_size * 10)
    
    # Calculate rate
    duration_minutes = len(audio_data) / sample_rate / 60
    transients_per_minute = len(peaks) / duration_minutes if duration_minutes > 0 else 0
    
    return len(peaks), transients_per_minute
```

### 🔄 Modifier `silence.py`

**Avant:**
```python
# silence.py (426 lignes)

def _filter_band(audio_mono, sample_rate, cutoff_freq):
    # ... 20 lignes ...

def _calculate_energy_db(audio_data):
    # ... 3 lignes ...

def _calculate_autocorrelation(audio_data, sample_rate, lag=50):
    # ... 13 lignes ...

def _calculate_temporal_variance(audio_data, sample_rate):
    # ... 17 lignes ...

def detect_vinyl_noise(audio_data, sample_rate, cutoff_freq):
    # ... utilise les fonctions ci-dessus ...
    filtered = _filter_band(audio_mono, sample_rate, cutoff_freq)
    energy = _calculate_energy_db(filtered)
    autocorr = _calculate_autocorrelation(filtered, sample_rate)
    # ...
```

**Après:**
```python
# silence.py (< 300 lignes)

from .silence_utils import (
    filter_band,
    calculate_energy_db,
    calculate_autocorrelation,
    calculate_temporal_variance,
    detect_transients
)

def detect_vinyl_noise(audio_data, sample_rate, cutoff_freq):
    """Detect vinyl surface noise above the musical cutoff (Phase 2).
    
    Args:
        audio_data: Audio samples (mono or stereo)
        sample_rate: Sample rate in Hz
        cutoff_freq: Musical cutoff frequency in Hz
        
    Returns:
        Tuple of (is_vinyl, details_dict)
    """
    # Convert to mono if needed
    if audio_data.ndim > 1:
        audio_mono = np.mean(audio_data, axis=1)
    else:
        audio_mono = audio_data
    
    # Filter above cutoff
    filtered = filter_band(audio_mono, sample_rate, cutoff_freq)
    
    # Calculate metrics
    energy_db = calculate_energy_db(filtered)
    autocorr = calculate_autocorrelation(filtered, sample_rate, lag=50)
    variance = calculate_temporal_variance(filtered, sample_rate)
    
    # Decision logic
    has_energy = energy_db > -70.0
    is_random = autocorr < 0.3
    is_constant = variance < 0.5
    
    is_vinyl = has_energy and is_random and is_constant
    
    details = {
        "energy_db": energy_db,
        "autocorrelation": autocorr,
        "temporal_variance": variance,
        "has_energy": has_energy,
        "is_random": is_random,
        "is_constant": is_constant
    }
    
    return is_vinyl, details
```

**Gain:** 
- ✅ Fichier principal réduit de 426 → ~280 lignes
- ✅ Fonctions mathématiques testables indépendamment
- ✅ Documentation améliorée
- ✅ Réutilisabilité accrue

---

## 2. Refactoring `main.py` - Décomposer `run_analysis_loop()`

### 📊 Avant (111 lignes)

```python
def run_analysis_loop(all_flac_files, all_non_flac_files, output_dir):
    """Run the main analysis loop on the provided files."""
    
    # Load progress
    progress_file = output_dir / "progress.json"
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            progress = json.load(f)
        processed_files = set(progress.get("processed", []))
        results = progress.get("results", [])
    else:
        processed_files = set()
        results = []
    
    # Filter files
    files_to_process = [f for f in all_flac_files if str(f) not in processed_files]
    
    # Progress tracking
    total = len(all_flac_files)
    done = len(processed_files)
    
    # Main loop
    for i, filepath in enumerate(files_to_process, start=done + 1):
        try:
            # Display progress
            print(f"\n[{i}/{total}] Analyzing: {filepath.name}")
            
            # Analyze file
            result = analyze_flac_file(filepath)
            
            # Store result
            results.append(result)
            processed_files.add(str(filepath))
            
            # Save progress every 10 files
            if i % 10 == 0:
                progress_data = {
                    "processed": list(processed_files),
                    "results": results,
                    "timestamp": datetime.now().isoformat()
                }
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(progress_data, f, indent=2)
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Error analyzing {filepath}: {e}")
            results.append({
                "filename": filepath.name,
                "error": str(e),
                "verdict": "ERROR"
            })
    
    # Final save
    progress_data = {
        "processed": list(processed_files),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, indent=2)
    
    return results
```

### ✨ Après (Décomposé)

```python
def run_analysis_loop(all_flac_files, all_non_flac_files, output_dir):
    """Run the main analysis loop on the provided files.
    
    Args:
        all_flac_files: List of FLAC files to analyze
        all_non_flac_files: List of non-FLAC files to report
        output_dir: Directory for saving progress and reports
        
    Returns:
        List of result dictionaries
    """
    tracker = _initialize_progress_tracker(all_flac_files, output_dir)
    
    for filepath in tracker.files_to_process:
        result = _process_single_file(filepath, tracker)
        tracker.add_result(result)
        
        if tracker.should_save_progress():
            tracker.save_progress()
    
    tracker.save_progress()  # Final save
    return tracker.results


def _initialize_progress_tracker(all_files, output_dir):
    """Initialize the progress tracker.
    
    Args:
        all_files: List of all files to process
        output_dir: Directory for progress file
        
    Returns:
        ProgressTracker instance
    """
    progress_file = output_dir / "progress.json"
    
    if progress_file.exists():
        with open(progress_file, "r", encoding="utf-8") as f:
            progress_data = json.load(f)
    else:
        progress_data = {"processed": [], "results": []}
    
    return ProgressTracker(
        all_files=all_files,
        progress_file=progress_file,
        processed_files=set(progress_data.get("processed", [])),
        results=progress_data.get("results", [])
    )


def _process_single_file(filepath, tracker):
    """Process a single FLAC file.
    
    Args:
        filepath: Path to FLAC file
        tracker: ProgressTracker instance
        
    Returns:
        Result dictionary
    """
    try:
        tracker.display_progress(filepath)
        result = analyze_flac_file(filepath)
        return result
        
    except KeyboardInterrupt:
        raise
        
    except Exception as e:
        logger.error(f"Error analyzing {filepath}: {e}")
        return {
            "filename": filepath.name,
            "error": str(e),
            "verdict": "ERROR"
        }


class ProgressTracker:
    """Tracks analysis progress and handles persistence."""
    
    def __init__(self, all_files, progress_file, processed_files, results):
        self.all_files = all_files
        self.progress_file = progress_file
        self.processed_files = processed_files
        self.results = results
        self.current_index = len(processed_files)
        self.save_interval = 10
        
        # Filter files to process
        self.files_to_process = [
            f for f in all_files 
            if str(f) not in processed_files
        ]
    
    def add_result(self, result):
        """Add a result and mark file as processed."""
        self.results.append(result)
        filepath = result.get("filepath", result.get("filename"))
        self.processed_files.add(str(filepath))
        self.current_index += 1
    
    def should_save_progress(self):
        """Check if progress should be saved."""
        return self.current_index % self.save_interval == 0
    
    def save_progress(self):
        """Save current progress to file."""
        progress_data = {
            "processed": list(self.processed_files),
            "results": self.results,
            "timestamp": datetime.now().isoformat()
        }
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f, indent=2)
    
    def display_progress(self, filepath):
        """Display progress message."""
        total = len(self.all_files)
        current = self.current_index + 1
        print(f"\n[{current}/{total}] Analyzing: {filepath.name}")
```

**Gain:**
- ✅ Fonction principale réduite de 111 → 15 lignes
- ✅ Responsabilités clairement séparées
- ✅ Classe `ProgressTracker` réutilisable et testable
- ✅ Gestion d'erreurs isolée

---

## 3. Refactoring `quality.py` - Pattern Strategy

### 🏗️ Structure Proposée

```
analysis/
├── quality.py              # Orchestrateur principal
└── quality_detectors/      # Nouveau package
    ├── __init__.py
    ├── base.py            # Classe de base
    ├── clipping.py        # Détecteur de clipping
    ├── dc_offset.py       # Détecteur de DC offset
    ├── corruption.py      # Détecteur de corruption
    ├── silence.py         # Détecteur de silence
    ├── bit_depth.py       # Détecteur de bit depth
    └── upsampling.py      # Détecteur d'upsampling
```

### 🎯 Classe de Base

**`quality_detectors/base.py`:**

```python
"""Base class for audio quality detectors."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
import numpy as np


class QualityDetector(ABC):
    """Abstract base class for quality detectors."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Detector name for result keys."""
        pass
    
    @abstractmethod
    def detect(self, data: np.ndarray, **kwargs) -> Dict[str, Any]:
        """Perform detection on audio data.
        
        Args:
            data: Audio data (mono or stereo)
            **kwargs: Additional parameters (sample_rate, etc.)
            
        Returns:
            Dictionary with detection results
        """
        pass
    
    def can_detect(self, **kwargs) -> bool:
        """Check if detector can run with given parameters.
        
        Returns:
            True if detector can run, False otherwise
        """
        return True
```

### 🔍 Exemple de Détecteur

**`quality_detectors/clipping.py`:**

```python
"""Clipping detection."""

import numpy as np
from .base import QualityDetector


class ClippingDetector(QualityDetector):
    """Detects audio clipping."""
    
    DEFAULT_THRESHOLD = 0.99
    
    @property
    def name(self) -> str:
        return "clipping"
    
    def detect(self, data: np.ndarray, threshold: float = None, **kwargs):
        """Detect clipping in audio data.
        
        Args:
            data: Audio data (mono or stereo)
            threshold: Clipping threshold (default: 0.99)
            
        Returns:
            Dictionary with clipping results
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD
        
        # Flatten if stereo
        if data.ndim > 1:
            data_flat = data.flatten()
        else:
            data_flat = data
        
        # Detect clipping
        clipped = np.abs(data_flat) >= threshold
        clipped_samples = np.sum(clipped)
        total_samples = len(data_flat)
        clipping_percentage = (clipped_samples / total_samples) * 100
        
        # Determine severity
        if clipping_percentage == 0:
            severity = "none"
        elif clipping_percentage < 0.1:
            severity = "light"
        elif clipping_percentage < 1.0:
            severity = "moderate"
        else:
            severity = "severe"
        
        return {
            "has_clipping": clipped_samples > 0,
            "clipping_percentage": clipping_percentage,
            "clipped_samples": int(clipped_samples),
            "severity": severity
        }
```

### 🎼 Orchestrateur Principal

**`quality.py` (refactoré):**

```python
"""Audio quality analysis orchestrator."""

import logging
from pathlib import Path
from typing import Dict, Any, List
import soundfile as sf

from .quality_detectors import (
    ClippingDetector,
    DCOffsetDetector,
    CorruptionDetector,
    SilenceDetector,
    BitDepthDetector,
    UpsamplingDetector
)

logger = logging.getLogger(__name__)


class AudioQualityAnalyzer:
    """Orchestrates audio quality analysis."""
    
    def __init__(self):
        """Initialize with all detectors."""
        self.detectors = [
            ClippingDetector(),
            DCOffsetDetector(),
            SilenceDetector(),
            BitDepthDetector(),
        ]
        
        # Special detectors (need extra params)
        self.corruption_detector = CorruptionDetector()
        self.upsampling_detector = UpsamplingDetector()
    
    def analyze(
        self, 
        filepath: Path, 
        metadata: Dict = None, 
        cutoff_freq: float = 0.0
    ) -> Dict[str, Any]:
        """Perform complete quality analysis.
        
        Args:
            filepath: Path to audio file
            metadata: File metadata (optional)
            cutoff_freq: Cutoff frequency for upsampling detection
            
        Returns:
            Dictionary with all quality results
        """
        results = {}
        
        # Check corruption first
        corruption_result = self.corruption_detector.detect_from_file(filepath)
        results["corruption"] = corruption_result
        
        if corruption_result["is_corrupted"]:
            logger.warning(f"File is corrupted: {filepath}")
            return self._get_empty_results(results, error_mode=True)
        
        # Load audio data
        try:
            data, samplerate = sf.read(filepath, dtype='float32')
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return self._get_empty_results(results, error_mode=True, error_msg=str(e))
        
        # Run standard detectors
        for detector in self.detectors:
            try:
                result = detector.detect(
                    data=data,
                    samplerate=samplerate,
                    metadata=metadata
                )
                results[detector.name] = result
            except Exception as e:
                logger.error(f"{detector.name} failed: {e}")
                results[detector.name] = {"error": str(e)}
        
        # Run upsampling detector if cutoff provided
        if cutoff_freq > 0:
            upsampling_result = self.upsampling_detector.detect(
                cutoff_freq=cutoff_freq,
                samplerate=samplerate
            )
            results["upsampling"] = upsampling_result
        
        return results
    
    def _get_empty_results(self, results: Dict, error_mode: bool = False, error_msg: str = ""):
        """Generate empty results for all detectors."""
        for detector in self.detectors:
            if detector.name not in results:
                results[detector.name] = detector.get_empty_result(error_mode, error_msg)
        return results


# Convenience function for backward compatibility
def analyze_audio_quality(filepath: Path, metadata: Dict = None, cutoff_freq: float = 0.0):
    """Analyze audio quality (backward compatible function)."""
    analyzer = AudioQualityAnalyzer()
    return analyzer.analyze(filepath, metadata, cutoff_freq)
```

**Gain:**
- ✅ Séparation des responsabilités (SOLID)
- ✅ Chaque détecteur testable indépendamment
- ✅ Facile d'ajouter de nouveaux détecteurs
- ✅ Code plus maintenable et extensible

---

## 4. Nettoyage Automatique - Scripts Pratiques

### 🧹 Script de Nettoyage Complet

**`scripts/cleanup_code.ps1`:**

```powershell
# Script de nettoyage automatique du code Python
# Usage: .\scripts\cleanup_code.ps1

Write-Host "🧹 FLAC Detective - Code Cleanup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# 1. Corriger les espaces blancs
Write-Host "`n📝 Step 1: Fixing whitespace issues..." -ForegroundColor Yellow
autopep8 --in-place --select=W293,W291,W391 src/flac_detective/**/*.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Whitespace fixed" -ForegroundColor Green
} else {
    Write-Host "❌ Whitespace fix failed" -ForegroundColor Red
}

# 2. Supprimer les imports inutilisés
Write-Host "`n📦 Step 2: Removing unused imports..." -ForegroundColor Yellow
autoflake --in-place --remove-unused-variables src/flac_detective/**/*.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Unused imports removed" -ForegroundColor Green
} else {
    Write-Host "❌ Import cleanup failed" -ForegroundColor Red
}

# 3. Corriger les statements multiples
Write-Host "`n🔧 Step 3: Fixing multiple statements on one line..." -ForegroundColor Yellow
autopep8 --in-place --select=E701 src/flac_detective/**/*.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Multiple statements fixed" -ForegroundColor Green
} else {
    Write-Host "❌ Statement fix failed" -ForegroundColor Red
}

# 4. Vérifier les résultats
Write-Host "`n📊 Step 4: Checking results..." -ForegroundColor Yellow
$violations = flake8 src/flac_detective --count
Write-Host "Remaining violations: $violations" -ForegroundColor $(if ($violations -lt 100) { "Green" } else { "Yellow" })

Write-Host "`n✨ Cleanup complete!" -ForegroundColor Cyan
```

### 🧪 Script de Validation

**`scripts/validate_refactoring.ps1`:**

```powershell
# Script de validation après refactoring
# Usage: .\scripts\validate_refactoring.ps1

Write-Host "🧪 FLAC Detective - Refactoring Validation" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# 1. Run tests
Write-Host "`n🔬 Running tests..." -ForegroundColor Yellow
pytest tests/ -v
$test_result = $LASTEXITCODE

# 2. Check code quality
Write-Host "`n📊 Checking code quality..." -ForegroundColor Yellow
flake8 src/flac_detective --max-complexity=10 --count
$flake8_result = $LASTEXITCODE

# 3. Check test coverage
Write-Host "`n📈 Checking test coverage..." -ForegroundColor Yellow
pytest tests/ --cov=src/flac_detective --cov-report=term-missing
$coverage_result = $LASTEXITCODE

# Summary
Write-Host "`n📋 Validation Summary:" -ForegroundColor Cyan
Write-Host "  Tests: $(if ($test_result -eq 0) { '✅ PASS' } else { '❌ FAIL' })"
Write-Host "  Code Quality: $(if ($flake8_result -eq 0) { '✅ PASS' } else { '⚠️  WARNINGS' })"
Write-Host "  Coverage: $(if ($coverage_result -eq 0) { '✅ PASS' } else { '⚠️  LOW' })"

if ($test_result -eq 0 -and $flake8_result -eq 0) {
    Write-Host "`n✅ Refactoring validated successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n⚠️  Some checks failed. Please review." -ForegroundColor Yellow
    exit 1
}
```

---

## 📚 Ressources Supplémentaires

### Outils Recommandés

- **autopep8**: Formatage automatique PEP 8
- **black**: Formatage opinionated
- **autoflake**: Suppression d'imports inutilisés
- **isort**: Tri des imports
- **pylint**: Analyse statique avancée
- **mypy**: Vérification de types

### Commandes Utiles

```bash
# Formater tout le projet avec black
black src/flac_detective/

# Trier les imports
isort src/flac_detective/

# Analyse complète
pylint src/flac_detective/

# Vérification de types
mypy src/flac_detective/
```

---

**💡 Conseil Final:** Toujours exécuter les tests après chaque refactoring pour s'assurer que rien n'est cassé !
