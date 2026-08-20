# Encoder provenance — what generated our fixtures, and how well we can prove it

Provir's `BUILD.md` (archived in `ml/exchange/`) states the principle this file
applies: **the encoder build is load-bearing for encoder-specific claims.** A
detector that brackets artifacts by encoder version, then generates its own
fixtures with binaries of unrecorded provenance, is arguing a principle to others
that it has not applied to itself. His hashed LAME register plus our Musepack
r495-vs-r475 finding compress into one rule:

> **Banner, source revision and build date are three independent axes, and a
> version string pins none of them.** (Eleven of his binaries carry nine distinct
> banners; two byte-different builds twenty years apart print the same string.
> Our Debian mpcenc shares Provir's `1.30.1` banner and is built from a later
> source revision.)

## The rule going forward

Every fixture-generating workflow records the encoder **in the artifact next to
the CSV it produced** — package version, binary sha256, banner. In force:

| generator | provenance |
|---|---|
| Musepack arm (`musepack-arm.yml`) | `musepack_provenance.txt` in the artifact — first recording already earned its keep (r495 vs Provir's r475) |
| CoreAudio arm (`coreaudio-arm.yml`) | `coreaudio_provenance.txt` in the artifact (OS build number stands in for source revision — the encoder is the OS framework) |

## The retroactive gap, disclosed rather than patched silently

The audit corpus (80 certified sources × 9 codecs, built 2026-08) and the
external-encoder generalisation set (June 2026) were generated **before** this
rule existed. Nothing was hashed at generation time. What follows is what the
generating machines can still attest on 2026-08-20, stated as *probable* identity
— the binaries present today, predating the corpus builds and unchanged since —
never as proven identity. That distinction is the entire point of the rule.

### Local machine (audit corpus: `aac_ff*`, `mp3_*`, `opus_256`, `vorbis_q8`)

```
ffmpeg 8.1-full_build-www.gyan.dev (gcc 15.2.0, MSYS2)
  sha256 d1e2a156261ecc67...   223,360,000 b   installed 2026-03-17 (predates all corpus builds)
flac 1.x (reference encoder for FLAC containers)
  sha256 ff23d9cbc11d18c0...   339,456 b       installed 2025-02-11
```

### Local machine (audit corpus: `aacmf_256`)

MediaFoundation's encoder is the OS. `Windows 11 Pro, build 10.0.26200` — same
situation as CoreAudio: the OS build number is the closest available analogue of
a source revision.

### Hetzner box (external-encoder zoo, `ml/generate_transcodes_external.py`)

Captured over SSH on 2026-08-20, Debian/Ubuntu packages unchanged since install:

```
lame    3.100 (pkg 3.100-6build1)        sha256 2f0c5b94ed04760c...    96,496 b
oggenc  vorbis-tools 1.4.2 (1.4.2-2)     sha256 07266134c1d0f15c...    73,816 b
opusenc opus-tools 0.2, libopus 1.4      sha256 6f73a78ca5fa741d...    61,504 b
fdkaac  1.0.0 (1.0.0-1build1)            sha256 15e4f970ccc08f1d...    90,624 b
ffmpeg  (decode side)                    sha256 ed16af623947494a...   342,488 b
```

Worth stating for the exchange: our LAME is **3.100** — the modern era. Every
LAME-specific claim in this repository is therefore about 3.100 behaviour, and
none of it transfers to the 3.9x-era builds Provir's wild corpus contains, where
early `-b 320` applies no lowpass at all. His exhibit's exact encoder is pinned
in `ml/exchange/README.md` (`lame3.92`, sha256 `cb2cdfde7b170d90...`, built
2002-04-16), so the era gap is now measurable from both sides.
