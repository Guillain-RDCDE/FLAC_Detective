# The quality stage reads the file once: measured — 2026-09-18

Answers `QUALITY_SINGLE_PASS_REGISTRATION_2026-09-18.md`, whose five criteria
were committed (`71cbfa6`) before any pass was run. All five are met. The
numbers below include the one that went the wrong way.

---

## Criterion 1 — field-for-field equality

Both implementations run on the same files in the same process, the three
result dicts compared with `==`.

| corpus | files |
|---|---|
| `audit_corpus/authentic` | 40 |
| `audit_corpus/fake/mp3_192` | 40 |
| `audit_corpus/fake/aac_ff256` | 40 |
| `fd-pistes-completes` (complete tracks) | 12 |
| `fd-issue8/dur/long_mp3` (complete transcodes) | 24 |
| **total** | **196** |

**196 compared, 0 mismatched.** Not "within tolerance" — equal, including
`dc_offset_value` compared before its six-decimal rounding could hide a drift,
and `clipped_samples` as an integer.

Plus twelve edge cases as unit tests (`tests/test_quality_single_pass.py`): a
fully silent file, one clipping on every sample, a DC-shifted one, mono against
stereo, 24-bit, a one-frame file, an unreadable file.

This was expected to hold by construction rather than by luck: the same blocks
are read in the same order at the same dtype, the same integer is incremented,
and the same Python float accumulates the same per-block `np.sum` in the same
sequence. Each result dict is built by the detector that owns it, through the
methods `detect` itself now calls, so the two paths cannot drift apart later.

## Criterion 2 — no verdict moves

Full pipeline, 92 files (40 authentic extracts, 40 MP3-192 extracts, 12
complete tracks), `--workers 2 --sample-duration 30`. Before-pass from a
detached worktree at `v1.14.1` (`df9e479`), after-pass from the branch, each
verified by printing the `flac_detective.__file__` it actually imported — a
worktree, never `git stash push -- src`, which stashes nothing on a clean tree
and silently compares the code with itself.

**0 verdicts moved, 0 scores moved, 0 differences** in `has_clipping`,
`clipping_percentage`, `has_dc_offset`, `dc_offset_value`, `has_silence_issue`,
`silence_issue_type`, `cutoff_freq`.

The wall-clock of those two passes (392 s and 431 s) measures nothing: the test
suite and the linters were using the same four cores. Speed is measured
separately, below, on an idle machine.

## Criterion 3 — damaged files keep their behaviour

The three detectors each had their own `try/except`, so one failing left the
other two their answer. One shared loop could have taken all three down with a
single exception. The scan returns `None` on any failure and the caller then
runs the three detectors independently, which is the code that shipped.

Tested: a non-audio file yields exactly the three `severity: "error"` dicts it
yielded before. Note this path is only reachable when the corruption check has
been skipped (a cache is present) — an outright corrupt file returns earlier
still, as it always did.

## Criterion 4 — memory must not grow

Peak traced allocation, single analysis of a 20-minute track (160 MB on disk):

| | peak |
|---|---|
| three passes (v1.14.1) | 0.5 MB |
| one pass | 0.5 MB |

Unchanged. The streaming design is the reason this stage stopped loading whole
files, and it is intact: the loop still holds one block at a time.

## Criterion 5 — empty and fully-silent files

Exact answers preserved, including the `full_silence` result and the zero-frame
early returns. Unit-tested.

## Speed, on an idle machine

In-process, one file at a time, the two versions alternating on the same files.

| | v1.14.1 | one pass | |
|---|---|---|---|
| 6 complete tracks | 16.4 s/file | 7.5 s/file | **2.18x** |
| 10 extracts of 60 s | 6.0 s/file | 4.7 s/file | **1.29x** |
| quality scan alone, 196 files | 514.8 s | 196.0 s | **2.63x** |

Verdicts identical in both sets.

The gain is large where the file is long and modest on a short extract, which
is what the model predicts: only the quality stage changed, and its share of
the work grows with duration. On the 20-minute synthetic track the whole
analysis goes from 45.4 s to 21.7 s, with the quality stage from 39.3 s to
15.8 s.

The registration predicted "about a third of the quality stage, so about 26 s
of the 39.3 s". Measured: 23.5 s. Close enough to say the model of where the
time goes was right.

## What got WORSE, and it should be said

The longest silence between two progress events, on that 20-minute track:

| | longest gap |
|---|---|
| 1.14.0 (one event for the whole stage) | 39.3 s |
| 1.14.1 (three passes, three events) | 12.7 s |
| this change (one scan, one gap) | **15.8 s** |

The three substages now fire together, because all three genuinely start
together — announcing them one after another would describe a sequence that no
longer happens. The scan is indivisible, so it is one gap. Against 1.14.1 that
is 3 seconds worse in granularity while the whole analysis takes half as long,
which is a trade worth making and not one to hide.

The real answer is a progress event carrying a position within the traversal
("scanned N of M frames"), which the loop could now emit cheaply. That is a
third event shape in one day, so it is registered as future work rather than
improvised here.

## Still not done, deliberately

The decoded audio often sits in `AudioCache` already, and each detector has a
`detect_from_data`. Using them would remove the read entirely — and change the
result: `DCOffsetDetector.detect_from_data` averages per-channel means where
this path takes one sum over one total, equal in algebra and not in floating
point. That is a change of result wearing the clothes of an optimisation, and
it needs its own registration if it is ever wanted.
