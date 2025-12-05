# Phase 3 Optimization - FFT Parallelization & Memory 🚀

## 🎯 Objective
Reduce processing time by **10-15%** by parallelizing FFT calculations and optimizing array handling.

## 📊 Technical Strategy

### 1. Parallel FFT (`scipy.fft`)
The `scipy.fft` module supports parallel execution via the `workers` argument or a context manager.
We will implement a global context manager or set the default workers to `-1` (all cores).

**Implementation:**
```python
from scipy import fft

# Inside analysis functions
with fft.set_workers(-1):
    fft_vals = fft.rfft(data_windowed)
```

### 2. Targeted Modules

#### A. `spectrum.py`
- **Function**: `analyze_spectrum`
- **Function**: `analyze_segment_consistency` (via `_analyze_single_segment` if extracted, or inline)
- **Action**: Wrap FFT calls with `set_workers(-1)`.

#### B. `audio_cache.py`
- **Function**: `get_spectrum`
- **Action**: Wrap FFT calls with `set_workers(-1)`.

#### C. `silence.py`
- **Function**: `calculate_spectral_energy`
- **Action**: Wrap FFT calls with `set_workers(-1)`.

## 📝 Implementation Steps

1.  **Modify `spectrum.py`**: Add `set_workers` context manager.
2.  **Modify `audio_cache.py`**: Add `set_workers` context manager.
3.  **Modify `silence.py`**: Add `set_workers` context manager.
4.  **Verification**: Run tests to ensure no regressions.

## 📉 Expected Impact

| Operation | Current | Optimized | Gain |
|-----------|---------|-----------|------|
| FFT (Single Core) | ~10-20ms | ~2-5ms (Multi) | **-75%** (on FFT only) |
| Total Analysis | ~1.0s | ~0.85s | **-15%** |

---
**Status**: Ready to start
