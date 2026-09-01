# Independence guard on the corroboration barrier — registered 2026-09-01, before any measurement

Written and committed **before** the first number is produced. Results go in a
dated section at the bottom. A criterion that fails is recorded as failed; a
criterion that turns out to be mis-specified is **withdrawn in writing**, never
deleted.

## The defect

`src/flac_detective/analysis/new_scoring/evidence.py` groups rules into evidence
families and `uncorroborated_conviction_blocked` requires two of them before a
conviction. The grouping was chosen by asking *what does each rule measure*, once,
at design time. It never asks whether two families, **on this file**, ended up
looking at the same observation.

Measured consequence, from `R15_BANDLIMIT_REGISTRATION_2026-08-31.md`: 44 authentic
sources, all AUTHENTIC, given a 14 kHz roll-off and nothing else — 15 convicted.
v1.13.3 removed eleven of the fifteen at zero cost on six arms. **The four
survivors all carry `cnn` + `spectral`.** Rule 12 reads a mid/side mel-spectrogram;
on a file whose top octave has been removed, the dominant feature of that
spectrogram is the same roll-off Rules 1, 2 and 4 read. Two families, one
observation, and the barrier counts two.

The defect is general — the barrier has never asked the question for **any** pair.
Only one pair has measured evidence behind it, so only one pair gets declared.

## The danger this repair carries, named before it is measured

The obvious guard — collapse `cnn` and `spectral` into one witness when the cutoff
is low — cannot distinguish, from the cutoff alone, between:

* an authentic recording band-limited at 14 kHz (`detect_cutoff` reads 15,250–15,500), and
* an **honest low-bitrate transcode**, which is a true positive: `aac_ff128` and a
  128 kbps MP3 both live in the same 15–16 kHz neighbourhood.

On a low-rate arm, `cnn` + `spectral` is precisely how a correct conviction is
made. A guard measured only on set A's arms — all 256 kbps and above, all reading
19 kHz or higher — would report zero cost **because the population that pays the
cost is absent from the set**. Pricing it there would be measuring a repair on a
corpus chosen so it cannot object.

So the price population is declared here, before the constant is chosen.

## Populations (fixed now, none of them set A's shipped audio)

| id | what | source |
|----|------|--------|
| P1 | 80 authentic files, the null | `audit_corpus/authentic` |
| P2 | 44 parked authentic sources + the 14 kHz roll-off, `BAND_LIMIT_FILTER` from `ml/v3_build_set_a.py` | `fd-v3-setA/corpus/_unused` + `_dup_series` |
| P3 | high-rate arms: `mp3_320`, `mp3_V0`, `aac_ff256`, `aacmf_256`, `opus_256`, `vorbis_q8` | `audit_corpus/fake` |
| P4 | **low-rate arms, where this guard is dangerous**: `aac_ff128`, `mp3_192`, plus `mp3_128` and `mp3_V2` built from P1's sources for this measurement | `audit_corpus/fake` + built here |

P4's two new arms are built **before** any candidate constant is evaluated, from
`audit_corpus/authentic`, with the same ffmpeg invocation shape the existing arms
use. They are built once and reused for every candidate.

Operating point, unchanged and the same one the exchange uses: conviction =
`FAKE_CERTAIN`, signalled = `WARNING` or above.

## The two candidate mechanisms

**Mechanism A — conditional collapse.** A declared table of family pairs that stop
being independent under a named condition. One entry: (`cnn`, `spectral`) when
`cutoff_freq < GUARD_HZ`. When the condition holds, the pair contributes **one**
witness instead of two. Absence of a cutoff (NaN) is not a low cutoff and never
triggers the guard.

**Mechanism B — conditional contribution bar.** When `cnn` and `spectral` are the
only two families and `cutoff_freq < GUARD_HZ`, the CNN must contribute at least
`CNN_CORROBORATION_MIN` points to count as a witness, instead of the usual
`MIN_FAMILY_CONTRIBUTION`. The reasoning: on an honest low-rate transcode the CNN
is confident, on a band-limited genuine it is hesitant, and the existing barrier
already uses contribution as its handle on "did this family say enough".

Mechanism B is the more expensive claim, because it asserts something about the
CNN's margin that has not been measured. If A meets every bound, B is not tried.

## Candidate constants

`GUARD_HZ` ∈ {14000, 15000, 16000, 17000}. `CNN_CORROBORATION_MIN` ∈ {20, 30, 40}
(only if B is reached).

## Choice rule, written before the sweep

Among the configurations that satisfy **I3 and I4** (the two hard bounds below),
choose the one with the **smallest** `GUARD_HZ` that also satisfies I1. Smallest
wins because a narrower condition is a smaller claim: the guard should fire on the
population it was measured for and nowhere else. Ties broken toward Mechanism A.

## Criteria

* **I1 — efficacy.** P2 convictions fall from their baseline to **at most 1**.
* **I2 — the null does not move against us.** P1 false convictions ≤ baseline. Any
  increase fails.
* **I3 — HARD, refusal clause.** P3 loses **zero** convictions. One lost conviction
  on a high-rate arm and the configuration is refused outright.
* **I4 — HARD, refusal clause, the price this document exists to force.** P4 loses
  **at most 3 %** of its baseline convictions. This is the bound the naive guard is
  expected to fail, and failing it is a result, not an obstacle.
* **I5 — no silent scope.** The shipped guard must name its pair, its condition and
  its rationale in code, and must be inert on every file whose cutoff is unknown.

**If no configuration of either mechanism satisfies I1, I3 and I4 together, the
guard is REFUSED.** The defect then stays documented and open in
`flac-detective-resultats-registrations` and in the public record, which is a
better outcome than a repair whose price was measured somewhere it could not be
charged. Two repairs have already been refused this way (`R15_RELATIVE_DEAD`, and
the live-MID-bins attempt inside `R15_BANDLIMIT`); this is the same clause.

## Results

*(to be appended, dated, after the measurement runs)*
