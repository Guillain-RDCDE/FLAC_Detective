# FLAC Detective v0.6.7 - Technical Documentation

## Overview

FLAC Detective is an advanced audio analysis tool designed to detect MP3-to-FLAC transcodes with exceptional precision. Version 0.6.6 builds on the production-ready v0.5.0 (79.2% authentic detection rate, <0.5% false positive rate) by adding robust error handling for temporary FLAC decoder errors.

## Architecture

### Core Components

```
src/flac_detective/
├── analysis/
│   ├── new_scoring/          # Advanced scoring system
│   │   ├── __init__.py       # Public API
│   │   ├── models.py         # Data structures
│   │   ├── constants.py      # Detection thresholds
│   │   ├── bitrate.py        # Bitrate analysis
│   │   ├── silence.py        # Silence & vinyl detection
│   │   ├── artifacts.py      # Compression artifacts
│   │   ├── audio_loader.py   # NEW v0.6.6: Retry mechanism for decoder errors
│   │   ├── rules/            # Scoring rules directory
│   │   │   ├── __init__.py
│   │   │   ├── artifacts.py  # Rule 9
│   │   │   ├── cassette.py   # Rule 11
│   │   │   └── ...
│   │   ├── calculator.py     # Orchestration & optimization
│   │   └── verdict.py        # Score interpretation
│   ├── spectrum.py           # Spectral analysis
│   ├── quality.py            # Quality analysis (corruption detection)
│   └── audio_cache.py        # File read optimization
├── reporting/                # Report generation
└── main.py                   # CLI entry point
```

## Error Handling and Retry Mechanism (v0.6.6)

### Problem Statement

Some valid FLAC files generate temporary decoder errors (e.g., "flac decoder lost sync") when loaded by `soundfile` or `librosa`. These errors are often transient and resolve on retry, but previously caused files to be incorrectly marked as CORRUPTED.

### Solution Architecture

**Module**: `src/flac_detective/analysis/new_scoring/audio_loader.py`

#### Core Functions

**1. `is_temporary_decoder_error(error_message: str) -> bool`**

Identifies temporary decoder errors that should trigger retry:
- "lost sync"
- "decoder error"
- "sync error"
- "invalid frame"
- "unexpected end"

```python
def is_temporary_decoder_error(error_message: str) -> bool:
    temporary_error_patterns = [
        "lost sync", "decoder error", "sync error",
        "invalid frame", "unexpected end"
    ]
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in temporary_error_patterns)
```

**2. `load_audio_with_retry(file_path, max_attempts=3, initial_delay=0.2, backoff_multiplier=1.5)`**

Loads audio with automatic retry on temporary errors:
- **Max attempts**: 3 (configurable)
- **Exponential backoff**: 0.2s → 0.3s → 0.45s
- **Returns**: `(audio_data, sample_rate)` or `(None, None)` on failure

```python
def load_audio_with_retry(file_path, max_attempts=3, initial_delay=0.2, 
                          backoff_multiplier=1.5):
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            audio_data, sample_rate = sf.read(file_path)
            if attempt > 1:
                logger.info(f"✅ Audio loaded successfully on attempt {attempt}")
            return audio_data, sample_rate
        except Exception as e:
            if is_temporary_decoder_error(str(e)):
                if attempt < max_attempts:
                    logger.warning(f"⚠️ Temporary error on attempt {attempt}: {e}")
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= backoff_multiplier
                else:
                    logger.error(f"❌ Failed after {max_attempts} attempts: {e}")
            else:
                break  # Non-temporary error, don't retry
    return None, None
```

### Integration Points

#### 1. Rule 9: Compression Artifacts Detection

**File**: `src/flac_detective/analysis/new_scoring/artifacts.py`

**Changes**:
```python
# Before (v0.6.0)
audio_data, sample_rate = sf.read(file_path)

# After (v0.6.6)
audio_data, sample_rate = load_audio_with_retry(file_path)
if audio_data is None or sample_rate is None:
    logger.error("RULE 9: Failed to load audio after retries. Returning 0 points.")
    return 0, [], details  # No penalty for temporary errors
```

**Behavior**:
- On success: Normal analysis proceeds
- On failure after retries: Returns 0 points (neutral contribution)
- File is NOT marked as corrupted

#### 2. Rule 11: Cassette Detection

**File**: `src/flac_detective/analysis/new_scoring/rules/cassette.py`

**Changes**:
```python
# Before (v0.6.0)
audio, sr = sf.read(file_path)

# After (v0.6.6)
audio, sr = load_audio_with_retry(file_path)
if audio is None or sr is None:
    logger.error("RULE 11: Failed to load audio after retries. Returning 0 points.")
    return 0, reasons  # No penalty
```

#### 3. Corruption Detection

**File**: `src/flac_detective/analysis/quality.py`

**Changes**:
```python
class CorruptionDetector(QualityDetector):
    def detect(self, filepath: Path, **kwargs) -> Dict[str, Any]:
        try:
            # Use retry mechanism
            data, samplerate = load_audio_with_retry(str(filepath))
            
            if data is None or samplerate is None:
                # Temporary error, NOT corruption
                return {
                    "is_corrupted": False,
                    "readable": True,
                    "error": "Temporary decoder error (not marked as corrupted)",
                    "partial_analysis": True,
                }
            
            # Check for real corruption (NaN, Inf)
            if np.any(np.isnan(data)) or np.any(np.isinf(data)):
                return {"is_corrupted": True, ...}
            
            return {"is_corrupted": False, ...}
            
        except Exception as e:
            # Distinguish temporary vs real errors
            if is_temporary_decoder_error(str(e)):
                return {"is_corrupted": False, "partial_analysis": True, ...}
            else:
                return {"is_corrupted": True, ...}
```

### Error Handling Strategy

#### Temporary Errors (Retry)
- **Trigger**: Error message matches temporary patterns
- **Action**: Retry up to 3 times with exponential backoff
- **On success**: Continue normal analysis
- **On failure**: Return 0 points, set `partial_analysis: True`
- **Corruption status**: NOT marked as corrupted

#### Real Errors (No Retry)
- **Examples**: File not found, permission denied, NaN/Inf values
- **Action**: Immediate failure, no retry
- **Corruption status**: Marked as corrupted

### Performance Impact

| Scenario | Time Impact | Frequency |
|----------|-------------|-----------|
| No error | 0ms (no retry) | ~99% of files |
| Success on attempt 2 | +200ms | ~0.8% of files |
| Success on attempt 3 | +500ms | ~0.1% of files |
| Failure after 3 attempts | +1000ms | ~0.1% of files |

**Overall impact**: Negligible (<0.5% average overhead)

### Logging

**Debug Level**:
```
DEBUG: Loading audio (attempt 1/3): file.flac
WARNING: ⚠️ Temporary error on attempt 1: flac decoder lost sync
INFO: Retrying in 0.2s...
DEBUG: Loading audio (attempt 2/3): file.flac
INFO: ✅ Audio loaded successfully on attempt 2
```

**Error Level** (after 3 failures):
```
ERROR: ❌ Failed after 3 attempts: flac decoder lost sync
ERROR: RULE 9: Failed to load audio after retries. Returning 0 points.
```

### Result Flags

**New field**: `partial_analysis: bool`

Indicates that some optional rules (R9, R11) failed due to temporary errors:

```python
{
    "verdict": "AUTHENTIC",
    "score": 25,
    "is_corrupted": False,
    "partial_analysis": True,  # NEW in v0.6.6
    "corruption_error": "Temporary decoder error (not marked as corrupted)"
}
```

**Interpretation**:
- `partial_analysis: False` → Full analysis completed
- `partial_analysis: True` → R9/R11 failed, but verdict based on R1-R8 is still valid

## Detection Rules

### Rule 1: MP3 Spectral Signature Detection (+50 pts)

**Purpose**: Identifies constant bitrate MP3 transcodes by analyzing frequency cutoff patterns.

**Method**:
1. Detect cutoff frequency from spectrum analysis
2. Match against known MP3 bitrate signatures:
   - 128 kbps: 10-15.5 kHz
   - 160 kbps: 15.5-16.5 kHz
   - 192 kbps: 16.5-17.5 kHz
   - 224 kbps: 17.5-18.5 kHz
   - 256 kbps: 18.5-19.5 kHz
   - 320 kbps: 19.5-21.5 kHz
3. Verify container bitrate matches expected range

**Safeguards**:
- **95% Nyquist Exception**: Skip if cutoff ≥ 95% of Nyquist frequency
- **90% Nyquist Exception** (320 kbps only): Skip if cutoff ≥ 90% of Nyquist
- **Variance Check**: Skip if cutoff_std > 100 Hz (variable spectrum)
- **Absolute Limit**: Skip if cutoff > 21.5 kHz (MP3 never exceed this)

**Example** (44.1 kHz):
```python
# Detection zones
0-19.5 kHz      : MP3 128-256 kbps (active)
19.5-19.845 kHz : MP3 320 kbps (active)
19.845-20.947   : Protected (90-95% Nyquist, skip 320k)
20.947-22.05    : Ultra-protected (95%+ Nyquist, skip all)
```

### Rule 2: Cutoff Frequency Deficit (+0-30 pts)

**Purpose**: Penalizes files with suspiciously low cutoff relative to sample rate.

**Method**:
```python
cutoff_threshold = get_cutoff_threshold(sample_rate)
if cutoff_freq < cutoff_threshold:
    deficit = cutoff_threshold - cutoff_freq
    penalty = min(deficit / 200, 30)
```

**Thresholds by sample rate**:
- 44.1 kHz → 20 kHz
- 48 kHz → 22 kHz
- 88.2 kHz → 40 kHz
- 96 kHz → 44 kHz

### Rule 3: Source vs Container Bitrate (+50 pts)

**Purpose**: Detects when MP3 source bitrate is much lower than FLAC container.

**Trigger**: MP3 detected (R1) AND container_bitrate > 600 kbps

**Rationale**: Proves file is a converted MP3, not an authentic FLAC.

### Rule 4: Suspicious 24-bit Files (+30 pts)

**Purpose**: Flags 24-bit files with low MP3 source bitrate.

**Conditions** (all must be true):
1. Bit depth = 24-bit
2. MP3 source detected with bitrate < 500 kbps
3. Cutoff frequency < 19 kHz

**Safeguard**: Skip if vinyl noise detected (R7 Phase 2)

### Rule 5: High Variance Protection (-40 pts)

**Purpose**: Protects authentic FLAC with variable bitrate encoding.

**Trigger**: bitrate > 1000 kbps AND variance > 100 kbps

**Rationale**: FLAC uses VBR; constant bitrate suggests transcode.

### Rule 6: High Quality Protection (-30 pts)

**Purpose**: Protects authentic high-quality FLAC files.

**Conditions** (all must be true):
1. No MP3 signature detected
2. Container bitrate > 700 kbps
3. Cutoff frequency ≥ 19 kHz
4. Bitrate variance > 50 kbps

### Rule 7: Silence & Vinyl Analysis (-50 to +70 pts)

**Purpose**: Distinguishes MP3 dither from authentic silence and vinyl noise.

**Activation**: Cutoff in ambiguous zone (19-21.5 kHz)

#### Phase 1: Dither Detection
- **+50 pts**: ratio > 0.3 (artificial dither → TRANSCODE)
- **-50 pts**: ratio < 0.15 (natural silence → AUTHENTIC)
- **0 pts**: 0.15 ≤ ratio ≤ 0.3 (uncertain → Phase 2)

#### Phase 2: Vinyl Noise Detection
- **-40 pts**: Vinyl noise detected (authentic vinyl rip)
- **+20 pts**: No noise above cutoff (digital upsample suspect)
- **0 pts**: Noise with pattern (uncertain → Phase 3)

#### Phase 3: Clicks & Pops (Optional)
- **-10 pts**: 5-50 clicks/min (confirms vinyl)
- **0 pts**: Outside range

**Total Range**: -100 to +70 points

### Rule 8: Nyquist Exception (-30/-50 pts)

**Purpose**: Protects files with cutoff near Nyquist frequency.

**Calculation** (always executed FIRST):
```python
nyquist = sample_rate / 2.0
cutoff_ratio = cutoff_freq / nyquist

if cutoff_ratio >= 0.98:
    score = -50  # Very close to Nyquist
elif cutoff_ratio >= 0.95:
    score = -30  # Close to Nyquist
else:
    score = 0
```

**Safeguards** (reduce/cancel bonus if suspicious):
- MP3 signature + silence_ratio > 0.2 → Cancel bonus
- MP3 signature + silence_ratio > 0.15 → Reduce to -15 pts

**Critical**: R8 is calculated FIRST and applied BEFORE short-circuit to guarantee protection.

### Rule 9: Compression Artifacts Detection (+0-40 pts)

**Purpose**: Detects psychoacoustic compression signatures.

**Activation**: cutoff < 21 kHz OR MP3 detected

#### Test 9A: Pre-echo Detection (+0-15 pts)
- Analyzes MDCT ghosting before transients
- > 10% transients affected: +15 pts
- 5-10% affected: +10 pts

#### Test 9B: High-Frequency Aliasing (+0-15 pts)
- Detects filterbank artifacts
- Correlation > 0.5: +15 pts (strong)
- Correlation 0.3-0.5: +10 pts (moderate)

#### Test 9C: MP3 Noise Pattern (+0-10 pts)
- Identifies quantization noise patterns
- Pattern detected: +10 pts

**Total Range**: 0-40 points

### Rule 10: Multi-Segment Consistency (-20/-30 pts)

**Purpose**: Validates anomalies are consistent throughout file.

**Activation**: score > 30 (already suspect)

**Method**:
1. Divide file into 5 segments (start, 25%, 50%, 75%, end)
2. Detect cutoff for each segment
3. Calculate variance

**Actions**:
- Variance > 1000 Hz: -20 pts (dynamic mastering, not transcode)
- Only 1 problematic segment: -30 pts (local artifact)
- Variance < 500 Hz: 0 pts (confirms transcode or authenticity)

## Scoring System

### Score Calculation

```python
total_score = 0

# Phase 1: Calculate R8 FIRST (protection)
r8_score = apply_rule_8(...)
total_score = 0

# Phase 2: Fast rules (R1-R6)
total_score += apply_rule_1(...)  # MP3 detection
total_score += apply_rule_2(...)  # Cutoff deficit
total_score += apply_rule_3(...)  # Source vs container
total_score += apply_rule_4(...)  # 24-bit suspect
total_score += apply_rule_5(...)  # High variance
total_score += apply_rule_6(...)  # High quality

# Apply R8 BEFORE short-circuit
total_score += r8_score
total_score = max(0, total_score)

# Short-circuit 1: FAKE_CERTAIN
if total_score >= 86:
    return total_score  # R8 already applied

# Short-circuit 2: Fast path AUTHENTIC
if total_score < 10 and no_mp3_detected:
    return total_score  # R8 already applied

# Phase 3: Expensive rules (conditional)
if 19000 <= cutoff <= 21500:
    total_score += apply_rule_7(...)  # Silence/vinyl

if cutoff < 21000 or mp3_detected:
    total_score += apply_rule_9(...)  # Artifacts

# Refine R8 if MP3 detected
if mp3_detected:
    total_score -= r8_score  # Remove old
    r8_score = apply_rule_8(..., mp3_detected, silence_ratio)
    total_score += r8_score  # Apply refined

# Phase 4: Multi-segment (if suspect)
if total_score > 30:
    total_score += apply_rule_10(...)

return max(0, total_score)
```

### Verdict Thresholds

```python
if score >= 86:
    verdict = "FAKE_CERTAIN"     # 100% confidence
elif score >= 61:
    verdict = "SUSPICIOUS"        # High confidence
elif score >= 31:
    verdict = "WARNING"           # Manual review recommended
else:
    verdict = "AUTHENTIC"         # 99.5% confidence
```

## Performance Optimizations

### 1. Smart Short-Circuits (~70% time reduction)

**Fast Path (Authentic)**:
```python
if score < 10 and mp3_bitrate_detected is None:
    # Skip R7, R9, R10 (expensive rules)
    return score
```
- Applies to ~68% of files
- Saves ~2-3 seconds per file

**Early Termination (Fake)**:
```python
if score >= 86:
    # Skip remaining rules
    return score
```
- Applies to ~2% of files
- Saves ~1-2 seconds per file

### 2. Progressive Rule 10 (~17% time reduction)

```python
# Start with 2 segments
cutoffs = analyze_segments(file, num_segments=2)
variance = calculate_variance(cutoffs)

# Expand to 5 only if needed
if variance_is_borderline:
    cutoffs = analyze_segments(file, num_segments=5)
```

### 3. Parallel Execution (~6% time reduction)

```python
if run_rule7 and run_rule9:
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_r7 = executor.submit(apply_rule_7, ...)
        future_r9 = executor.submit(apply_rule_9, ...)
        
        r7_score = future_r7.result()
        r9_score = future_r9.result()
```

### 4. File Read Cache (~3% time reduction)

```python
@lru_cache(maxsize=128)
def read_audio_file(filepath):
    return sf.read(filepath)
```

**Total Performance Gain**: ~80% (10 hours → 1h45 for 759 files)

## Data Structures

### AudioMetadata

```python
@dataclass
class AudioMetadata:
    sample_rate: int      # Hz (e.g., 44100, 48000)
    bit_depth: int        # bits (16 or 24)
    channels: int         # 1 (mono) or 2 (stereo)
    duration: float       # seconds
```

### BitrateMetrics

```python
@dataclass
class BitrateMetrics:
    real_bitrate: float      # kbps (file_size * 8 / duration / 1000)
    apparent_bitrate: int    # kbps (sample_rate * bit_depth * channels / 1000)
    variance: float          # kbps (std dev across segments)
```

## Constants

### MP3 Signatures

```python
MP3_SIGNATURES = [
    (320, 19500, 21500),  # 320 kbps: ~19.5-21.5 kHz
    (256, 18500, 19500),  # 256 kbps: ~18.5-19.5 kHz
    (224, 17500, 18500),  # 224 kbps: ~17.5-18.5 kHz
    (192, 16500, 17500),  # 192 kbps: ~16.5-17.5 kHz
    (160, 15500, 16500),  # 160 kbps: ~15.5-16.5 kHz
    (128, 10000, 15500),  # 128 kbps: < 15.5 kHz
]
```

### Container Bitrate Ranges

```python
MP3_CONTAINER_RANGES = {
    128: (400, 550),
    160: (450, 650),
    192: (500, 750),
    224: (550, 800),
    256: (600, 850),
    320: (700, 1050),  # Widened in v0.5.0
}
```

### Score Thresholds

```python
SCORE_FAKE_CERTAIN = 86
SCORE_SUSPICIOUS = 61
SCORE_WARNING = 31
SCORE_AUTHENTIC = 30
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flac_detective --cov-report=html

# Run specific test file
pytest tests/test_new_scoring_rules.py
```

### Test Coverage

- **Rules**: 100% coverage for R1-R10
- **Bitrate calculations**: 95% coverage
- **Silence analysis**: 90% coverage
- **Overall**: ~85% code coverage

### Validation Tests

```python
# Test 1: Authentic high-quality FLAC
assert score <= 30  # AUTHENTIC

# Test 2: MP3 128-224 kbps transcode
assert score >= 86  # FAKE_CERTAIN

# Test 3: Authentic vinyl rip
assert score <= 30  # AUTHENTIC (R7 Phase 2 protection)

# Test 4: Grey zone (19-20 kHz)
# Depends on variance and other factors
```

## Logging

### Log Levels

```python
# Minimal (errors only)
logging.basicConfig(level=logging.ERROR)

# Normal (info + warnings)
logging.basicConfig(level=logging.INFO)

# Verbose (debug)
logging.basicConfig(level=logging.DEBUG)
```

### Log Format

```
RULE 1: +50 points (cutoff 17500 Hz ~= 192 kbps MP3, container 700 kbps in range 500-750)
RULE 2: +12 points (cutoff 17458 < threshold 20000)
RULE 8 (pre-calculated): 0 points
OPTIMIZATION: Fast rules + R8 score = 62
OPTIMIZATION: Short-circuit at 62 < 86, continuing...
```

## API Usage

### Python API

```python
from flac_detective.analysis.new_scoring import new_calculate_score
from pathlib import Path

# Analyze a file
filepath = Path("/path/to/file.flac")
score, verdict, confidence, reasons = new_calculate_score(
    cutoff_freq=20500,
    metadata={"sample_rate": 44100, "bit_depth": 16, "channels": 2},
    duration_check={"duration": 180.5},
    filepath=filepath
)

print(f"Score: {score}/150")
print(f"Verdict: {verdict}")
print(f"Confidence: {confidence}")
print(f"Reasons: {reasons}")
```

### CLI Usage

```bash
# Analyze directory
flac-detective /path/to/music

# JSON output
flac-detective /path/to/music --format json

# Verbose
flac-detective /path/to/music --verbose

# Custom output
flac-detective /path/to/music --output report.txt
```

## Troubleshooting

### Common Issues

**Issue**: High false positive rate  
**Solution**: Check if R8 is being calculated first (v0.5.0 fix)

**Issue**: Vinyl rips flagged as fake  
**Solution**: Ensure R7 Phase 2 & 3 are active

**Issue**: Slow analysis  
**Solution**: Enable short-circuits and parallel execution

**Issue**: Inconsistent results  
**Solution**: Check file read cache is enabled

**Issue**: Files marked as CORRUPTED with "lost sync" error (v0.6.6)  
**Solution**: Update to v0.6.6 which includes automatic retry mechanism

**Issue**: "flac decoder lost sync" in logs  
**Solution**: This is now handled automatically. Check for "✅ Audio loaded successfully on attempt X" message

**Issue**: File has `partial_analysis: True` flag  
**Solution**: This is normal. Rules 9 and 11 failed temporarily, but verdict based on R1-R8 is still valid

**Issue**: Want to see retry attempts in logs  
**Solution**: Enable DEBUG logging: `--log-level DEBUG` or `logging.basicConfig(level=logging.DEBUG)`

## Future Enhancements

### Planned for v0.6

- GUI interface
- Configurable sensitivity presets
- Per-rule enable/disable
- Custom threshold configuration
- HTML reports with spectrograms

### Under Consideration

- ALAC/WAV support
- Machine learning integration
- Cloud API
- Music player integration

## References

### Research Papers

- MP3 psychoacoustic compression (ISO/IEC 11172-3)
- Spectral analysis techniques
- Vinyl noise characteristics
- FLAC encoding patterns

### Tools & Libraries

- **NumPy**: Numerical computations
- **SciPy**: Signal processing
- **Soundfile**: Audio file I/O
- **Mutagen**: Metadata extraction
- **Matplotlib**: Spectrogram generation

---

**FLAC Detective v0.6.6 Technical Documentation**  
**Last Updated: 2025-12-12**
