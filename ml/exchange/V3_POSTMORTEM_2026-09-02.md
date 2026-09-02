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

**What replaces it.** Conviction rate by arm is a property of how much the
encoder disturbs the signal at that bitrate, not of how much attention the
detector has had. AAC at 256 kbps is a heavier disturbance to our instruments
than LAME at 320, and the ordering follows the encoder rather than the effort.
Nothing here is a repair — no constant moved — it is a belief withdrawn.

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

## What set C has to carry

The four targets pick themselves from the table above: the pre-tag houses, V0,
Vorbis at quality, and low-rate arms — the last because the 16,000 Hz constant
in the independence guard could only be priced on material below 256 kbps, and
neither set A nor set B contains any. Built before any constant is chosen on
them, as `ml/build_lowrate_arms.py` was.

And a band-limited stratum built by whichever side did not build the last one,
with both keys sealed at build time, which `write_key` now does.
