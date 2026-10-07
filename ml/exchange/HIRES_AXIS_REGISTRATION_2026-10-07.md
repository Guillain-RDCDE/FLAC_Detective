# The hi-res axis: upsampling, padded depth, 32-bit — registered 2026-10-07, before the engine runs

Written and committed **before the before- and after-passes run**, per the
convention. Everything below was derived by reading the code and by building
the corpora; no verdict has been computed on them by either engine.

---

## Where this comes from

Issue #12, closed 2026-10-07. After confirming the 2.1.0 fix, the reporter
(barthess) asked three things: is there a training set at other sample rates
than 44.1 kHz (48, 96, 192); at other depths than 16 bits (24, 32, float); and
does the tool read **upsampling**, not only transcoding.

The honest answer given there: the hi-res axis exists (`hires_verdict`:
`UPSAMPLED`, `PADDED_DEPTH`, `UPSAMPLED_AND_PADDED`, `GENUINE_HIRES`,
`NOT_HIRES`), but it has only ever been checked on synthetic signals
(`tests/test_hires.py`) and on 54 unlabelled library files (2.0.0, "harmless,
not effective"). It has **never had a registration**. This is it.

## What the code says before anything is measured

Read on `d29699d` (2.1.0 + Dependabot #15):

1. **`BitDepthDetector` reads the first 10,000 frames of channel 0 only**
   (`analysis/quality.py`), ~0.1 s at 96 kHz. A genuine 24-bit track that opens
   with digital silence or a fade-in reads "16-bit exact" on that chunk and is
   labelled `PADDED_DEPTH`. Expected: **false positives on genuine 24-bit
   files**, number unknown until measured. It also knows only 16 or 24: a
   32-bit container is never estimated.
2. **32-bit integer FLAC cannot be opened**: libsndfile 1.2.2 (the `soundfile`
   wheel) implements FLAC at PCM_S8/16/24 only — "File contains data in an
   unimplemented format" on a file `flac 1.5.0` encodes and verifies (`flac -t`
   ok). `needs_ffmpeg_decode` routes by suffix, so a `.flac` never reaches the
   ffmpeg façade that already folds 32-bit and float sources to 24-bit for
   ALAC/TrueHD. Expected: **ERROR** (or whatever the repair path does, to be
   reported as found). A 32-bit **WAV** (PCM_32, FLOAT) is readable by
   libsndfile and is routed natively; its metadata reads 32 bits; the depth
   detector then tests "16-bit exact" only.
3. **`detect_upsampling` reads the first 30 s, mono-summed**, finds the content
   edge (last smoothed bin within 40 dB of the in-band median), snaps it to a
   standard Nyquist (±6 %), and requires the floor above to sit **70 dB under
   the in-band reference**. A plain upsample (no dither) leaves the resampler's
   stopband up there (≈ −140 dB): caught. A 24-bit upsample finished with
   **noise-shaped dither** pushes shaped noise above 22 kHz: expected to be
   **missed** by the silent-floor test. This is the evasion a seller who knows
   what Spek shows would use.
4. **The hi-res verdict is not printed in the text report** (default and
   `--advanced`): it reaches the CSV, the GUI, the JSON and `plain_explanation`
   (easy mode) only. A command-line user never sees `UPSAMPLED`.
5. The transcode axis at 96/192 kHz: Rule 1 and the container window read a
   cutoff against the file's own Nyquist. An upsampled CD has a 22.05 kHz
   wall under a 48 kHz Nyquist. Whether the transcode rules read that wall as
   a lossy signature is **unknown**; it is measured here, not assumed.

## Corpora

**Fake arm — truth known to the bit (168 files).** The 28 attested CD tracks
(`fd-attested-cd`, AccurateRip / owner-attested, 44.1 kHz 16-bit, 28/28
AUTHENTIC since 1.17.0) through six recipes (`D:/fd-hires/build_fake_arm.py`,
ffmpeg 8.1):

| arm | recipe | truth |
|---|---|---|
| `up96_soxr` | 44.1 → 96 kHz, soxr, 24-bit, no dither | upsampled |
| `up96_swr` | 44.1 → 96 kHz, swresample, 24-bit, no dither | upsampled |
| `up96_shaped` | 44.1 → 96 kHz, soxr, 24-bit, **shibata noise-shaped dither** | upsampled (evasion) |
| `up192_soxr` | 44.1 → 192 kHz, soxr, 24-bit, no dither | upsampled |
| `pad24` | 44.1 kHz, 16-bit data in a 24-bit container | padded |
| `up96_pad24` | 44.1 → 96 kHz at 16-bit, then 24-bit container | upsampled and padded |

**32-bit / float (3 files, `D:/fd-hires/bits`).** 60 s of one attested track
as 32-bit integer FLAC (`flac 1.5.0`), 32-bit integer WAV and 32-bit float WAV.
Truth: 16-bit content in a 32-bit container, genuine lossless.

**Genuine control, labelled (28).** The 28 attested tracks themselves: the
transcode axis must not move, and the hi-res axis must read `NOT_HIRES`.

**Genuine hi-res, unlabelled stress (172).** Every non-CD file of the library
sample (`fd-r1w/library_sample.txt`, one track per album): 45 at 96 kHz, 5 at
192, 1 at 88.2, 1 at 64; 35 at 48 kHz/24, 24 at 48/16; 83 at 44.1/24; two at
96/16 and 192/16. Provenance not certified, so **no numeric criterion**: every
file the hi-res axis flags, before or after, is inspected by hand with an
independent instrument (`truedepth.py`: trailing-zero bits over the WHOLE
file, no engine code) and named in the results. **There is no certified
external hi-res source in this registration**: the 2L test bench is offline
(site renovation, checked 2026-10-07), the other free sources found are
paywalled, composer-hosted on Google Drive, or silent on native resolution.
That gap is stated, not filled.

Torch live only: the hi-res axis is independent of Rule 12, and the change
touches no scoring rule.

## The change

* **Depth detector reads the whole file in windows**, not the first 0.1 s:
  eight windows spread over the file, the decision "16-bit exact" taken only on
  windows that carry non-zero audio, and only if every such window agrees. It
  estimates 16 / 24 / 32 (a 32-bit container is tested at both boundaries).
* **32-bit integer FLAC is decoded through the ffmpeg façade** when libsndfile
  refuses it (the façade already writes 24-bit PCM for anything wider), so the
  file is analysed instead of erroring; metadata keeps the declared 32 bits.
* **The text report prints the hi-res verdict** (default and advanced) for any
  file whose `hires_verdict` is not `NOT_HIRES`.
* **The upsampling test is not changed by this registration.** If the shaped
  arm is missed, that is reported as a limit, and any instrument for it gets
  its own registration (criteria first, then design), as Rule 16 did.
* The transcode scoring rules are untouched.

## Criteria, registered before the passes run

Before = `d29699d` (worktree `fd-hires-base`); after = the same plus this
change only. `FLACAnalyzer.analyze_file`, default mode, 30 s, torch live.

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **H1** | attested 28, transcode verdict moves (before → after) | **0** | any |
| **H2** | attested 28, `hires_verdict` | **NOT_HIRES** 28/28, both | any other |
| **H3** | library 172, transcode verdict moves | **0** | any |
| **H4** | library 24-bit files read `PADDED_DEPTH` **before** | **> 0**, every one a false positive (true depth 24 by `truedepth.py`) | — (a reading of the defect) |
| **H5** | library files read `PADDED_DEPTH` **after** | exactly the files `truedepth.py` reads as 16-bit content in a 24-bit container (expected: few or none) | any file flagged whose true depth is > 16, or any 16-in-24 file missed |
| **H6** | `pad24` 28, `up96_pad24` 28: padded read | **28/28** each, before and after | any under 28 after |
| **H7** | `up96_soxr`, `up96_swr`, `up192_soxr`: `UPSAMPLED` (or `_AND_PADDED`) | **≥ 26/28** each, before and after | any arm under 24 after, or any detection lost |
| **H8** | `up96_shaped`: upsampled read | **expected mostly missed** (prediction: ≤ 14/28 before); reported, not a refusal | — |
| **H9** | fake arms 168, transcode axis | **0 convicted** (SUSPICIOUS / FAKE_CERTAIN), before and after: upsampled lossless CD audio is not a transcode | reported if before > 0 (pre-existing); refuse if after > before |
| **H10** | 32-bit FLAC | before: ERROR (reported as found); after: analysed, transcode AUTHENTIC, `hires_verdict` **PADDED_DEPTH** (estimated 16 in 32) | after not analysed, or convicted |
| **H11** | 32-bit WAV, float WAV | after: analysed, `PADDED_DEPTH` (16 in 32) | not analysed or convicted |
| **H12** | library hi-res flagged `UPSAMPLED` after | each named and inspected by hand (spectrum: cliff at a standard Nyquist with a silent floor); every one either a plausible upsample or a stated false positive | a stated false positive that a repair could not be registered for is a limit, not a refusal |
| **H13** | text report shows the hi-res line | on every non-`NOT_HIRES` file, default and advanced (unit test) | missing |
| **H14** | cost of the depth windows | reported (eight 10,000-frame reads) | — |
| **H15** | full test suite, four gates, Sphinx `-W` | green | any red |

H1, H3, H5, H6, H7 (after), H9 (after > before), H10, H11, H13 or H15 failing
refuses the change. H4 and H8 are readings of the before-engine and are
reported as found. The results are appended below after the passes, everything
above left as committed.

---

## Amendment 1 — registered 2026-10-07 after the before-pass on the fake arms, before any after-pass

The before-pass on the fake arms (engine `d29699d`) read **0 of 28** of
`up192_soxr` as upsampled, against the prediction of ≥ 26. A probe of the
instrument's two numbers on every hi-res file (`D:/fd-hires/upsample_probe.py`,
no verdict computed) found the cause by reading, not by trial: the in-band
reference is the median over **5-45 % of the file's own Nyquist**, which at
192 kHz is 4.8-43 kHz — mostly the empty band of the upsample itself. The
median sinks into the void, and the content edge ("within 40 dB of the
reference") is found at Nyquist: the file reads genuine. At 96 kHz the band is
2.4-21.6 kHz and the test works (27 of 28 snap to 44.1 kHz).

Two more things the probe showed, written down before anything is changed:

* **The `up96_shaped` arm as first built was no evasion arm.** ffmpeg applies
  `dither_method` only when it reduces the sample format; with a 32-bit output
  it applied none, and the arm's floors are identical to `up96_soxr` (both
  −71 to −132 dB). Its before-pass rows are a duplicate of `up96_soxr` and are
  not counted. **Rebuilt as `up96_shaped16`**: soxr to 96 kHz, shibata dither at
  a 16-bit output, stored in a 24-bit container (`build_shaped16.py`). On the
  probe its floors above the cliff run **−53 to −80 dB** (two files read no
  edge at all: the shaped noise is within 40 dB of the reference), so under
  the −70 dB bar about half of it will be read. That is the evasion.
* **Candidate source rates.** For a 96 kHz file the instrument also tries
  88.2 kHz, whose Nyquist (44.1 kHz) is inside the file's own rolloff; six
  library files snap to it with no readable band above. Not a source.

### The change (amendment)

1. The reference band becomes **1 kHz to 0.9 × 22.05 kHz**: content every
   candidate source carries, at every file rate.
2. A candidate source rate must be **≤ the file rate / 1.5** (96 kHz: 44.1 and
   48; 192 kHz: 44.1, 48, 88.2, 96).
3. **The −70 dB silent-floor bar does not move.** The unlabelled 96 kHz library
   files that snap to a candidate rate under the new reference read floors of
   −42 to −68 dB except the two already flagged (−81, −89); the bar stays above
   every one of them by 2 dB or more, and moving it would be a calibration on
   unlabelled files.

Nothing else in `detect_upsampling` changes; the transcode rules do not read
it.

### Criteria added

| id | criterion | predicted | refuse if |
|---|---|---|---|
| **H7a** | `up192_soxr` read upsampled, after | **27/28** (the 28th: no edge within ±6 % of 22.05 kHz, named) | < 26 |
| **H7b** | `up96_soxr`, `up96_swr` read upsampled, after | **27/28** each, none lost | < 26, or any lost |
| **H6a** | `up96_pad24` read upsampled (and padded), after | **≥ 18/28** (probe: 20 floors under −70; the 16-bit quantisation floor is the miss) | < 18 |
| **H8a** | `up96_shaped16` read upsampled, before and after | **about half** (probe: 15 floors under −70); reported, not a refusal | — |
| **H12a** | library files read `UPSAMPLED` after | **exactly the two read before** (Thylacine *Fauré*, Portishead *Machine gun* copy 02); every other file that snaps to a candidate rate stays `GENUINE_HIRES` | any other file flagged |
| **H12b** | library files that snapped to 88.2 kHz before (6) | `GENUINE_HIRES` after, as before | any flagged |

H7a, H7b, H6a, H12a or H12b failing refuses the amendment, not the registration.
The after-passes run once, on the engine with the registration's change and
this amendment together.
