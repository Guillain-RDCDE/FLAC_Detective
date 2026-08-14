# Reply to Jamie Dodd (Provir) — draft, 14 August 2026

Working copy of the response to the head-to-head benchmark and the Rule 9A
finding. Kept in the repo because everything it claims is reproducible from
`ml/rule_audit.py`, `ml/mdct_probe.py` and `ml/wild_audit.py`, and because the
next person to ask "why was Rule 9 deleted" should find the whole exchange in one
place rather than in a LinkedIn thread.

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
