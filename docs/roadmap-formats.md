# Roadmap: multi-format support (WAV / ALAC / APE)

> Design note for the v0.15+ work of widening FLAC Detective beyond `.flac`.
> Status: **WAV shipped in v0.15.0; ALAC + APE shipped in v0.16.0** (decode-façade
> + bitrate-from-original wiring). Kept as the design record. See the commit history
> around v0.14 for the original scoping context.

## The key insight: detection is codec-agnostic

The transcode signal FLAC Detective looks for — the MP3 **spectral cliff**, the
cutoff vs. sample rate, compression artefacts (pre-echo, aliasing), and the CNN
mel-spectrogram — all operate on the **decoded PCM**. They don't care what
container delivered the samples. So widening to other *lossless* containers is
overwhelmingly an **input/output** problem, not a detection-science problem.

What is actually coupled to FLAC:

| Concern | Location | Notes |
|---|---|---|
| File discovery | `main.py` (`suffix == ".flac"`) | trivial: widen the accepted extensions |
| Audio decoding | `analysis/new_scoring/audio_loader.py` (soundfile) | WAV is free (libsndfile); ALAC/APE need another decoder |
| Metadata | `analysis/metadata.py` (`mutagen.flac.FLAC`) | needs a per-format reader or `mutagen.File` |
| Container-bitrate rules | `analysis/new_scoring/bitrate.py` + Rules 1/3 | **format-dependent semantics — see below** |

## The worldview gotcha: non-FLAC is currently treated as *fake*

The bigger coupling isn't technical, it's philosophical. Today the tool does not
merely skip non-FLAC files — `main._create_non_flac_result()` reports them with
**score 100, verdict `NON_FLAC`, "must be replaced with an authentic FLAC."** The
tool's worldview is *"a lossless collection is made of FLACs; anything else is
suspect."*

So supporting WAV means a deliberate **product shift**: WAV moves from *"rejected,
replace it"* to *"a first-class lossless format we analyse on its own merits"* (is
this WAV a genuine recording, or an MP3→WAV fake?). Concretely, the scanner must
route `.wav` into the **analysis** list instead of the non-FLAC reject list, while
ALAC/APE (until their decoders land) stay in the reject list. This is a decision
to make explicitly, not a silent glob change.

## The design gotcha: container-bitrate rules

Rules **1** (MP3-bitrate signature) and **3** (source-vs-container) reason about a
*lossless-compressed* container: a real FLAC of clean audio compresses to a
genuinely lossless size, while an MP3-sourced fake compresses smaller / sits in a
recognisable bitrate band. This logic is meaningful for FLAC and for other
**lossless-compressed** formats (ALAC, APE) — but **not for uncompressed WAV**: a
WAV transcoded from an MP3 still has the full uncompressed bitrate (~1411 kbps),
so the "compressible → suspect" signal disappears.

**Decision:** for uncompressed formats, **gate Rules 1 and 3 off** and rely on the
spectral rules (cutoff / artefacts / CNN), which still see the MP3 cliff. There is
already a precedent for conditionally disabling Rule 1 — Rule 11 (cassette) does it
for legitimate analogue sources — so the mechanism exists.

## Effort and sequencing

| Format | Decoder | Effort | Value | When |
|---|---|---|---|---|
| **WAV** | soundfile (already) | **low** (~½ day) | high — common | ✅ v0.15.0 |
| **ALAC** (`.m4a`) | ffmpeg decode-façade | medium (~1–2 d) | medium — Apple | ✅ v0.16.0 |
| **APE** (`.ape`) | ffmpeg decode-façade | medium-high | low — niche | ✅ v0.16.0 |

### WAV (v0.15) — concretely
1. Widen file discovery to `.wav` (+ keep `.flac`).
2. Metadata: read WAV header (soundfile `sf.info` gives sample rate / channels /
   subtype → bit depth); duration from frames.
3. Gate Rules 1 & 3 when the input is uncompressed (no lossless-compression signal).
4. Tests: a synthetic clean WAV (authentic) and an MP3→WAV fake (flagged by the
   cliff), plus a regression check that FLAC behaviour is unchanged.

### The structural investment (unlocks ALAC/APE cleanly)
Refactor `audio_loader` to be **format-agnostic**: try soundfile first, fall back
to an ffmpeg-decode path for containers libsndfile can't read. Once that exists,
ALAC and APE are mostly "add the extension + a metadata reader".

**Landed (v0.16 foundation):** `analysis/audio_formats.py` — the isolated,
tested decode-façade. `ffmpeg_available()`, `probe_codec()` (ffprobe
`codec_name`), `is_analysable_lossless()` (FLAC/WAV native; ALAC/APE/etc. by
probe; an **AAC** `.m4a` correctly returns False → stays a reject),
`needs_ffmpeg_decode()`, and `decode_to_wav()` (ffmpeg `-i … -vn temp.wav`).
ffmpeg is a **hard requirement for non-native formats only** — FLAC/WAV never
touch it. Tests in `tests/test_audio_formats.py` (skip if ffmpeg absent).

### ALAC/APE wiring — the bitrate-from-original subtlety (must get right)
The decode-façade lets the pipeline treat ALAC/APE as a plain WAV for the
**spectral** rules. But there's a trap in the **bitrate** path:

- For a *lossless-compressed* source (FLAC/ALAC/APE), `real_bitrate` =
  `original_compressed_size × 8 / duration`, and the
  `real/apparent < 0.92` ratio is what keeps Rules 1 & 3 **on** (the
  "compressible → could be a fake" signal).
- If we naively feed the **decoded WAV** to the calculator, it computes
  `real_bitrate` from the *uncompressed* WAV → ratio ≈ 1.0 → the file is
  mistaken for uncompressed → **R1/R3 gate off** → we'd miss ALAC-wrapped fakes.

So the calculator must derive `real_bitrate` from the **original `.m4a`/`.ape`
size**, while the rules read audio from the **decoded WAV**. Today
`new_calculate_score(filepath, …)` derives bitrate from the *same* `filepath`
the rules load audio from — one path can't be both (the original isn't
soundfile-readable). The wiring therefore needs the original size/bitrate
threaded in separately (e.g. an explicit `source_size`/pre-computed
bitrate-metrics argument), not just a temp-path swap. This is the careful
core-path change that distinguishes ALAC from the trivial WAV case.

Metadata likewise: `.m4a` → `mutagen.mp4` (or ffprobe), `.ape` → ffprobe, since
`mutagen.flac.FLAC` / `soundfile.info` can't read them.

## Out of scope (and why)
- **Detecting AAC/Opus/Vorbis → lossless transcodes** is a *detection* limit, not a
  format-input one. As of v1.2.0 this is **less of a wall than once thought**: the CNN
  (Rule 12) separates these codecs from genuine FLAC on full-range audio (ROC-AUC
  0.94–0.99), surfaced via the `--deep` flag as WARNING. The genuine fundamental limit is
  **band-limited** material of any codec (baroque, 1920s, solo acoustic), where a transcode
  removes almost nothing — see `ml/README.md`. Supporting a container ≠ being able to judge
  it, but for these codecs the gap is now mostly closed on full-range audio.
