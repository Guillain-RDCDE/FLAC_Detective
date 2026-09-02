# v3 post-mortem — what the round refuted, and what it left open

2026-09-02, written after both halves were scored and both keys had moved. The
numbers it discusses are fixed: the verdict files were hashed and published
before either key was released, and the engine was not touched between the run
and the key.

## K4 was refuted, and the belief behind it is the thing to fix

The registered prediction was that MP3 arms would top out above high-rate AAC.
On his 280 files:

| arm | convicted |
| --- | --- |
| aac_256 | 80 % |
| mp3_320_lame | 71 % |
| opus_256 | 49 % |
| mp3_320_pretag | 9 % |
| mp3_V0_lame | 6 % |
| atrac3plus | 0 % |
| vorbis_q10 | 0 % |

AAC 80 against MP3 71. The prediction is wrong.

**Where the belief came from.** Every MP3-specific instrument in the panel —
the filter-bank statistics, the implied-bitrate reading, the lattice work — was
built first and tuned longest, because MP3 was the format the project started
on. "We are strongest on MP3" was true *of the instruments* and quietly became
a claim *about the arms*, which is a different sentence. It survived because
set A's own arms agreed with it, and set A's arms were chosen by us.

**What replaces it — first version, and it was still too kind to us.** The first
draft of this section said conviction rate follows "how much the encoder
disturbs the signal at that bitrate", and that AAC at 256 is simply a heavier
disturbance than LAME at 320. That keeps the prediction's shape: it still treats
"high-rate AAC" as a thing with a rate.

**It is not.** Provir pointed at his own two AAC arms, 17 points apart, and the
same split is larger on our own half. Measured with v1.13.8 on set A r2, same
bitrate, same music, one encoder swapped:

| arm | convicted |
| --- | --- |
| aacmf_256 (Media Foundation) | 15/36 — 42 % |
| aac_ff256 (ffmpeg native) | 4/36 — 11 % |

Thirty-one points between two encoders of the same codec at the same rate. And
the same ffmpeg encoder that we convict at 11 % on our corpus we convict at 80 %
on his. So "high-rate AAC" varies by 31 points across encoders and by 69 points
across corpora for one encoder — it is not a quantity, and K4 compared MP3
against it as though it were.

Those two figures are themselves pooled across our own stratum, and the split
below shows both are on the low side: on full-band sources alone the two AAC
encoders read 15/24 and 4/24, sixty-three per cent against seventeen, a
**46-point** gap.

**What actually replaces the belief**: conviction rate is a property of the
encoder implementation and the material together, and any claim of the form "we
are strong on codec X" is unreadable until both are named. Nothing here is a
repair — no constant moved — it is a belief withdrawn, and then withdrawn a
second time when the first replacement turned out to carry the same assumption.

Set C arm that follows directly: two AAC encoders at one rate, declared, so the
next version of this question is asked blind instead of reconstructed afterwards.

**What it costs elsewhere.** Any future claim of the form "we are strong on X"
must name the measurement and the corpus that produced it. The claim above never
had one; it had a history.

## K2 was not testable, and was being reported as failed

K2 read "NOT as predicted" at 0.0 % against 0.0 %. Nothing was convicted among
his genuine rows at all, so there was no direction to read, and the band-limited
side held three rows.

Two separate defects in one line. A comparison of two zeros is not a
refutation; and three rows cannot carry a direction, because one file moves the
rate by 33 points. Both were reported as a failed prediction.

Repaired in `score_v3_return.py` as a dated amendment, after the round and
marked as such: a directional criterion now returns HELD, FAILED or NOT
TESTABLE, and the third never enters the failure list. The floor is derived —
at n rows one file is worth 1/n, so ten is where the smallest possible step
stops being larger than most differences worth claiming — rather than chosen to
suit this case. Re-scoring changes that one line and nothing else, which was
checked line by line against the archived reports.

**The registration rule that follows**: a directional prediction must state its
minimum evaluable n when it is registered, not when it is scored.

## A pooled rate that hid a stratum we built ourselves

Reported to him as his research column's headline: mp3_V0 81 %, vorbis_q8 72 %,
mp3_320 64 %. He split those by our own stratum and returned the real shape,
which our scorer now reproduces from his raw verdicts:

| arm | our full-band sources | our band-limited sources |
| --- | --- | --- |
| mp3_320 | 23/24 | **0/12** |
| mp3_V0 | 24/24 | 5/12 |
| vorbis_q8 | 23/24 | 3/12 |

His 320 column does not read our filtered files at all. The pooled figures were
not wrong arithmetic — they were an average across a factor we constructed, knew
about, and held the map for. An average over your own construction is a number
about the construction as much as about the instrument.

Two consequences. Ours: `score_v3_return.py` now prints the per-stratum split
whenever a stratum map exists, with the pooled line kept beside it so the
published figure stays checkable. His: the conclusion he drew on 2 September from
five constructed sources — that a filter in front of the encoder does not silence
his instruments — does not survive twelve real ones, and he withdrew it in those
words. Our scoring of those rows as misses stands; his account of why they were
silent does not.

### And the first thing the split showed was about us

Turning it on for our own engine on our own half, v1.13.8:

| arm | full-band | band-limited |
| --- | --- | --- |
| aacmf_256 | 15/24 | **0/12** |
| mp2_256 | 16/24 | **0/12** |
| vorbis_q8 | 12/24 | **0/12** |
| aac_ff256 | 4/24 | **0/12** |
| mp3_320 | 4/24 | **0/12** |
| mp3_V0 | 2/24 | **0/12** |
| opus_256 | 2/24 | **0/12** |

Zero on every arm. Our filter does not merely silence his instruments — it
silences ours, on every codec we carry, without exception. Ninety-six lossy files
built from twelve filtered sources and not one conviction among them.

That reframes the band-limited stratum. It was built and declared as a false
positive hazard: band-limiting an honest file makes us convict it one time in
three, which is what R11D and the R15 domain gate were priced against. It is also
a **recall** hazard of a size nobody had measured, and the pooled arm rates we
have been quoting since August hid it, because two thirds of each arm is
full-band and carries the number.

No repair follows from this today, and none should: the observation is four hours
old and the corpus it comes from is one we built. It is registered as the first
question for set C, where the stratum will be built by the other side.

## Three open questions, none of them repairs

These are recorded as questions on purpose. None has an account yet, and
inventing one is how a constant gets tuned to a corpus.

**1. `mp3_V0_lame` at 6 %, against `mp3_320_lame` at 71 %.** Same encoder, same
music, twelve times fewer convictions at the *lower* nominal bitrate. V0 is
variable-rate and averages near 245 kbps, so a bitrate story alone does not
explain a factor of twelve. His shipped engine reads 0 % on our `mp3_V0` too,
and his research instrument reads 81 % on the same rows — so the information is
present and neither shipped engine reads it.

**2. `vorbis_q10` at 0 %, on 35 files.** A plain miss, not a coverage limit: the
panel claims Vorbis. His research instrument reads 72 % on our `vorbis_q8`. The
question to him is what principle it works on — not the code, which stays
separate, because two engines sharing a codebase are one witness with two names.

**3. The pre-tag houses.** `mp3_320_pretag` at 9 % against `mp3_320_lame` at
71 %: same bitrate, same music, different encoder house. He declared this as a
limit of his own instrument before scoring — roughly 60 % of what he can address
he cannot convict — and it reproduces on ours, on his files, with neither side
having tuned for it. Two independent instruments blind in the same place is
evidence about what pre-tag encoders leave behind, not a shared bug.

## The set rotted on disk while we were reading it, and the guard caught it

Measuring the AAC split above needed a fresh pass over set A r2. It threw FLAC
decoder errors around file 150, and the first explanation was the wrong one: two
heavy jobs had been started at once on this machine, so it looked like
contention — the same shape as the 152 contiguous ERROR rows Provir had to
quarantine.

It was not contention. A second pass **refused to run at all**:

```
1 files do not match the manifest: ['audio/fd-exchange-v3-setA-r2-0151.flac: digest'] — nothing scored
```

That file had become a Dropbox files-on-demand reparse point and lost 50,794
bytes, rewritten at 17:14 the same afternoon. One file of 288, an `mp3_320` from
src024. This is precisely the v2 transport incident that `run_engine_on_set.py`
cites as its reason for verifying at READ time rather than at copy time, and the
check earned its place: it refused to score rotten bytes instead of publishing a
verdict about them.

**The root cause is ours and it was already written down.** The measurement copy
is supposed to live outside Dropbox — the v2 set does — and a clean copy of set A
r2 was sitting at `C:\Users\loutr\fd-exchange-v3-setA-r2\` all along, 288 of 288
matching the manifest. The pass was pointed at the copy inside `Temp/` instead.
Repaired from the clean one, and re-run from outside Dropbox.

**What the numbers owe to this**: nothing, and that is checkable rather than
asserted. The verdict file from the clean copy hashes
`8cdbfe0b39a7ed8576b5132f1488fe39f4fd6f2a14f5fced5e07591c5fa90527`, byte for byte
what the contaminated pass produced. 288 rows, 0 ERROR, 0 NOT_ASSESSED, and no
decoder errors the second time.

## The discipline that applies from now on

**Set B is an archive, not a bench.** It is the only corpus neither party built
and on which a clean measurement exists. Any repair validated by measuring its
effect on those 280 files turns a blind set into a training set, and the next
number taken from it is worth nothing. Repairs are validated on our own corpus
or on new material; set B is quoted, never optimised against.

**The engine is unfrozen again.** It was held still from the moment his verdicts
arrived until both keys had moved. That window is closed, and repairs are
ordinary work once more — each one a dated amendment with before and after,
as v1.13.3 through v1.13.7 were.

**Never measure from inside a syncing folder.** Written down before and ignored
today. A frozen set has exactly one measurement copy, it lives outside Dropbox,
and a pass that names a path under `Temp/` is pointing at the wrong one. The
read-time manifest check is the backstop, not the plan.

**One heavy job at a time on this machine.** Also written down before and also
ignored today: a scoring pass and the test suite were started together, and the
test run ended in `INTERNALERROR` on a coverage-file lock with 461 tests passed.
Every test passed and the run is still not a green gate, because a run that ends
that way has not finished. It was re-run alone.

## What set C has to carry

The four targets pick themselves from the table above: the pre-tag houses, V0,
Vorbis at quality, and low-rate arms — the last because the 16,000 Hz constant
in the independence guard could only be priced on material below 256 kbps, and
neither set A nor set B contains any. Built before any constant is chosen on
them, as `ml/build_lowrate_arms.py` was.

And a band-limited stratum built by whichever side did not build the last one,
with both keys sealed at build time, which `write_key` now does.
