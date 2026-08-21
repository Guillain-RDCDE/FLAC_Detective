# The 2026-08 blind exchange set — committed bytes for a published hash

`MANIFEST.sha256` lists all 599 files of the FLAC Detective side of the blind
exchange with Provir (Jamie Dodd): SHA-256 and byte length per file, produced by
`ml/freeze_exchange_set.py` on 2026-08-15.

Self-hash of this manifest, for citing in correspondence:

```
0318d5faa24b82286f97dff346346ad2707be6c903674686daa6c7e0e8400c24
```

## Why this file is in the repository and the audio is not

The audio is ~3 GB and lives in the gitignored `Temp/` directory. Until v1.10 the
manifest lived there too — which means the hash chain for a sealed artefact had
no committed anchor at all. Any cleanup of `Temp/` would have destroyed the only
authoritative copy of what was sealed, and there would have been no way to prove
after the fact what the published hashes referred to.

That gap was not hypothetical. Jamie hit the same one from the other side on
2026-08-17: his arm-2 spec no longer matched the hash he had published, because a
project-wide rename (VerifID -> Provir) had rewritten a path inside it along with
376 other files. He recovered the sealed bytes only because LinkedIn had retained
his own sent attachment. His conclusion, which applies here word for word:

> Publishing a hash is worth nothing if you don't commit the bytes in the same
> action.

And the failure mode behind it:

> A bulk rename is a content edit to every sealed document it touches.

## Verifying

Re-verified in full on 2026-08-17 against the frozen audio: **599 files checked,
0 missing, 0 divergent.**

```bash
cd Temp && sha256sum -c ../ml/exchange/MANIFEST.sha256
```

## What is deliberately absent

The answer key (`fd-exchange-2026-08-LABELS.json`, which maps each file id to its
codec arm) is **not** in this repository and must never be. It is covered by the
`*-LABELS.json` rule in `.gitignore`. A blind exchange stops being blind the
moment the key is published, and the manifest is exactly the artefact that lets
the other side verify integrity *without* it.


## Known defect: 599 rows, 589 distinct files

Disclosed 2026-08-18, found by Jamie Dodd by sorting this manifest.

Ten digests appear twice. They are not ten scattered accidents: they are **one
entire source group** — the genuine file and all nine of its transcodes —
present twice under two sets of ids.

```
0104 == 0219   0178 == 0295   0179 == 0305   0190 == 0494   0202 == 0408
0270 == 0303   0293 == 0573   0365 == 0491   0478 == 0547   0562 == 0577
```

**Cause.** Two Internet Archive items hold the same taper's same track — one
named `…-matrix-…`, the other `…-matrix2-…`. The corpus dedup keyed on the item
identifier, so both passed as independent recordings. Clustering by content gives
57 groups of ten, one of nine, and one of twenty; the set is 59 source recordings,
not 60.

**Consequences, both mild and both real.** Per-arm denominators read 60 when one
recording is counted twice in every arm, genuine included — the corrected rates
are in `CHANGELOG.md` and `ml/README.md`, and nothing material moved. And the
repeated hashes are a leak in themselves: sorting this file reveals that those
twenty ids carry only ten distinct labels, without touching the audio.

**Why it is not re-frozen.** Verdicts have already been exchanged against these
exact ids. Re-freezing would invalidate a comparison that is already made, so the
set stays as shipped and the defect is published instead.

**The fix, at the level of the class.** `ml/freeze_exchange_set.py` had already
*computed* every digest — it writes them here — and never compared them to each
other. It ran a careful check for metadata tags, which looks outward at what might
leak, and no check at all on what it had just produced. `audit_own_output()` now
refuses to ship a set whose digests repeat, and warns when a source contributes
fewer arms than its peers. `tests/test_exchange_set_integrity.py` pins the shipped
counts so this defect cannot be quietly widened.


## Second known defect: the Opus arm leaks its sample rate

Found 2026-08-18 while scoring Provir's return, in his own evidence column.

`opus_256` is **100 % at 48 000 Hz**. Every other arm and the genuine files keep
the source rate — 78 % at 44 100 Hz. Opus/CELT works at 48 kHz whatever it is fed,
and the round-trip never resampled back, so **every Opus file in this set is
identifiable without decoding a single sample.** Provir's return carries an
`AI_SR_48000` flag on 100 % of them.

There is a milder second case in the same column. MP3 tops out at 48 kHz, so the
five 96 kHz sources were silently downsampled: the MP3 arms hold 22 % at 48 kHz
and 0 % at 96 kHz, against genuine's 13 % and 8 %. "48 kHz with no 96 kHz
counterpart" is therefore a partial tell on those arms too.

**What it invalidates, measured rather than assumed.** Not as much as it might.
FLAC Detective's own Opus numbers are unaffected: on the 8 sources that were
already 48 kHz — where nothing changed — it flags 50.0 %, against 48.1 % on the 52
that were resampled. Flat, so the engine is not reading the container. Provir's
Opus result survives too, and for a better reason: all 60 Opus files carry
non-trivial evidence independent of the rate flag (`HF_SEAM` at 100 %, his MP3
conjunction at 98 %), so his 100 % there is real detection rather than a metadata
shortcut.

**The class, for the third time.** Encoder tags leaked first, repeated digests
second, a container property third. Each time the freeze checked what someone had
thought of, and not what it had just produced. `_audit_sample_rates()` now refuses
any set where an arm's sample-rate distribution is one the genuine arm does not
share — stated as a general rule rather than as a special case for Opus, since the
special cases are exactly what keeps being missed. Verified against this set: it
rejects it.


---

# Protocol for the next blind exchange

Agreed after three leaks in one set. Jamie Dodd's observation is the reason for
the change, and it is the whole argument:

> All three were container-side, and none was findable by the party who built the
> corpus.

Encoder tags. Repeated digests. Sample rate. Each time the freeze verified what
someone had thought of, and each time the other side found it in minutes by
looking at a column. The builder cannot audit their own blind set, because the
things that leak are the things they did not think to check.

## The rule

**Swap evidence columns before either side scores anything.**

Not verdicts — evidence. Each side runs its detector over the set and sends the
per-file evidence column *only*: flags, measured quantities, sample rate, whatever
the engine records. No verdicts, no labels, no scores.

This costs nothing and closes the channel all three leaks used, because a flag
firing on 100 % of one arm is visible in an evidence column long before anyone
knows which arm it is. `AI_SR_48000` on 60 files would have been obvious on day
one; instead it surfaced after the blind was already spent.

## Why it does not spoil the blind

Neither side learns a label from the other's evidence column. What they learn is
whether some flag partitions the set suspiciously cleanly — which is exactly the
signature of a leak and carries no information about *which* partition is genuine.

If a leak is found, the affected arm is disclosed and excluded before scoring,
rather than discovered afterwards and argued about.

## Builder's checklist, before sending

`ml/freeze_exchange_set.py` enforces the first three automatically:

1. **No repeated digests** — `audit_own_output()` refuses to ship, naming the pairs.
2. **No arm identifiable by sample rate** — `_audit_sample_rates()`, stated as a
   general rule rather than a special case for Opus, since special cases are what
   keeps being missed.
3. **No short arms** — a source contributing fewer arms than its peers skews that
   arm's denominator, and is invisible once the ids are shuffled.
4. **No metadata tags** — the original leak, checked since the first set.
5. **Round-trips return to the source sample rate** — `build_audit_corpus.py`
   forces `-ar` on the decode leg. Also the more realistic round-trip: a transcode
   passed off as lossless arrives at the rate the album should have.

None of these existed before the set that taught us each one.

## Provir's mpcenc build record — received 2026-08-20, bytes and hashes in the same action

`provir-msvc-r475.patch` (his 8-file patch making musepack r475 configure and build
under MSVC for the first time since 2011) and `provir-mpcenc-BUILD.md` (his build
record: source sha256, toolchain, the four upstream defects, the profile-ladder
measurement, and his own same-day correction section incorporating the 250 Hz grid
finding). Received 2026-08-20 after LinkedIn silently dropped the original
attachments; `BUILD.md` renamed with the `provir-` prefix on arrival, bytes
untouched.

```
1b015005548e0f690a29cc62f3d49c48bf2d1228fcadcad7e2f6871b2dbb2864  provir-msvc-r475.patch
0af127b114f964766403a95ff0dc715d33cb32beda922508a827d5f8f1e28cff  provir-mpcenc-BUILD.md
```

Verified on receipt, against the claims made about them: the patch touches exactly
8 files; `mpcdec/CMakeLists.txt` does carry the `win32/attgetopt` reference with no
`.c` extension (the line that proves the MSVC path never once compiled); all four
defect classes are present and each hunk is annotated `PROVIR:` in place. The
patch's fixture-generating relevance: our Musepack arm's encoder claims can now be
checked against a source-built encoder with recorded provenance instead of a
downloaded binary.

## The Goodbye My Friend reproduction key — received 2026-08-20 (evening)

His arm-1 exhibit (store file walls at 21,562.8 Hz; CD audio re-encoded through
era-LAME reproduces the wall to 8.1 Hz) was until now recreatable only on his
machine, because "LAME 3.92" names a family of byte-different binaries — his own
hashed register shows nine distinct banners across eleven builds, two of them
twenty years apart printing the same string. The exhibit's exact encoder is now
pinned:

```
lame3.92   sha256 cb2cdfde7b170d90...   195,072 bytes   built 2002-04-16
```

With this, the recreation leg of the exhibit is reproducible by anyone holding a
binary matching that hash. Joint rule this produced, from his register plus our
r495-vs-r475 Musepack finding: banner, source revision and build date are three
independent axes, and a version string pins none of them.

## The wild53 feature ledger — received 2026-08-20 (late)

His 53 wild files, as a per-file feature ledger with labels, bases and dates — no
audio, and every sha field empty (his note names that as the ledger's real gap).
One commercial compilation (Original Hardcore: The Nu Breed, 2004), three DJ-mix
discs, owner ruling lossy on all 53; bases owner-knowledge 34 / eye 19; his engine
41 GENUINE / 12 SUSPECT, 0 convictable in every configuration, with the CNN column
included precisely because it shows a 77 % dependency on a component he bars from
published claims. The note also carries his withdrawal of the 634 lawful
denominator (no ledger, no producing script - only withdrawable) - checked on our
side: nothing in this repository ever cited 634 or the 0.16 % figure.

```
2345a7baac8e666d...  provir-wild53-feature-ledger.csv
a19f0bdf51a24048...  provir-wild53-note.txt
```

What it changed here: three schema repairs in ml/wild_fake_ledger.py (see its
docstring and tests/test_wild_fake_ledger.py) and AMENDMENT 2 of
PREREGISTERED_2026-08-20.md - the pre-registration stays unspent, because this
delivery does not carry the population it names.

## The v2 exchange set — frozen 2026-08-20, NOT yet sent

Built to retire the two defects the 2026-08 set could not shake: sources are now
deduplicated by CONTENT at pick time (30 s of decoded PCM, mono s16le - the
599-that-were-589 repair, pinned by tests/test_exchange_dedup.py), and every
transcode is resampled back to its source rate, so the Opus arm no longer
announces itself by living at 48 kHz (verified on the frozen set: all ten arms
carry the identical rate distribution, 53 x 44.1k + 5 x 48k + 1 x 96k).

590 files: 59 fresh etree sources (95 candidate items, disjoint draw from the
v1 set) x 10 arms, balanced. MANIFEST_v2.sha256 is committed here in the same
action as its self-hash, per the standing rule:

```
a476fa216c7092269891d2e222bd73b323cd8003ce95bb9af2c983bf970b991f  MANIFEST_v2.sha256
```

The answer key lives outside the shipped directory, gitignored (*-LABELS.json).
The set awaits a human decision to send - and per this directory's protocol,
the next blind exchange trades EVIDENCE COLUMNS before anyone scores.

## Corrections stamped on the wild53 note - 2026-08-21, both his, both self-caught

The archived provir-wild53-note.txt stays byte-frozen; two of its numbers are
corrected here, above it, the usual way:

- DEADRUN_UNCORROBORATED "22" is the OCCURRENCE count; the per-file count -
  which is what every other row in that table is - is **20** (two files carry
  two DEADRUN variants each). His words: one hand-carried number was wrong, in
  the exact document written to demonstrate why hand-carried numbers fail.
- The regenerated ledger (incoming with the audio) carries sha256 and
  pcm_sha256 per row and supersedes the archived one as a manifest; the
  archived copy remains the record of what was first received.

His condition travels with the 53 wavs and is adopted as written: if any of
this music turns out essential to our binary, buy the disc.

## The wild53 AUDIO - received 2026-08-21, verified 53/53, W-series scored

Two zip archives via the Drive link circuit; extracted to C:\Users\loutr\wild53
(off-repo). The regenerated ledger inside carries sha256 + pcm_sha256 per row
and verified 53/53 with 0 divergent against the wavs. Scored the same day by
ml/score_wild53.py (committed before it ran); per-row results in
ml/wild53_scores.csv, W-series outcome appended to PREREGISTERED_2026-08-20.md.

Also in the delivery, unannounced - the complete Scott Brown arm-1 provenance
pair, hashed on receipt:

```
2b32826260e555de801822eeda5232e58fe95c106ed039f01e76097e2bd3e528  Scott Brown - Goodbye My Friend (Original Mix).aiff
b86d6d968e54f86c22bb5bf099db4c58c64a0ed880f8a490c1a6efeba85abcc4  Various - Scott Brown - Hardwired III (CD2) - Unmixed DJ Friendly.flac
```

His purchase condition travels with all of it and is adopted as written: if any
of this music turns out essential to our binary, buy the disc.
