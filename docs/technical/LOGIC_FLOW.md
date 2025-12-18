# 🔍 Analysis Logic Flow

## Complete Analysis Pipeline

### Entry Point

```
User input: python -m flac_detective /path/to/files
    ↓
main.py parses arguments
    ↓
Initializes FLAC Detective engine
    ↓
Begins file discovery
```

### Phase 1: File Discovery

```
Search /path/to/files
    ├─ Find all *.flac files (recursive)
    ├─ Verify file access permissions
    ├─ Build file queue
    └─ Count total files to process

Result: List of absolute FLAC file paths
```

### Phase 2: File Processing Queue

```
For each FLAC file:
    ├─ Check if cached (avoid re-analysis)
    ├─ Copy to temp folder (if external drive)
    ├─ Add to analysis queue
    └─ Update progress indicator

Result: Ready for analysis
```

### Phase 3: Audio Metadata Extraction

```
For each FLAC file:
    
    [Read FLAC streaminfo]
    ├─ Duration (seconds)
    ├─ Sample rate (Hz)
    ├─ Channels (mono/stereo)
    ├─ Bit depth (16-bit or 24-bit)
    └─ Total frames
    
    ↓
    
    Validate metadata:
    ├─ Duration > 0
    ├─ Sample rate standard (44100, 48000, etc)
    └─ Channels in [1,2,6,8]
    
    Result: AudioMetadata object
```

### Phase 4: Spectral Analysis (FFT)

```
For each FLAC file:
    
    [Load audio frames]
    └─ Decode FLAC to PCM
    
    ↓
    
    [Compute FFT]
    ├─ Window: Hann window
    ├─ Size: 8192 or 16384
    └─ Overlap: 50%
    
    ↓
    
    [Analyze spectrum]
    ├─ Convert magnitude to dB
    ├─ Find peak frequencies
    └─ Identify energy distribution
    
    ↓
    
    [Detect cutoff frequency]
    ├─ Find -3dB point
    ├─ Smooth noisy edges
    └─ Return cutoff_freq (Hz)
    
    Result: SpectralMetrics object
```

### Phase 5: Metrics Calculation

```
Compute various metrics:
    
    Bitrate Metrics:
    ├─ File size (bytes)
    ├─ Duration (seconds)
    ├─ Container bitrate = (size * 8) / (duration * 1000)
    └─ Estimated MP3 source bitrate (from cutoff)
    
    Energy Metrics:
    ├─ Total energy
    ├─ High-frequency energy (>16kHz)
    ├─ Energy ratio = HF_energy / total_energy
    └─ Variance of energy
    
    Cutoff Metrics:
    ├─ Cutoff frequency (Hz)
    ├─ Cutoff standard deviation
    ├─ Distance from Nyquist (22050 Hz)
    └─ Match to known MP3 patterns
    
    Result: BitrateMet rics, EnergyMetrics objects
```

### Phase 6: Scoring Context Creation

```
Create ScoringContext:
    
    context = ScoringContext(
        filepath = Path to file,
        cutoff_freq = 20000 Hz (example),
        bitrate_metrics = {...},
        audio_meta = {...},
        sample_rate = 44100 Hz,
        energy_ratio = 0.05,
        cutoff_std = 150 Hz
    )
    
    Initial: score = 0, verdict = "UNKNOWN"
    
    Result: Ready for rule scoring
```

### Phase 7: Rule Application (11 Rules)

```
For each rule (1-11):
    
    RULE N:
    ├─ Check preconditions
    ├─ Analyze specific metrics
    ├─ Calculate score delta
    ├─ Generate reasons
    └─ Update context.score
    
    Rule.apply(context)
    └─ context.score += delta
    
Sequence:
    Rule 1: MP3 Spectral     → +0 to +50
    Rule 2: Cutoff vs Nyquist → +0 to +30
    Rule 3: Bitrate Comparison → +0 to +50
    Rule 4: 24-bit Detection    → +0 to +30
    Rule 5: VBR Protection      → -10 to +0
    Rule 6: Quality Protection  → -20 to +0
    Rule 7: Vinyl Analysis      → -30 to +20
    Rule 8: Nyquist Exception   → +0
    Rule 9: Compression Artifacts → +0 to +50
    Rule 10: Consistency        → +0 to +20
    Rule 11: Cassette Detection → -20 to +0

Result: Cumulative score (can exceed 100)
```

### Phase 8: Score Normalization & Verdict

```
Normalize score to 0-100:
    
    normalized = min(max(raw_score, 0), 100)
    
    ↓
    
    Apply verdict logic:
    
    if normalized >= 86:
        verdict = "FAKE_CERTAIN" ❌
    elif normalized >= 61:
        verdict = "SUSPICIOUS" ⚠️
    elif normalized >= 31:
        verdict = "WARNING" ⚡
    else:
        verdict = "AUTHENTIC" ✅
    
    Result: Final verdict
```

### Phase 9: Report Generation

```
Prepare output:
    
    For each file:
    ├─ Filename
    ├─ Location
    ├─ Duration, Sample rate, Bit depth
    ├─ Score
    ├─ Verdict
    ├─ Individual rule scores
    └─ Reasons for verdict
    
    ↓
    
    Generate formats:
    ├─ Console output (real-time)
    ├─ Text report file (flac_report_YYYYMMDD_HHMMSS.txt)
    └─ Statistics (total analyzed, fake count)
    
    Result: Reports saved
```

### Phase 10: Cleanup & Summary

```
Post-analysis:
    
    ├─ Delete temp files (/tmp/flac_detective_*)
    ├─ Save analysis to cache
    ├─ Display summary:
    │  ├─ Total files: 122
    │  ├─ Authentic: 119
    │  ├─ Warnings: 2
    │  └─ Fakes: 1
    └─ Report location
    
    Result: Analysis complete
```

---

## Decision Trees

### Rule 1: MP3 Spectral Detection

```
Is cutoff >= 95% Nyquist (20947 Hz)?
├─ YES → SKIP (likely anti-aliasing)
└─ NO ↓
   
   Is cutoff == 20000 Hz exactly?
   ├─ YES → Check high-frequency energy
   │  ├─ Energy > threshold → SKIP (ambiguous)
   │  └─ Energy ≤ threshold → CONTINUE
   └─ NO ↓
   
   Does cutoff match known MP3 pattern?
   ├─ YES → Does container bitrate match expected range?
   │  ├─ YES → +50 points (MATCH)
   │  └─ NO → SKIP
   └─ NO → SKIP
```

### Rule 2: Cutoff vs Nyquist

```
threshold = 22000 Hz

distance = threshold - cutoff_freq

if distance > 0:
    score += min(distance / 200, 30)
else:
    score += 0
```

---

## Performance Characteristics

### Time Complexity

```
Per file:
├─ Metadata reading: O(1) - constant time
├─ FFT computation: O(n log n) where n = frame count
├─ Rule application: O(11) = O(1)
└─ Report generation: O(1)

Overall: O(n log n) per file
         O(N * n log n) for N files
```

### Space Complexity

```
Per file analysis:
├─ Raw audio: ~n bytes (duration * sample_rate * channels * 2)
├─ FFT buffers: ~4n bytes
├─ Context object: ~1 KB
└─ Cache entry: ~10 KB

Total: ~O(n) space
```

---

## Fallback Strategies

### FFmpeg Unavailable

```
If FFmpeg not found:
    ├─ Try system PATH
    ├─ Try common locations (/usr/bin, Program Files)
    ├─ Show error message
    └─ EXIT (cannot proceed)
```

### Corrupted FLAC File

```
If metadata unreadable:
    ├─ Try alternate FLAC library
    ├─ Log error
    ├─ Skip file
    └─ Continue with next
```

### Memory Pressure

```
If memory usage > 80%:
    ├─ Pause parallel workers
    ├─ Reduce FFT size
    ├─ Clear caches
    └─ Resume when memory < 60%
```

---

See Also:
- [../RULES.md](../RULES.md) - Rule details
- [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md) - Implementation
- [ERROR_HANDLING.md](ERROR_HANDLING.md) - Error handling
