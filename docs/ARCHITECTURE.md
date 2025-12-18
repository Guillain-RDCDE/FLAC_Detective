# 🏗️ FLAC Detective Architecture

## System Overview

FLAC Detective is a modular audio analysis framework with 11 independent detection rules.

```
┌─────────────────────────────────────────────┐
│         User Input (FLAC files)             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
         ┌──────────────────┐
         │  File Indexer    │
         │  (Find all FLACs)│
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  Metadata Reader │
         │  (Duration, SR)  │
         └────────┬─────────┘
                  │
                  ▼
      ┌───────────────────────────┐
      │  Spectral Analysis        │
      │  (FFT, cutoff freq, etc)  │
      └────────┬──────────────────┘
               │
               ▼
      ┌──────────────────────────┐
      │   11-Rule Scorer         │
      │  (Rules 1-11 apply here) │
      └────────┬─────────────────┘
               │
               ▼
      ┌──────────────────────────┐
      │  Verdict Generator       │
      │  (AUTHENTIC/WARNING/etc) │
      └────────┬─────────────────┘
               │
               ▼
      ┌──────────────────────────┐
      │  Report Generator        │
      │  (Console + Text file)   │
      └──────────────────────────┘
```

## Core Components

### 1. **Analyzer** (`src/flac_detective/analysis/analyzer.py`)
- Main orchestrator
- Manages analysis pipeline
- Handles file I/O & caching

### 2. **Audio Metadata** (`src/flac_detective/analysis/metadata.py`)
- Reads FLAC metadata
- Extracts: duration, sample rate, channels, bit depth
- Uses Mutagen library

### 3. **Spectral Analysis** (`src/flac_detective/analysis/spectrum.py`)
- FFT computation
- Frequency cutoff detection
- Energy distribution analysis

### 4. **Scoring Engine** (`src/flac_detective/analysis/new_scoring/`)
- Strategy pattern implementation
- 11 independent rules (Rules 1-11)
- Calculates final verdict score

### 5. **Reporting** (`src/flac_detective/reporting/`)
- Generates console output
- Creates text reports
- Formats statistics

## Detection Rules (11 Total)

| Rule | Name | Detection Method |
|------|------|------------------|
| 1 | MP3 Spectral Signature | Cutoff frequency analysis |
| 2 | Cutoff vs Nyquist | Frequency boundary check |
| 3 | Source vs Container | Bitrate comparison |
| 4 | Suspicious 24-bit | Unnormal bit depth detection |
| 5 | High Variance Protection | VBR protection |
| 6 | Variable Bitrate Protection | High-quality protection |
| 7 | Silence & Vinyl | Surface noise, clicks, pops |
| 8 | Nyquist Exception | High frequency preservation |
| 9 | Compression Artifacts | Pre-echo, aliasing detection |
| 10 | Multi-Segment Consistency | Uniform artifact patterns |
| 11 | Cassette Detection | Analog source identification |

## Data Flow

```
FLAC File
   │
   ├─► Extract Metadata (duration, SR)
   │
   ├─► Compute FFT (spectral analysis)
   │
   ├─► Calculate Metrics:
   │   - Cutoff frequency
   │   - Energy distribution
   │   - Variance patterns
   │   - Bitrate ratio
   │
   ├─► Apply Rules 1-11:
   │   - Each rule returns (score_delta, reasons)
   │   - Total score = sum of all deltas
   │
   └─► Generate Verdict:
       - Score ≥ 86  → FAKE_CERTAIN
       - Score 61-85 → SUSPICIOUS
       - Score 31-60 → WARNING
       - Score ≤ 30  → AUTHENTIC
```

## Performance Optimization

- **Caching**: Results cached to avoid re-analysis
- **Short-circuits**: Obvious cases flagged early
- **Parallel processing**: Multiple rules computed independently
- **FFT optimization**: Downsampled when possible

## See Also

- [RULES.md](RULES.md) - Detailed rule specifications
- [technical/LOGIC_FLOW.md](technical/LOGIC_FLOW.md) - Detailed analysis flow
- [technical/TECHNICAL_DETAILS.md](technical/TECHNICAL_DETAILS.md) - Implementation details
