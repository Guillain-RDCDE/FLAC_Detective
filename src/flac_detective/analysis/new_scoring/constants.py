"""Constants for the new FLAC fake detection scoring system."""

# MP3 Standard Bitrates (kbps) - IMMUTABLE
MP3_STANDARD_BITRATES = [96, 128, 160, 192, 224, 256, 320]

# MP3 Bitrate Signatures (Frequency Ranges)
# Format: (bitrate_kbps, min_freq, max_freq)
# Ranges are slightly overlapping or contiguous to catch edge cases
MP3_SIGNATURES = [
    (320, 19500, 21500),  # 320 kbps: ~19.5-21.5 kHz (often 20.5k)
    (256, 18500, 19500),  # 256 kbps: ~18.5-19.5 kHz
    (224, 17500, 18500),  # 224 kbps: ~17.5-18.5 kHz
    (192, 16500, 17500),  # 192 kbps: ~16.5-17.5 kHz
    (160, 15500, 16500),  # 160 kbps: ~15.5-16.5 kHz
    (128, 10000, 15500),  # 128 kbps or lower: < 15.5 kHz
]

# Bitrate tolerance (kbps)
BITRATE_TOLERANCE = 10

# Score thresholds
SCORE_FAKE_CERTAIN = 86
SCORE_SUSPICIOUS = 61
SCORE_WARNING = 31
SCORE_AUTHENTIC = 30

# Variance threshold for authenticity (kbps)
VARIANCE_THRESHOLD = 100

# High bitrate threshold (kbps)
HIGH_BITRATE_THRESHOLD = 1000

# Coherent bitrate threshold (kbps)
COHERENT_BITRATE_THRESHOLD = 800

# Coherence tolerance (kbps)
COHERENCE_TOLERANCE = 100

# Apparent bitrate threshold for Rule 3 (kbps)
SEUIL_BITRATE_APPARENT_ELEVE = 600

# Default number of segments for variance calculation
DEFAULT_VARIANCE_SEGMENTS = 10

# Minimum segments for variance calculation
MIN_VARIANCE_SEGMENTS = 1

# Cutoff frequency thresholds by sample rate (Hz)
CUTOFF_THRESHOLDS = {
    44100: 20000,
    48000: 22000,
    88200: 40000,
    96000: 44000,
    176400: 80000,
    192000: 88000,
}

# Nyquist percentage for unknown sample rates
NYQUIST_PERCENTAGE = 0.45
