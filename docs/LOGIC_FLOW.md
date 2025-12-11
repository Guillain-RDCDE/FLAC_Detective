# FLAC Detective - Decision Logic Flow

This document explains FLAC Detective's analysis logic as a simple decision tree. Follow the flow to understand how each file is analyzed and scored.

---

## Main Analysis Flow

```
           START: FLAC File
                  |
                  v
       [1] Is file readable?
                  |
      +-----------+-----------+
      |                       |
     NO                      YES
      |                       |
      v                       v
   ERROR:            [2] Extract metadata
   File corrupted        (sample rate, channels, duration)
      |                       |
      v                       v
   VERDICT:          [3] Perform spectral analysis (FFT)
   CORRUPTED                  |
                  +-----------+-----------+
                  |                       |
                ERROR                  SUCCESS
                  |                       |
                  v                       v
               VERDICT:          [4] Calculate cutoff frequency
               CORRUPTED              & energy ratio
                                      |
                                      v
                              [5] Calculate bitrate metrics
                                      |
                                      v
                              [6] Check quality issues
                                  (duration, DC offset,
                                   silence, clipping)
                                      |
                                      v
                              [7] Check upsampling
                                      |
                                      v
                              [8] Apply 11 detection rules
                                      |
                                      v
                                   SCORE
                                 (0-150 points)
                                      |
                                      v
                              [9] Determine verdict
                                  based on score
                                      |
                                      v
                              END: Report result
```

---

## Scoring System Logic

```
SCORE = 0  (start with clean slate)

For each detection rule:
    IF (rule conditions met)
        THEN SCORE += rule_points

Final SCORE --> Determine VERDICT:

    IF SCORE >= 80
        THEN VERDICT = FAKE_CERTAIN
    
    ELSE IF SCORE >= 50
        THEN VERDICT = FAKE_PROBABLE
    
    ELSE IF SCORE >= 30
        THEN VERDICT = SUSPICIOUS
    
    ELSE
        THEN VERDICT = AUTHENTIC
```

---

## Rule 1: MP3 CBR Detection (50 points)

```
INPUT: cutoff_freq, real_bitrate, cutoff_std, energy_ratio

STEP 1: Check for 20 kHz exception (FFT rounding)
    IF cutoff_freq == 20000 Hz
       AND (energy_ratio > 0.000001 OR cutoff_std == 0)
    THEN 
        SKIP RULE (probably FFT rounding, not MP3)
        RETURN 0 points

STEP 2: Check MP3 signature
    IF cutoff_freq matches MP3 signature (16k, 18k, 19.5k, 20k, 20.5k, 21k)
       AND cutoff_std < 100 Hz (very stable cutoff)
       AND real_bitrate matches expected MP3 bitrate range
    THEN 
        SCORE += 50 points
        SET estimated_mp3_bitrate
    ELSE
        RETURN 0 points
```

**MP3 Signatures:**
- 128 kbps → 16 kHz cutoff
- 192 kbps → 18.8 kHz cutoff
- 256 kbps → 19.5 kHz cutoff
- 320 kbps → 20.5 kHz cutoff

---

## Rule 2: Frequency Deficit (0-30 points)

```
INPUT: cutoff_freq, sample_rate

STEP 1: Determine theoretical maximum
    expected_cutoff = sample_rate / 2 - 1000 Hz
    
    Examples:
        44.1 kHz → 21.05 kHz expected
        48 kHz   → 23 kHz expected
        96 kHz   → 47 kHz expected

STEP 2: Calculate deficit
    deficit = expected_cutoff - cutoff_freq
    
    IF deficit <= 0
        THEN RETURN 0 points (full spectrum present)
    ELSE
        points = deficit / 200
        RETURN min(points, 30)
```

---

## Rule 3: Bitrate Incoherence (50 points)

```
INPUT: real_bitrate, file_duration, cutoff_freq

STEP 1: Calculate expected minimum bitrate
    IF sample_rate == 44100 Hz
        expected_min = 400 kbps
    ELSE IF sample_rate == 48000 Hz
        expected_min = 450 kbps
    ELSE IF sample_rate == 96000 Hz
        expected_min = 900 kbps

STEP 2: Check incoherence
    IF real_bitrate < expected_min
       AND cutoff_freq < (sample_rate/2 - 2000)
       AND duration > 60 seconds
    THEN 
        SCORE += 50 points (inflated file)
    ELSE
        RETURN 0 points
```

---

## Rule 4: Critical Duration Issue (20 points)

```
INPUT: metadata_duration, calculated_duration

STEP 1: Calculate discrepancy
    diff = |metadata_duration - calculated_duration|
    
    IF diff > 1.0 second
       AND metadata_duration > 0
    THEN 
        SCORE += 20 points (encoding error)
    ELSE
        RETURN 0 points
```

---

## Rule 5: Excessive Silence (10 points)

```
INPUT: audio_samples

STEP 1: Count silent samples
    FOR each sample:
        IF |sample| < threshold
            THEN silent_count++

STEP 2: Calculate silence ratio
    silence_ratio = silent_count / total_samples
    
    IF silence_ratio > 0.5 (50% silent)
        THEN SCORE += 10 points
    ELSE
        RETURN 0 points
```

---

## Rule 6: Extreme Clipping (15 points)

```
INPUT: audio_samples, max_value

STEP 1: Count clipped samples
    FOR each sample:
        IF |sample| >= max_value * 0.99
            THEN clipped_count++

STEP 2: Calculate clipping ratio
    clipping_ratio = clipped_count / total_samples
    
    IF clipping_ratio > 0.01 (1% clipped)
        THEN SCORE += 15 points
    ELSE
        RETURN 0 points
```

---

## Rule 7: DC Offset (5 points)

```
INPUT: audio_samples

STEP 1: Calculate average DC offset
    dc_offset = mean(all_samples)
    
    IF |dc_offset| > threshold
        THEN SCORE += 5 points
    ELSE
        RETURN 0 points
```

---

## Rule 8: Spectral Holes (15 points)

```
INPUT: frequency_spectrum

STEP 1: Analyze spectrum for gaps
    FOR each frequency band:
        IF energy < threshold
           AND neighboring_bands_have_energy
        THEN hole_detected = TRUE

STEP 2: Count significant holes
    IF hole_count > threshold
        THEN SCORE += 15 points
    ELSE
        RETURN 0 points
```

---

## Rule 9: Compression Artifacts (20 points)

```
INPUT: frequency_spectrum

STEP 1: Look for artifact patterns
    Check for:
        - Pre-echo artifacts
        - Brick-wall filter residue
        - Quantization noise patterns

STEP 2: Score artifacts
    IF significant_artifacts_detected
        THEN SCORE += 20 points
    ELSE
        RETURN 0 points
```

---

## Rule 10: Fake High-Resolution (25 points)

```
INPUT: sample_rate, bit_depth, spectral_content

STEP 1: Check if file claims high-res
    IF sample_rate > 48000 Hz OR bit_depth > 16
        THEN is_hires_claim = TRUE
    ELSE
        RETURN 0 points

STEP 2: Verify actual content
    IF is_hires_claim
       AND spectral_content_limited (no energy above 20 kHz)
       AND no_24bit_dynamic_range
    THEN 
        SCORE += 25 points (fake hi-res)
    ELSE
        RETURN 0 points
```

---

## Rule 11: Cassette Tape Detection (10 points)

```
INPUT: frequency_spectrum, noise_floor

STEP 1: Look for cassette signatures
    Check for:
        - High frequency rolloff (~12-15 kHz)
        - Tape hiss pattern
        - Dolby noise reduction artifacts

STEP 2: Score cassette indicators
    IF cassette_signature_detected
        THEN SCORE += 10 points
    ELSE
        RETURN 0 points
```

---

## Upsampling Detection Logic

```
INPUT: sample_rate, frequency_spectrum

STEP 1: Check if upsampling is possible
    IF sample_rate <= 48000 Hz
        THEN RETURN not_upsampled (base rate)

STEP 2: Look for hard cutoff at lower frequency
    expected_cutoffs = [22050, 24000] Hz  (44.1k/48k Nyquist)
    
    FOR each expected_cutoff:
        IF hard_cutoff_detected_at(expected_cutoff)
           AND no_significant_energy_above(expected_cutoff)
        THEN 
            is_upsampled = TRUE
            suspected_original_rate = expected_cutoff * 2

STEP 3: Return result
    IF is_upsampled
        THEN MARK FILE as upsampled
    ELSE
        RETURN not_upsampled
```

---

## Quality Issues Detection

```
For each file, check:

[A] Duration Check
    IF |metadata_duration - calculated_duration| > 1.0 sec
        THEN flag: duration_issue

[B] DC Offset Check
    IF |mean(samples)| > threshold
        THEN flag: dc_offset_issue

[C] Silence Check
    IF silence_ratio > 0.5
        THEN flag: silence_issue

[D] Clipping Check
    IF clipping_ratio > 0.01
        THEN flag: clipping_issue
```

---

## Final Verdict Logic

```
INPUT: SCORE, is_corrupted, is_upsampled, quality_flags

STEP 1: Check corruption first
    IF is_corrupted
        THEN VERDICT = CORRUPTED
        RETURN

STEP 2: Determine verdict from score
    IF SCORE >= 80
        THEN 
            VERDICT = FAKE_CERTAIN
            ICON = [XX]
            ACTION = DELETE
    
    ELSE IF SCORE >= 50
        THEN 
            VERDICT = FAKE_PROBABLE
            ICON = [!!]
            ACTION = MANUAL_REVIEW
    
    ELSE IF SCORE >= 30
        THEN 
            VERDICT = SUSPICIOUS
            ICON = [?]
            ACTION = MANUAL_REVIEW
    
    ELSE
        THEN 
            VERDICT = AUTHENTIC
            ICON = [OK]
            ACTION = KEEP

STEP 3: Add quality flags to report
    Append: duration_issue, dc_offset, silence, clipping

STEP 4: Add upsampling flag if detected
    IF is_upsampled
        THEN Append: upsampled_from_{original_rate}
```

---

## Summary Decision Tree

```
                        FILE
                         |
         +---------------+---------------+
         |                               |
    CORRUPTED?                       READABLE
         |                               |
         v                               v
    VERDICT:                        ANALYZE
    CORRUPTED                            |
                          +--------------+--------------+
                          |                             |
                     SPECTRAL                       QUALITY
                     ANALYSIS                        CHECKS
                          |                             |
                    CUTOFF FREQ                    DURATION
                    ENERGY RATIO                   DC OFFSET
                    BITRATE                        SILENCE
                          |                        CLIPPING
                          v                             |
                   APPLY 11 RULES                       |
                          |                             |
                          v                             |
                   CALCULATE SCORE                      |
                    (0-150 pts)                         |
                          |                             |
          +---------------+---------------+             |
          |               |               |             |
      SCORE>=80      SCORE>=50       SCORE<30           |
          |               |               |             |
          v               v               v             v
    FAKE_CERTAIN    FAKE_PROBABLE     AUTHENTIC    (+ FLAGS)
        [XX]            [!!]            [OK]
          |               |               |
       DELETE       MANUAL_REVIEW       KEEP
```

---

## Example: Analyzing a File

```
FILE: suspicious.flac
    |
    v
[1] Read file --> SUCCESS
    |
    v
[2] Metadata:
    - Sample rate: 44100 Hz
    - Bit depth: 16
    - Duration: 180 sec
    |
    v
[3] Spectral analysis:
    - Cutoff freq: 16200 Hz
    - Cutoff std: 45 Hz
    - Energy ratio: 0.000000001
    |
    v
[4] Bitrate:
    - Real bitrate: 850 kbps
    - Expected for 44.1k: ~900 kbps
    |
    v
[5] Apply Rules:

    Rule 1: MP3 CBR Detection
        - Cutoff 16200 Hz matches MP3 128k signature
        - Cutoff std 45 Hz < 100 Hz (stable)
        - Bitrate 850 kbps in MP3 128k range
        - EXCEPTION: energy_ratio near zero (not FFT rounding)
        --> +50 points

    Rule 2: Frequency Deficit
        - Expected: 21050 Hz
        - Actual: 16200 Hz
        - Deficit: 4850 Hz
        - Points: 4850/200 = 24 points (capped at 30)
        --> +24 points

    Rule 3: Bitrate Incoherence
        - Real bitrate 850 kbps > 400 kbps minimum
        --> +0 points

    [Other rules return 0 points]

    TOTAL SCORE: 50 + 24 = 74 points
    |
    v
[6] Determine Verdict:
    - SCORE = 74
    - 50 <= 74 < 80
    --> VERDICT: FAKE_PROBABLE
    --> ICON: [!!]
    --> ACTION: Manual review recommended
    --> REASON: "MP3 128k signature + frequency deficit"
```

---

## Key Principles

1. **Additive Scoring**: Points accumulate for each detected issue
2. **Multiple Evidence**: Higher confidence when multiple rules trigger
3. **Conservative Approach**: 20 kHz cutoff exception prevents false positives
4. **Contextual Analysis**: Rules consider sample rate, bitrate, duration together
5. **Clear Thresholds**:
   - 80+ points = Almost certainly fake
   - 50-79 points = Probably fake
   - 30-49 points = Worth checking
   - <30 points = Likely authentic

---

## Reading the Report

```
[XX] Score 123/100 | FAKE_CERTAIN
     --> Delete this file, definitely a transcode

[!!] Score 72/100 | FAKE_PROBABLE
     --> Very suspicious, manual review recommended

[?] Score 35/100 | SUSPICIOUS
     --> Worth checking, might be edge case

[OK] Score 12/100 | AUTHENTIC
     --> Looks good, keep this file
```

---

*FLAC Detective v0.6.4 - Logic flows like electricity, truth emerges from circuits*
