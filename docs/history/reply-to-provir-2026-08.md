# FLAC Detective — reply to Provir, 15 August 2026

Guillain d'Erceville. Answers both of Jamie Dodd's messages: the 13 August
head-to-head with the Rule 9A finding, and the 15 August rematch.

Every number below is reproducible from `ml/rule_audit.py`, `ml/mdct_probe.py`
and `ml/wild_audit.py` in the FLAC Detective repository, and this document lives
there alongside them — so that the next person asking "why was Rule 9 deleted"
finds the whole exchange in one place instead of a LinkedIn thread. Where I got
something wrong, including about Jamie's own figures, the correction is left in
rather than edited out.

---

Jamie,

You were right about 9A, and the rest of this message is what happened when I
pulled on it.

**9A reproduces.** On my own probe set — 480 files, 120 band-limited genuine plus
360 transcodes, disjoint from yours — `preecho_pct` comes out at AUC 0.513
against your 0.517. It also reproduces in-pipeline on a fresh 800-file corpus at
0.486. Three corpora, same verdict.

**It was worse than standalone could show.** I ran the same measurement on the
other two tests in that rule. HF aliasing: AUC 0.586, fires on 6 % of genuine and
9 % of fakes. MP3 noise pattern: AUC 0.497 — chance to three decimals. Rule 9 as
a whole was dead weight, not just 9A. Embarrassingly, I had already caught the
noise-pattern test being a degenerate near-constant during an ML feature study
and written it up, and the finding never crossed from the study into the scoring
table. Your message is what made me go back and finish that job.

Rule 9 is deleted, not retuned. There was nothing to tune toward.

**One nuance you couldn't have seen from standalone:** in FD, 9A sat behind a
gate (cutoff < 21 kHz OR an MP3 signature), so high-rolloff genuine files never
reached it — that's why the 0/29 held on your corpus. But the gate only opens on
files that are already borderline, which is exactly where a free +15 does the
most damage, so your effective-floor-of-16 point stands. Also worth flagging for
your own reruns: the pre-echo routine hard-truncates to 30 s internally, so
`--sample-duration 120` never actually extended it.

---

**Then the audit found something I wasn't looking for.**

To check 9A properly I had to build the thing this project never had: per-rule
score attribution, and a harness that measures each rule alone against a frozen
corpus (80 certified-genuine sources, one per album, times 9 codecs). The first
full run flagged Rule 11 at **AUC 0.321**.

Below 0.5 isn't noise, it's inverted. Rule 11 is the cassette-protection rule —
tape hiss, wow and flutter, natural roll-off — and its output is *evidence of
being a genuine analog transfer*. It was being added straight to the transcode
score. A strong signal earned a compensating bonus so it roughly cancelled, but a
*moderate* cassette signal got the penalty and no bonus. Sounding like a cassette
made you look like a fake. Five of my 80 genuine files were flagged; two were
analog-sourced reissues that Rule 11 had personally pushed upward, and one was a
WARNING sitting at exactly the threshold, composed of Rule 9's free +15 and Rule
11's +5.

That one is entirely on me and predates your message. But I would not have found
it without building the harness your message forced, which is worth saying out
loud.

And then a third, from the same instrument. Once each rule's contribution was
visible per file, this turned up:

    AAC 320k   score=45   {Rule8: -50, Rule13: +45}

Minus fifty plus forty-five is minus five. The score accumulator clamped at zero
on *every* addition, and Rule 8 — the Nyquist protection, which the pipeline
calculates first by design — contributes −50 to a genuine full-band file. It was
being erased the instant it was added. Every protection rule that happened to run
before a penalty was inert, in a tool whose stated first principle is "protect
authentic files first".

Three bugs — a dead rule, an inverted rule, a destroyed protection — all invisible
in a total, all obvious in a breakdown. The structural fix is a CI test that fails
if a scoring rule exists in the code but not in the committed audit. You can't
ship an unmeasured rule any more.

---

**Derrien.** This was the useful half of your message and I owe you for it.

I implemented the alignment version: re-analyse with the encoder's own transform
and look for the frame offset at which quantised-to-zero coefficients reappear as
spectral holes. The statistic is peak-to-median hole density across all 1024
offsets — flat near 1.0 for genuine audio, which is the analytic null.

Your KBD α=4 note saved me the day it cost you. I have it as a regression test
now (`test_wrong_window_loses_the_signal`): analysed with a sine window the
statistic drops far enough to look like the method doesn't work.

Measured on 80 genuine sources and their transcodes:

| codec | median peak ratio | AUC |
|---|---|---|
| AAC 128k (ffmpeg) | 19.6 | 0.998 |
| AAC 256k (ffmpeg) | 21.5 | 0.990 |
| AAC 320k (ffmpeg) | 13.6 | **0.993** |
| AAC 256k (MediaFoundation) | 2.7 | 0.791 |
| Vorbis q8 | 1.42 | 0.806 |
| Opus 256k | 1.26 | 0.526 |
| MP3 (192 / 320 / V0) | ~1.24 | 0.40–0.46 |
| genuine (n=80) | 1.25 | — |

False positives: I ran the statistic over **880 certified-genuine files**
(EAC/XLD/Audiochecker ripper logs). Maximum peak ratio across all 880: **1.494**.
Zero above 1.5. My review threshold sits at 2.0 and my hard threshold at 3.0, so
both are in empty space rather than pressed against a tail. The honest reading of
0/880 is "up to 0.44 %", not zero — I'm taking that convention from you.

234 of the 240 ffmpeg-AAC files peaked at the *same* offset (1020), which is
encoder delay showing through and a nice confirmation the statistic reads what it
claims to.

**Three things it does not do**, since the table above looks better than the
method is:

1. **MP3 and Opus sit at the null.** Different framing, hypothesis doesn't fit.
   Fine for me — the cutoff rules already convict there — but this is an AAC
   answer, not a universal one.
2. **MediaFoundation AAC is only half caught** (AUC 0.791, bimodal: p25 = 1.27,
   p50 = 2.66). Same codec, same bitrate, different encoder, and it drops 0.2 AUC.
   I put the MF column in the corpus specifically so I couldn't quietly report
   "AAC solved". If you have qaac or fdkaac to hand, I'd like to know whether
   yours degrades the same way — that's the number that decides whether this
   generalises or whether we've both fitted ffmpeg.
3. **Very aggressive quantisation defeats it.** Above ~60 % zeroed coefficients
   the local-median reference is itself zero and the statistic collapses. Low
   bitrate, where the cliff is obvious anyway — but it's a hole, and it has a test.

There's also a false-positive mode I found by testing rather than by luck: sparse
tonal material (I used four bare sine waves) empties the analysis band, the
denominator collapses to ~0.0002 against ~0.005 for real music, and the ratio
drifts to 3.0 on nothing at all — right at my hard threshold. There's now a
reliability gate that abstains below a baseline occupancy floor. Worth checking
whether your implementation has the same edge, because on a pure ratio statistic
I don't see how it wouldn't.

---

**Net effect, same 800-file corpus before and after:**

| | before | after |
|---|---|---|
| genuine flagged (false positives) | 6.2 % | 3.8 % |
| AAC 320 kbps flagged | 17.5 % | 97.5 % |
| AAC 256 kbps flagged | 50.0 % | 98.8 % |
| all fakes flagged | 60.3 % | 76.0 % |
| convictions | 19.9 % | 19.7 % |

Convictions are flat on purpose — Rule 13 tops out at SUSPICIOUS.

One more thing the audit surfaced that I'm not fixing tonight, since you'll spot
it if you ever join our per-file results. My three remaining false convictions all
have the same shape: Rule 1 and Rule 3 contributing +50 each. Those two fire
together on 141 of 800 files and give the *identical* value in all 141 — Rule 3
reads the bitrate Rule 1 inferred. One inference convicting twice, and 100 points
clears my 86-point bar unaided. Simulated, discounting Rule 3 when Rule 1 has
fired takes genuine convictions 3/80 → 0/80 and fake convictions 142/720 → 4/720.
So my conviction tier — the column I beat you on — *is* that double-count, and the
threshold was implicitly calibrated around it. That needs its own measurement, not
a quick edit. Worth knowing before you take the 4× conviction number too seriously.

**On the benchmark.** No objection to the methodology. You ran at my maximum,
kept the tiers separate, counted abstentions against yourself, and put a Wilson
bound on your own clean row — that's more discipline than most published
comparisons. The conviction/review split reads to me as a design difference
rather than a capability gap, which is what you said yourself.

I'd take you up on the raw JSON and the per-file join. The rows I want most are
the ones where we disagree in opposite directions.

And I read the competition the way you do. A quarter of a store's catalogue being
lossy-sold-as-lossless is the actual problem; which binary catches it isn't. You
told me about a dead axis you could have let me carry, and pointed at the paper
that got me through my own ceiling. The MDCT implementation is in the repo, MIT,
and the corpus builder with it — take whatever's useful.

Guillain

---

# Part 2 — on the rematch (15 August)

Answering this second because the first half is what I owe you; this half is
mostly agreement.

**260 of 768 is a real jump and I'm not going to pretend otherwise.** You also
didn't dress it up: the misses are in the table, the tiers stay separate, the
Wilson bound is still on the clean row, and you added a wild section rather than
leaving the constructed-corpus caveat as a footnote. That's the same discipline
as v1.

Reading the shape rather than the total: all 260 come from five arms at exactly
52 each, and 64 − 52 = 12 identical misses per arm, which you attribute to the
same handful of source recordings. That reads as a wall-reader — it fires
wherever a low-pass edge lands on the ladder and nowhere else, and the 12 are
sources already band-limited before the encoder touched them. Which is the same
population my own tool goes blind on, from the other direction. No complaint;
it's just worth naming that the jump is inside the half of the problem both
engines could already see.

**One row I can't reconcile, and you asked to be told.** In v1, Provir convicted
8 on `aac_cvbr128`. In v2 that arm reads 0, while `fdk_vbr5` goes 22 → 52. Your
v1 total of 30 was exactly those two arms (22 + 8), so those 8 didn't move — they
went away. Your honesty rows cover mp3_V0 and the vorbis/musepack/high-AAC arms,
but not this one. If the unmasking fix retired a rung that was mis-firing there,
that's a *better* engine and worth stating; if it's unintended, it's a regression
hiding inside a headline improvement. Either way it's the only row in the
document I couldn't make add up. (For the record, the 57 restored files do
reconcile: 3 genuine + 54 fakes, 29 + 714 = 743 → 32 + 768 = 800.)

**On the methodology, one thing you did for v1 and didn't for v2.** Your Rule 9A
finding was checkable, and I checked it. The v2 rung isn't — the definitions are
held back for a few weeks, which is entirely your right and I'd probably do the
same. But it means the chain of custody is currently self-attested. Freeze dates
and shadow ledgers are exactly the right artefacts; they just can't be audited
from outside yet. Not a criticism, a status.

## The offer: yes — and here is the reciprocal

Blind, hash-keyed, labels withheld, both directions. You score mine, I score
yours. One-directional removes "it's my corpus" for your numbers only.

Practical constraint on my side, worth stating up front: my audit corpus is built
from my own CD rips, so I can't lawfully ship it to you however frozen it is. I'm
rebuilding the exchange set from Internet Archive `etree` material — explicitly
licensed for redistribution — so the transcodes are distributable too. That takes
me a few days (my machine's outbound network has been down since yesterday, which
is its own comedy).

## Before that, something free — and pre-registered

You already re-run FLAC Detective against your corpus. Next time, use **1.8.0**
rather than 1.7.0: it has a new rule that reads MDCT frame alignment rather than
the band edge, and your table has four arms where *both* our engines read 0
(`aac_abr320`, `aac_cvbr256`, `aac_ff256`, `mpc_q10`). That's the half neither of
us was pricing.

So that this can't be a story told after the fact, here is what I predict **before
you measure**, written down now:

| your arm | my prediction for FD 1.8.0, review tier | confidence |
|---|---|---|
| `aac_ff256` (ffmpeg AAC) | **≥ 90 % flagged** | high — measured 98.8 % on my own ffmpeg-AAC arm |
| `aac_cvbr256`, `aac_abr320` (Apple/qaac) | **degraded, 30–90 %** | low — deliberately wide |
| `fdk_vbr5` (Fraunhofer) | **degraded, 30–90 %** | low |
| `mp3_192/256/320/V0` | **unchanged from 1.7.0** | high — the rule reads at the null on MP3 |
| `opus_256` | unchanged | high |
| `vorbis_q8` | small gain, < 15 pp | medium |
| `mpc_q10` | unchanged (Musepack isn't a 2048-sample MDCT) | medium |

Conviction tier: I predict **no change at all**. The rule is calibrated to reach
SUSPICIOUS on its own and stop there — one very strong signal earns "look at
this", not "guilty". So on your conviction column I stay at 123 and you stay
ahead. That's a design choice and I'm not going to quietly re-tune it to win a
column.

The interesting row is the qaac/fdk one, and it's the reason I want your corpus
rather than mine. On my own set the same rule reads AUC 0.993 on ffmpeg AAC and
0.791 on Microsoft's AAC encoder — same codec, same bitrate, different encoder,
0.2 of AUC gone. I don't know whether I've built an AAC detector or an
ffmpeg detector, and your three non-ffmpeg AAC arms are the cheapest existing
answer to that question. If the prediction above is wrong on those rows, that
finding is worth more to me than the rows I get right.

---

# Part 3 — the scorecard, and what it cost me (15 August, evening)

Two predictions wrong out of eight, and they are the two that were worth having.

## "123 stays 123" — no, 173

Right about the mechanism, and it is tighter than the write-up suggests. Checked
on my own corpus with the finding in hand: **90 files where Rules 12 and 13 both
score, 54 of them at exactly 85 against an 86-point bar, and 3 already convicted**
— on the MediaFoundation arm, by the identical mechanism (cutoff under 20 kHz, so
Rule 8's protection reads 0 and offsets nothing). My "tops out at SUSPICIOUS" was
true of the rule alone and false of the system, and on my own data it held by a
single point. I had the numbers and did not look.

**One precise disagreement.** Framing it as the same mechanism as Rules 1+3 is
not right. Rule 3 reads the bitrate Rule 1 inferred — one measurement counted
twice. Rule 12 is a CNN on a mid/side mel-spectrogram and Rule 13 is MDCT frame
alignment: genuinely independent physics. Two independent signals agreeing is
corroboration, which is what your own gate requires. The defect is not that it
composes — it is that nobody measured or intended it.

## Shipped as 1.9.0

Conviction moved from a score threshold to a corroboration gate: two independent
evidence families required, with Rules 1/2/3/4 counting as ONE because 3 and 4
read 1's inference.

| | v1.8 | v1.9 |
|---|---|---|
| fakes convicted | 142 | **177** |
| genuine convicted (audit corpus) | 3 | **0** |
| genuine convicted (178 wild files) | 2 | **0** |
| convictions resting on one family | 142 | **0** |
| AAC 256k (ffmpeg) convicted | 2.5 % | **58.8 %** |
| flag rates, both classes | — | unchanged |

The early exits had to go with it: the pipeline stopped as soon as the score
passed 86, before Rules 12 and 13 ran, so a corroboration gate on top of that
would have measured the short-circuit rather than the evidence. That is also why
the MP3 arm barely moved (32.5 % → 31.2 %) instead of collapsing as a naive
simulation predicted.

## The number that would have gone wrong, and how it was caught

With two families required, what points bar? On the 80 certified-genuine files
the answer looked free: **zero of them ever reach two families**, so the lowest
bar caught the most fakes.

Then the same question went to 178 wild Internet Archive recordings.
**Eighteen reach two families** — audience material with a low rolloff gives
spectral points, and the CNN fires on the same audio. Scores: 0, 0, 0, 0, 10, 18,
31, 31, 31, 31, 32, 32, 32, 32, 33, 33, 38, 41.

| corroborated bar | false convictions on 178 wild genuine files |
|---|---|
| 31 | **12 (6.7 %)** |
| 45 | 0 |
| **55 (shipped)** | **0**, 14 points of margin |

The bar my own certified corpus called free would have convicted one wild file in
fifteen. That is your "different populations behave very differently", arriving
with a receipt.

## Your Apple finding, sharpened by a number you don't have

"Open-source-encoder detector" is close but the binary breaks: my corpus has a
Microsoft MediaFoundation AAC arm, and Rule 13 reads it at **AUC 0.791**, bimodal
(p25 1.27 / p50 2.66) — partial, not zero. So it orders as
**ffmpeg ≈ FDK > Microsoft > Apple ≈ nothing**: a gradient in how completely an
encoder zeroes coefficients, not open versus closed. Apple sits at the far end,
and my reading is that my statistic counts *holes* while CoreAudio leaves a
different lattice. Which means the zeros were only ever a symptom — the general
object is the quantisation grid itself. That is where I am pointing next, and I
would have pointed at the wrong thing without your two Apple arms.

## Your Musepack question, answered and checkable

Look at the score: **31 exactly.** On my corpus 101 files score exactly 31 and
all 101 are the same thing — Rule 12's high-confidence floor, which lifts a
confident CNN detection to precisely the WARNING threshold and never one point
further. So what fires on s011 is the model, not a heuristic. Musepack was never
in its training set (mp3/aac/opus/vorbis only), so it is generalisation to an
unseen subband codec.

Honest caveat: 6/64 is 9.4 %, and I have not established that it is a Musepack
axis rather than noise landing on transcoded material. It needs measuring before
anyone calls it an axis, and I will do that before claiming it.

