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

# Score thresholds (verdict labels only — no scoring logic depends on these).
# SUSPICIOUS lowered 61 -> 55 (v0.15.1): a score-distribution study found real
# transcodes pile up with a *median of 58*, i.e. inside the old WARNING band, so
# genuine fakes were being under-called "WARNING (maybe legit)". Moving the floor
# to 55 reclaims them as SUSPICIOUS for ~+5 pp actionable recall, while authentic
# false positives stay ~1% (≈95% of authentic files score 0; p99 = 59). See
# ml/analyze_warning_band.py.
SCORE_FAKE_CERTAIN = 86
SCORE_SUSPICIOUS = 55
SCORE_WARNING = 31
SCORE_AUTHENTIC = 30

# ========== CONVICTION: CORROBORATION, NOT JUST POINTS (v1.9) ==========
# A conviction requires this many INDEPENDENT evidence families (see evidence.py),
# not merely a high total. The audit's finding was unambiguous: all three false
# convictions on 80 certified-genuine files, and all 26 convictions on the
# 320 kbps MP3 arm, came from Rules 1 and 3 contributing +50 each — and Rule 3
# reads the bitrate Rule 1 inferred. One measurement, counted twice, clearing 86
# unaided. No threshold can separate that from real evidence, because the
# arithmetic is identical; only counting sources can.
CONVICTION_MIN_FAMILIES = 2

# With two independent families agreeing, the points bar drops from 86. Set from
# measurement — see ml/README.md, "Choosing the corroborated bar": the value is
# chosen against the false-conviction rate on genuine material, not against how
# many fakes it catches.
CONVICTION_MIN_SCORE = 55

# A family must CONTRIBUTE this much to count as a witness (v1.10).
#
# v1.9 counted any family with a single positive point. That let a 16-point CNN
# reading legitimise 112 points of doubled spectral evidence and convict a genuine
# 2003 audience recording — the one false conviction in Provir's blind return.
# A witness that mumbles is not a second witness.
MIN_FAMILY_CONTRIBUTION = 20

# Rule 11 cassette evidence needed to protect a file (cancel Rule 1, apply -40).
# Lowered 30 -> 15 in v1.8 when test 11C was removed: 11C awarded a flat +15 to
# essentially every file (it keyed off Rule 9C, which measured AUC 0.497), so
# dropping the threshold by the same amount leaves the real tests' weights
# untouched. See rules/cassette.py.
#
# Raised 15 -> 25 in v1.13.1 by the identical argument, in the other direction.
# TEST 11D subtracted 10 for a "very stable" cutoff, which on a 250 Hz reporting
# grid means "the windows landed in one cell" — the ordinary case, and for every
# file of 90 s or less it was not even a reading (the wander is not computable
# from one window; it was returned as 0.0). That near-constant -10 had been
# absorbed into this gate. Measured before it was touched: removing it alone
# cost 44 of 132 files their conviction, against a registered bound of 5, so it
# moves into the threshold instead. Every other test keeps exactly the weight it
# had, and on both measurement corpora (every file 60 s, so every wander a NaN)
# not one verdict moves. See ml/exchange/R11D_ABSENCE_REGISTRATION_2026-08-30.md.
CASSETTE_THRESHOLD = 25

# Cutoff wander below which the spectrum counts as stable, in Hz. ONE definition,
# read by two rules that must not disagree about the instrument's quantum:
# Rule 1's gate A (skip on a variable spectrum) and Rule 11's TEST 11D (tape
# wow/flutter). ``detect_cutoff`` quantises to 250 Hz slice cells, so a
# rock-stable wall sitting on a cell boundary oscillates one cell and reads up
# to 125 Hz (50/50 between adjacent cells; 117.9 with the three windows
# ``analyze_spectrum`` samples, measured on a wild wall that had not moved).
# 130 is the smallest round figure above that one-cell wander: grid arithmetic,
# not a corpus fit. Lived inside apply_rule_1 until v1.13.1, where 11D was found
# reading the same statistic with a 50 Hz bound and calling one grid cell
# "wow/flutter".
CUTOFF_VARIANCE_THRESHOLD = 130.0

# Variance threshold for authenticity (kbps)
VARIANCE_THRESHOLD = 100

# High bitrate threshold (kbps)
HIGH_BITRATE_THRESHOLD = 1000

# Coherent bitrate threshold (kbps)
COHERENT_BITRATE_THRESHOLD = 800

# Coherence tolerance (kbps)
COHERENCE_TOLERANCE = 100

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
# ========== RULE 1 ENHANCEMENT: Minimum Container Bitrate Thresholds ==========
# Authentic FLAC files have minimum bitrates based on audio quality
# MP3 sources recompressed as FLAC show artificially low bitrates

# Absolute minimum for MP3 source detection (kbps)
# Files below this are almost certainly from low-bitrate MP3 sources
MIN_BITRATE_FOR_AUTHENTIC_FLAC = 160

# For stereo 16-bit 44.1kHz FLAC (most common format)
# Apparent bitrate = 44100 Hz * 16 bits * 2 channels / 1000 = 1411.2 kbps
# Real bitrate should be 40-70% of apparent (due to FLAC compression)
# So real bitrate range: 564-988 kbps (typical: 700-800 kbps)
# Anything significantly below 320 kbps is suspicious

# Red flag: Files with container bitrate < 160 kbps
# These are typically MP3 sources that were upscaled to FLAC
BITRATE_RED_FLAG_THRESHOLD = 160

# Extreme red flag: Files with container bitrate < 128 kbps
# These are definitely from very low-quality MP3 sources (or worse)
BITRATE_CRITICAL_THRESHOLD = 128
