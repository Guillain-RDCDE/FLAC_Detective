# The quality stage reads the file three times: one pass instead — registered 2026-09-18, before measurement

Written and committed **before any before/after pass is run**, per the
convention: the criteria are fixed while the answer is still unknown.

Prompted by the measurement that produced 1.14.1. Instrumenting the stages for
issue #11 showed where the time of a long track actually goes, and it is not
where the code's comments imply.

---

## The finding

On a 20-minute track (synthetic, tonal + noise, 44.1/16 stereo, 160 MB),
analysed at `--sample-duration 30`:

| stage | time | share |
|---|---|---|
| prepare | 0.2 s | 0.4 % |
| metadata | 0.0 s | 0.1 % |
| spectrum | 5.6 s | 12.4 % |
| **quality** | **39.3 s** | **86.7 %** |
| scoring | 0.2 s | 0.5 % |

and inside `quality`:

| detector | time | share of the stage |
|---|---|---|
| clipping | 13.1 s | 34.6 % |
| dc_offset | 11.7 s | 31.2 % |
| silence | 12.9 s | 34.2 % |
| bit_depth | 0.0 s | 0.0 % |
| upsampling | 0.0 s | 0.0 % |

Three detectors, three full streaming reads of the same file, one after the
other. The cost is the reading, not the arithmetic — the three shares are
equal because the three passes are the same pass.

This is deliberate, not an oversight: the comment above them records that the
stage stopped loading the whole file so that memory would stay bounded, and
each detector was given its own `sf_blocks` loop. Bounded memory is right. Three
traversals to obtain it is the part that is not.

## What is proposed

One `sf_blocks` traversal feeding all three accumulators, in place of three.

The point of this change is that it is **exact by construction**, and the
registration should say why before the numbers arrive:

- clipping accumulates `int(np.sum(np.abs(chunk) >= 0.99))` — an integer count,
  independent of grouping;
- dc_offset accumulates `float(np.sum(chunk))` into a Python float;
- silence tracks the first and last index over threshold, and a frame counter.

Fusing them iterates **the same blocks, in the same order, at the same dtype**,
and performs the same sequence of floating-point additions. Nothing is
reassociated. The arithmetic is not approximated, re-derived or vectorised
differently; only the number of times the file is read changes.

This is why the safe route is NOT the obvious one. Each detector already has a
`detect_from_data`, and the decoded audio is often in the shared `AudioCache`
already — but `DCOffsetDetector.detect_from_data` computes a mean of per-channel
means, where the streaming path computes one sum over one total. Those are equal
in algebra and not in floating point, and `dc_offset_value` is published to six
decimals. Reusing the cache would be a larger win and a change of result; it is
explicitly out of scope here and must be registered separately if it is ever
wanted.

## What must not change, and how failure is defined

The criteria below are fixed now. **Any one of them failing stops the change**,
whatever the speed gain.

1. **Field-for-field equality.** For every file measured, the three dicts
   (`clipping`, `dc_offset`, `silence`) returned by the fused pass must be
   EXACTLY equal to those returned by the three detectors today — every key,
   every value, including `dc_offset_value` at full precision and
   `clipped_samples` as an integer. Not "within tolerance": equal. An
   approximate result here would mean the reasoning above is wrong, and the
   change should then be abandoned rather than re-justified.

2. **No verdict moves.** Full-pipeline diff, verdict and score per file, on a
   labelled corpus. Expected: 0 moved out of N. `has_clipping`, `has_dc_offset`
   and `has_silence_issue` feed the scoring rules, so a single changed field
   could move a verdict — which is exactly why criterion 1 is equality.

3. **Damaged files keep their behaviour.** Today each detector has its own
   `try/except`: one failing does not stop the other two, and each reports its
   own `severity: "error"`. A single shared loop would let one exception take
   all three down. The fused pass must therefore fall back to the three
   independent detectors on any exception, and a file that fails must produce
   the same three dicts as it does today. Tested on a truncated and on a
   non-audio file.

4. **Memory must not grow.** Peak RSS on the longest available track must not
   exceed the current value. The purpose of the streaming design is bounded
   memory; an optimisation that trades it away is a different change and is
   refused here. Measured, not assumed.

5. **The empty and fully-silent files keep their exact answers**, including
   `full_silence` and the zero-frame early returns.

## How it will be measured

- **Equality (criterion 1)**: both implementations run on the same files in the
  same process, dicts compared with `==`. Corpus: `audit_corpus/authentic`
  (80 FLAC + 38 non-FLAC), plus the 12 complete tracks of
  `fd-pistes-completes` and the 24 complete transcodes of
  `fd-issue8/dur/long_mp3` — the long files are the ones this change is for,
  and the short extracts are the ones the engine usually sees.
- **Verdicts (criterion 2)**: before-pass in a detached worktree at the shipped
  tag, after-pass on the branch, same files, same order, diff per file — never
  `git stash push -- src`, which stashes nothing on a clean tree and silently
  compares the code with itself.
- **Speed**: the 20-minute track above, and the complete tracks. Reported as
  measured, including if the gain is smaller than the read count suggests.
- **Memory (criterion 4)**: peak RSS of a single-file analysis of the longest
  track, both versions.

## What is expected

Roughly a third of the `quality` stage, so about 26 s of the 39.3 s on the
20-minute track, and no change anywhere else. If the measured gain is far from
that, the model of where the time goes is wrong and this document is the record
of that being found out.
