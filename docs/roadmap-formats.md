# Roadmap: multi-format support (WAV / ALAC / APE)

> Design note for the v0.15+ work of widening FLAC Detective beyond `.flac`.
> Status: WAV targeted for v0.15; ALAC/APE later. Written after a scoping pass —
> see the commit history around v0.14 for context.

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
| **WAV** | soundfile (already) | **low** (~½ day) | high — common | **v0.15** |
| **ALAC** (`.m4a`) | ffmpeg / audioread (new path) | medium (~1–2 d) | medium — Apple | v0.16 |
| **APE** (`.ape`) | ffmpeg (new path) | medium-high | low — niche | on request |

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

## Out of scope (and why)
- **Detecting AAC/Opus/Vorbis → lossless transcodes** is a *detection* limit, not a
  format-input one, and is near-impossible at high bitrate (see `ml/README.md` —
  the tool's measured blind spot). Supporting a container ≠ being able to judge it.
