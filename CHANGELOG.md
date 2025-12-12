# Changelog

All notable changes to FLAC Detective will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.7] - 2025-12-12

### Changed
- **Performance Optimization**: Switched from multi-threading to **multi-processing** (ProcessPoolExecutor).
  - Bypasses Python GIL for true parallel analysis on all CPU cores.
  - Significant speedup on large datasets.
- **Reporting**:
  - Improved console log aesthetics with colored verdicts and aligned columns.
  - Removed unused Excel reporting module (`openpyxl` dependency removed).
  - Removed unused `matplotlib` dependency.
- **Cleanup**: Cleaned up internal threading in spectral analysis to avoid thread over-subscription.

## [0.6.6] - 2025-12-12

### Added
- **Automatic Retry Mechanism for FLAC Decoder Errors**
  - New `audio_loader.py` module with `load_audio_with_retry()` function
  - Automatic retry (max 3 attempts) for temporary decoder errors
  - Exponential backoff: 0.2s → 0.3s → 0.45s between retries
  - Detects temporary errors: "lost sync", "decoder error", "sync error", "invalid frame", "unexpected end"
  - Detailed logging: "⚠️ Temporary error on attempt X", "✅ Audio loaded successfully on attempt X"

### Changed
- **Rule 9 (Compression Artifacts)**
  - Now uses `load_audio_with_retry()` instead of direct `sf.read()`
  - Returns 0 points (no penalty) if loading fails after retries
  - No longer marks files as CORRUPTED on temporary decoder errors
- **Rule 11 (Cassette Detection)**
  - Now uses `load_audio_with_retry()` instead of direct `sf.read()`
  - Returns 0 points (no penalty) if loading fails after retries
  - No longer marks files as CORRUPTED on temporary decoder errors
- **Corruption Detection**
  - `CorruptionDetector` now distinguishes temporary errors from real corruption
  - Temporary decoder errors do NOT mark files as corrupted
  - Adds `partial_analysis: True` flag when optional rules (R9/R11) fail
  - Real corruption (NaN, Inf, unreadable files) still detected immediately

### Fixed
- **Critical: False CORRUPTED status on valid files**
  - Files with temporary "lost sync" errors are no longer marked as corrupted
  - Example: "04 - Bial Hclap; Sagrario - Danza coyote.flac" now analyzed correctly
  - Verdict based on critical rules (R1-R8) even if R9/R11 fail temporarily
- **Improved robustness**
  - Files with prolonged silences or non-standard encoding now analyzed correctly
  - Reduced false positives from temporary decoder synchronization issues

### Technical Details
- Modified files:
  - Created: `src/flac_detective/analysis/new_scoring/audio_loader.py`
  - Modified: `src/flac_detective/analysis/new_scoring/artifacts.py`
  - Modified: `src/flac_detective/analysis/new_scoring/rules/cassette.py`
  - Modified: `src/flac_detective/analysis/quality.py`
  - Modified: `src/flac_detective/analysis/analyzer.py`
- New test: `tests/test_audio_loader_retry.py`
- Documentation:
  - `docs/FLAC_DECODER_ERROR_HANDLING.md` - Technical implementation details
  - `docs/GUIDE_RETRY_MECHANISM.md` - User guide

### Performance Impact
- No impact on files without errors (no retry triggered)
- +0.2s to +1s for files with temporary errors (depending on retry count)
- Maximum +1s overhead for persistent errors (3 retries with backoff)

## [0.6.0] - 2025-12-05

### Added
- **Rule 11: Cassette Source Detection**
  - Detects tape hiss, natural roll-off, and cutoff variance
  - Awards 30-65 points for authentic cassette traits
  - **Priority Execution:** Runs before MP3 check and cancels false positive MP3 detections
- **Report Enhancement**: Relative paths in final report
  - Suspicious files now show paths relative to scan root (e.g. `\Album\Song.flac`)
  - Cleaner and more readable output

### Changed
- **Scoring Logic**:
  - Rule 11 runs *before* Rule 1 (MP3 check)
  - If cassette detected (score >= 50), Rule 1 is disabled and a -40pt bonus is applied
  - Fixes false positives where cassette tape noise patterns resembled MP3 artifacts

### Performance
- **Optimization**:
  - Rule 11 only activates for files with cutoff < 19 kHz
  - Integrated into the existing multi-stage optimization pipeline

## [0.5.0] - 2025-12-04

### 🎯 Major Achievement
- **79.2% authentic detection rate** on production dataset (759 files)
- **2.2% fake detection rate** with near-zero false positives (< 0.5%)
- **80% performance improvement** through intelligent optimizations

### Added
- **Rule 8: Nyquist Exception** - Protects authentic files with cutoff near Nyquist frequency
  - 95% Nyquist threshold for global protection
  - 90% Nyquist threshold for MP3 320 kbps specific protection
- **Rule 9: Compression Artifacts Detection** (3 phases)
  - Phase A: Pre-echo detection (MDCT ghosting)
  - Phase B: High-frequency aliasing detection
  - Phase C: MP3 quantization noise patterns
- **Rule 10: Multi-Segment Consistency Analysis**
  - Validates anomalies across 5 file segments
  - Detects dynamic mastering vs global transcoding
- **Rule 7 Enhancement: 3-Phase Vinyl Detection**
  - Phase 1: Dither detection (existing)
  - Phase 2: Vinyl surface noise detection (new)
  - Phase 3: Clicks & pops detection (new)

### Changed
- **Rule 1: MP3 Bitrate Detection** - Enhanced with multiple safeguards
  - Added 95% Nyquist exception (global)
  - Added 90% Nyquist exception (320 kbps specific)
  - Added variance check (cutoff_std > 100 Hz)
  - Widened 320 kbps container range: (700, 950) → (700, 1050) kbps
- **Rule Execution Order** - R8 now calculated FIRST and applied BEFORE short-circuit
  - Ensures authentic files near Nyquist are protected even if R1-R6 give high scores
  - Prevents false positives from early termination
- **Scoring System** - Refined thresholds
  - FAKE_CERTAIN: ≥ 86 points
  - SUSPICIOUS: 61-85 points
  - WARNING: 31-60 points
  - AUTHENTIC: ≤ 30 points

### Performance Optimizations
- **Phase 1: Smart Short-Circuits** (~70% time reduction)
  - Fast path for authentic files (score < 10, no MP3 detected)
  - Early termination for certain fakes (score ≥ 86 after R1-R6+R8)
- **Phase 2: Progressive Rule 10** (~17% time reduction)
  - Starts with 2 segments, expands to 5 only if needed
- **Phase 3: Parallel Execution** (~6% time reduction)
  - R7 and R9 run in parallel when both are needed
- **File Read Cache** - Avoids multiple reads of the same file
- **Total Performance Gain: ~80%** (10 hours → 1h45 for 759 files)

### Fixed
- **Critical: Short-circuit bug** - R8 was not applied before early termination
- **False positives on 21 kHz cutoff** - Files with cutoff at 95% Nyquist incorrectly flagged as MP3 320k
- **False positives on 20.2-20.8 kHz** - Zone between 90-95% Nyquist now protected for 320k detection
- **Vinyl rips misdetection** - R7 Phase 2 & 3 now correctly identify authentic vinyl sources

### Technical Improvements
- Modularized scoring system into separate files:
  - `rules.py` - All scoring rules
  - `bitrate.py` - Bitrate calculations
  - `silence.py` - Silence and vinyl analysis
  - `artifacts.py` - Compression artifacts detection
  - `calculator.py` - Main scoring orchestration
  - `verdict.py` - Score interpretation
- Comprehensive unit tests for all rules
- Improved logging with optimization markers
- Better error handling and edge case coverage

### Documentation
- Complete rule specifications in English
- Performance optimization documentation
- Vinyl detection methodology
- Nyquist exception rationale

## [0.2.0] - 2025-12-01

### Added
- Initial new scoring system implementation
- Rules 1-6 basic implementation
- Text and JSON report generation

### Changed
- Migrated from old scoring to new multi-rule system

## [0.1.0] - 2025-11-29

### Added
- Initial release
- Basic spectral analysis
- Simple scoring mechanism
- Text report output

---

## Version Comparison

| Version | Authentic Rate | Fake Rate | Performance | False Positives |
|---------|---------------|-----------|-------------|-----------------|
| 0.1.0   | ~93% | ~6% | Baseline | ~6% |
| 0.2.0   | ~76% | ~6% | Baseline | ~2% |
| 0.5.0   | **79.2%** | **2.2%** | **+80%** | **< 0.5%** |

[0.5.0]: https://github.com/GuillainM/FLAC_Detective/releases/tag/v0.5.0
[0.2.0]: https://github.com/GuillainM/FLAC_Detective/releases/tag/v0.2.0
[0.1.0]: https://github.com/GuillainM/FLAC_Detective/releases/tag/v0.1.0
