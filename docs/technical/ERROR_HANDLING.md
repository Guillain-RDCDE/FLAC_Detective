# 🛡️ Error Handling & Recovery

## Error Categories

### 1. File Access Errors

#### Permission Denied

```
Error: PermissionError: [Errno 13] Permission denied

Cause:
- Insufficient file read permissions
- Running process with wrong user
- File on network with disconnected credentials

Handling:
├─ Catch: PermissionError
├─ Log: Warning level
├─ Skip: File (continue with next)
└─ Report: "Permission denied - skipped"

User Action:
- Check file permissions: chmod +r file.flac
- Verify network mount active
- Run with sufficient privileges
```

#### File Not Found

```
Error: FileNotFoundError: [Errno 2] No such file or directory

Cause:
- Incorrect path provided
- File deleted during analysis
- Network drive disconnected

Handling:
├─ Catch: FileNotFoundError
├─ Validate: Path exists before processing
├─ Log: Error level
└─ Skip: File

User Action:
- Verify path is correct: ls /path/to/file
- Check network connection
- Provide absolute path, not relative
```

#### I/O Errors

```
Error: OSError: [Errno 5] Input/output error

Cause:
- Disk read failure
- Corrupted sector on drive
- Device disconnected during read

Handling:
├─ Retry: Up to 3 attempts
├─ Backoff: Exponential (1s, 2s, 4s)
├─ Log: Warning level first, Error after retries
└─ Skip: File if all retries fail

User Action:
- Check disk health: fsck (Linux), chkdsk (Windows)
- Copy file to local drive first
- Replace failing drive
```

---

### 2. Audio Format Errors

#### Unsupported FLAC Format

```
Error: mutagen.flac.FLACError: Unknown FLAC frame

Cause:
- Corrupted FLAC file
- Non-standard FLAC encoding
- Not actually a FLAC file (.flac extension but different format)

Handling:
├─ Catch: FLACError
├─ Fallback: Try alternate library (libflac)
├─ Log: Warning level
├─ Skip: File if both fail
└─ Report: "Unsupported or corrupted FLAC - skipped"

User Action:
- Verify file is actually FLAC: file filename.flac
- Check file header: hexdump -C filename.flac | head
- Re-download or re-encode from source
```

#### Invalid Metadata

```
Error: Metadata block invalid

Example issues:
├─ Sample rate: 0 or >192 kHz
├─ Channels: 0 or >8
├─ Bit depth: not in [16,24]
└─ Duration: 0 or negative

Handling:
├─ Validate: All metadata fields
├─ Use defaults: For missing values
├─ Log: Warning level
└─ Continue: With default assumptions

Example:
if duration <= 0:
    duration = 120  # default 2 minutes
if sample_rate not in [44100, 48000, 96000]:
    sample_rate = 44100  # default
```

---

### 3. FFmpeg Errors

#### FFmpeg Not Installed

```
Error: FileNotFoundError: [Errno 2] No such file or directory 'ffmpeg'

Cause:
- FFmpeg not in system PATH
- FFmpeg not installed

Handling:
├─ Check: System PATH first
├─ Check: Common install locations
├─ Fallback: Use alternative library (scipy)
├─ Log: Error level
└─ Skip: If all options unavailable

Recovery:
1. Try: python -c "import ffmpeg"
2. Try: which ffmpeg (Linux/macOS)
3. Try: where ffmpeg (Windows)
4. Install: See GETTING_STARTED.md
```

#### FFmpeg Decode Error

```
Error: FFmpeg stderr: "Invalid data"

Cause:
- Corrupted FLAC frames
- FFmpeg version incompatibility

Handling:
├─ Retry: With different FFmpeg flags
├─ Fallback: Use scipy for FFT
├─ Log: Warning level
├─ Degrade: Use lower quality analysis
└─ Continue: With partial results

Retry attempts:
1. Standard: ffmpeg -i input.flac
2. With -v quiet: ffmpeg -v quiet -i input.flac
3. With -fflags discardcorrupt: ffmpeg -fflags discardcorrupt
4. Scipy fallback: If all fail
```

---

### 4. Resource Errors

#### Out of Memory

```
Error: MemoryError

Cause:
- FFT buffer too large (very long files)
- Too many files analyzed in parallel
- Insufficient RAM on system

Handling:
├─ Monitor: Memory usage (80% threshold)
├─ Pause: Parallel workers if threshold exceeded
├─ Reduce: FFT size (trade quality for memory)
├─ Wait: For garbage collection
├─ Resume: When memory < 60%

Prevention:
├─ Reduce parallel workers: (CPU_count / 2)
├─ Disable caching for large batches
├─ Close other applications
└─ Add more RAM or process in batches

Code:
import psutil
if psutil.virtual_memory().percent > 80:
    pause_analysis()
    gc.collect()
```

#### Timeout

```
Error: TimeoutError: Analysis exceeds time limit

Cause:
- Very long file (>2 hours)
- Slow FFT computation
- I/O bottleneck

Handling:
├─ Timeout: 30 seconds per file (configurable)
├─ Skip: File (log timeout)
└─ Report: "Analysis timeout - partial results"

Configure:
# In config.py
ANALYSIS_TIMEOUT = 30  # seconds

# Per-file basis:
try:
    result = analyze_file(file, timeout=30)
except TimeoutError:
    log_warning(f"Skipped {file} - timeout")
```

---

### 5. Data Validation Errors

#### Invalid Cutoff Frequency

```
Error: Cutoff frequency out of range

Valid range: 100 Hz - 22050 Hz

Handling:
├─ Check: cutoff_freq in valid range
├─ Clamp: To [100, 22050]
├─ Log: Debug level if clamped
└─ Continue: With clamped value

Example:
if cutoff_freq < 100:
    cutoff_freq = 100  # minimum
    log.debug("Clamped low cutoff")
elif cutoff_freq > 22050:
    cutoff_freq = 22050  # Nyquist maximum
    log.debug("Clamped high cutoff")
```

#### Invalid Score

```
Error: Score outside expected range

Valid range: 0-100 (after normalization)

Handling:
├─ Validate: Each rule contribution
├─ Clamp: Final score to [0, 100]
├─ Log: Warning if out of bounds
└─ Continue: With clamped score

Example:
if raw_score < 0:
    log.warning(f"Negative score {raw_score}")
    raw_score = 0
if raw_score > 100:
    log.warning(f"Score overflow {raw_score}")
    raw_score = 100
```

---

### 6. Network Errors

#### Network Timeout

```
Error: TimeoutError: Network read timeout

Cause:
- Network drive slow/disconnected
- High latency connection

Handling:
├─ Retry: Up to 3 times with backoff
├─ Copy: File to local temp first
├─ Log: Warning level
├─ Skip: If persistent failures

Strategy:
1. Detect: Network path (contains //, \\, or network mount)
2. Copy: To /tmp/flac_detective_XXXX/
3. Analyze: Local copy
4. Cleanup: Temp file after analysis
```

#### Network Disconnection

```
Error: Network unreachable

Handling:
├─ Pause: Analysis
├─ Check: Network connection
├─ Prompt: "Network unavailable. Retry? (y/n)"
├─ Skip: Remaining files if user chooses
└─ Report: Partial results

Code:
try:
    analyze_network_file(file)
except (OSError, IOError):
    response = prompt("Network error. Continue? (y/n): ")
    if response.lower() != 'y':
        break
```

---

## Recovery Strategies

### Retry Logic

```python
def retry_analysis(file, max_retries=3):
    """Retry analysis with exponential backoff."""
    
    for attempt in range(max_retries):
        try:
            return analyze(file)
        except (IOError, OSError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                log.warning(
                    f"Attempt {attempt+1} failed. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                log.error(f"All {max_retries} attempts failed. Skipping {file}")
                raise
```

### Fallback Options

```
Primary: FFmpeg audio decoding
    ↓ (if fails)
Fallback 1: scipy.io.wavfile
    ↓ (if fails)
Fallback 2: Mutagen-only (metadata only, skip FFT)
    ↓ (if fails)
Skip: File (log error, continue)
```

### Graceful Degradation

```
Full Analysis (all 11 rules):
    ↓ (if memory pressure)
Reduced Analysis (skip rules 7, 9, 10):
    ↓ (if timeout approaching)
Fast Analysis (only rules 1, 2):
    ↓ (if critical failure)
Metadata Only (no FFT, verdict based on metadata)
    ↓ (if all else fails)
Skip: File
```

---

## Logging

### Log Levels

```
DEBUG: Detailed diagnostic info
    Example: "Cutoff clamped from 100 Hz to 100 Hz"

INFO: General informational messages
    Example: "Analyzing file: track.flac"

WARNING: Something unexpected, but recoverable
    Example: "FFmpeg not in PATH, trying fallback"

ERROR: Serious problem, file skipped
    Example: "Corrupted FLAC file, skipping"

CRITICAL: Entire analysis aborted
    Example: "Out of memory, cannot continue"
```

### Log Configuration

```python
# Enable debug output
import logging
logging.basicConfig(level=logging.DEBUG)

# File logging
handler = logging.FileHandler('analysis.log')
handler.setLevel(logging.WARNING)
logging.getLogger().addHandler(handler)
```

---

## Testing Error Paths

### Unit Tests

```python
def test_permission_denied():
    """Test handling of permission denied."""
    with patch('builtins.open', side_effect=PermissionError):
        result = analyze_file("test.flac")
        assert result is None  # File skipped

def test_memory_pressure():
    """Test degradation under memory pressure."""
    with patch('psutil.virtual_memory',
               return_value=Mock(percent=85)):
        # Should use reduced analysis
        pass

def test_retry_logic():
    """Test retry mechanism."""
    mock_analyze = Mock(side_effect=[IOError, IOError, SUCCESS])
    result = retry_analysis(mock_analyze)
    assert mock_analyze.call_count == 3
```

---

## See Also

- [../TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - User troubleshooting guide
- [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md) - Implementation details
- [LOGIC_FLOW.md](LOGIC_FLOW.md) - Analysis pipeline
