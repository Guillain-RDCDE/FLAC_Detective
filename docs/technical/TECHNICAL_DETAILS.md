# 🔬 Technical Details

## Spectral Analysis

### FFT (Fast Fourier Transform)

FLAC Detective uses FFT to analyze audio frequency content:

```
Time Domain Audio
    ↓
[FFT Computation]
    ↓
Frequency Domain
    ↓
[Identify Cutoff]
    ↓
MP3 Signature Detection
```

### Cutoff Detection Algorithm

1. **Load audio**: Read FLAC file
2. **Compute FFT**: Convert to frequency domain
3. **Analyze spectrum**: Find energy threshold
4. **Identify cutoff**: Last frequency with significant energy
5. **Compare patterns**: Check against known MP3 signatures

### Why MP3s Have Cutoffs

MP3 encoding uses psychoacoustic compression:
- 128 kbps: Removes content above ~16 kHz
- 192 kbps: Removes content above ~19 kHz
- 256 kbps: Removes content above ~20 kHz
- 320 kbps: Preserves ~20-20.5 kHz

When upscaled to FLAC, these patterns remain visible in FFT analysis.

---

## Scoring Engine

### Rule Application

```python
context = ScoringContext(...)

for rule_class in RULES:
    rule = rule_class()
    rule.apply(context)  # Modifies context.score

final_score = context.score
verdict = generate_verdict(final_score)
```

### Score Ranges

```
Rule contributions:
  +60 / +50 / +40   : Strong evidence (rules 1, 2, 3, 7, 9)
  +30 / +20 / +15   : Moderate evidence (rules 4, 5, 7, 10)
  +7 / 0 / -10 / -20: Weak/protective (rules 5, 6, 7, 8, 11)

Total Range: -50 to +180 (normalized to 0-100)
```

---

## Performance Characteristics

### FFT Computation

```
File Duration | Computation Time | Memory
2:00 min     | ~50 ms          | ~20 MB
5:00 min     | ~120 ms         | ~45 MB
10:00 min    | ~240 ms         | ~85 MB
```

### Overall Analysis

```
Number of Files | Time | Memory
10              | 5s   | 100 MB
100             | 50s  | 200 MB
1000            | 8min | 400 MB
```

---

## Caching

### Audio Cache

```
Cache Entry:
├── Audio Hash (MD5)
├── Spectral Data (FFT)
├── Metadata
├── Cutoff Frequency
└── Timestamp

Benefits:
- 2nd analysis of same file: 90% faster
- Avoids redundant FFT computation
- Location: ~/.flac_detective/cache/
```

### Cache Invalidation

```
Cache invalidated if:
- File modified (timestamp changed)
- File hash differs
- Cache entry older than 30 days
- Cache corruption detected
```

---

## Error Handling

### FFmpeg Errors

```
Handled:
- Corrupted FLAC frames
- Unsupported sample rates
- Missing FFmpeg

Fallback:
- Skip corrupted files
- Use default parameters
- Retry up to 3 times
```

### Resource Limits

```
Memory limit:  2 GB (adjustable)
Timeout:       30s per file
Max files:     10,000 per scan

If exceeded:
- Warning logged
- Graceful degradation
- Partial results returned
```

---

## Data Structures

### ScoringContext

```python
@dataclass
class ScoringContext:
    filepath: Path
    score: int = 0
    verdict: str = "UNKNOWN"
    
    cutoff_freq: float          # Hz
    bitrate_metrics: dict       # Bitrate info
    audio_meta: AudioMetadata   # Duration, SR
    
    reasons: List[str] = []     # Why scored
    mp3_bitrate_detected: Optional[int] = None
```

### AudioMetadata

```python
@dataclass
class AudioMetadata:
    duration: float             # Seconds
    sample_rate: int            # Hz
    channels: int               # 1, 2, etc
    bit_depth: int              # 16, 24
    frame_count: int            # Total frames
```

---

## File I/O

### FLAC Reading

```
FLAC File
  ├── STREAMINFO block
  │   ├── Duration
  │   ├── Sample rate
  │   └── Bit depth
  ├── VORBIS_COMMENT (optional metadata)
  └── Audio frames (FRAME blocks)

Library: mutagen.flac
```

### Temp File Handling

```
Original: /network/music/file.flac  (slow access)
    ↓
Copy to: /tmp/flac_detective_XXXX/file.flac  (fast access)
    ↓
Analyze
    ↓
Cleanup: /tmp/flac_detective_XXXX/file.flac
```

---

## Numerical Stability

### FFT Precision

- Type: 32-bit float
- Dynamic range: ~48 dB
- Frequency resolution: Sample_rate / FFT_size

### Cutoff Detection

- Threshold: -3dB (half power point)
- Smoothing: Gaussian window
- Validation: Cross-check with energy ratio

---

## Multiprocessing

### Parallel Analysis

```
Main Process
    ├─ File 1 → Worker 1 → Result 1
    ├─ File 2 → Worker 2 → Result 2
    ├─ File 3 → Worker 3 → Result 3
    └─ File 4 → Worker 4 → Result 4

Workers: min(4, CPU_count)
```

### Thread Safety

```
Shared resources:
  - Progress bar (thread-safe queue)
  - Result aggregation (atomic operations)

Per-thread:
  - Analyzer instance (independent FFT)
  - Temp files (unique names)
  - Cache entries (read-only)
```

---

See Also:
- [../RULES.md](../RULES.md) - Rule specifications
- [LOGIC_FLOW.md](LOGIC_FLOW.md) - Analysis algorithm
- [ERROR_HANDLING.md](ERROR_HANDLING.md) - Error handling details
