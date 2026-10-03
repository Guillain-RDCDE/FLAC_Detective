# `EdgeReading` — why it exists, and what width measured (August 2026)

Moved verbatim out of the docstring of `flac_detective.analysis.spectrum.EdgeReading`
on 2026-10-03, where it had grown to 143 lines of correspondence. The class itself
keeps a short docstring that points here. Nothing below was edited.

---

What `detect_cutoff` cannot say, because it can only return one float.

`detect_cutoff` returns Nyquist in three unrelated situations: the spectrum
genuinely runs to the top, the energy is concentrated in the bass and no wall was
looked for, and nothing was found at all. A caller reading 22,050 Hz cannot tell
a measurement from a shrug, and any median computed over a mixture of the two is
partly a median of failures.

This project already knows that lesson from Rule 15's mono gate — "the correct
behaviour being silence, not a low score, because a low score is still an
opinion" — and did not apply it here. Jamie Dodd's engine returns an explicit
*no wall found* sentinel, which is why his lawful population reads as a sentinel
rather than as a pile of numbers near Nyquist.

`found` is that sentinel. `width_hz` is the second half, and it is the more
valuable one.

## Why width

His measurement, given after retracting the frequency he had handed over: an edge
POSITION does not separate lawful masters from MP3 transcodes at all. Of his 17
real 2009 DJ-master MP3s, 11 carry a sharp wall topping out at 21,479 Hz and 6
have no wall up to 22,023 Hz — while 28 of his 75 lawful masters sit above 21,570.
Both populations live on both sides of any line.

Disclosed by him 2026-08-20, stamped here because we quote the figure: the "6
have no wall" half derives from his width field returning a magic `1500.0`
when no 30 dB drop is found — a sentinel living in a numeric field,
indistinguishable from a measurement to any caller (his own words: our
`detect_cutoff` returning Nyquist for three conditions, in his code). He
verified the claim survives, because 1500.0 there really does mean "found
nothing" — but a file genuinely measuring 1500 Hz of transition would be
silently reclassified. The figure rests on a magic float, not a typed absence.

What separates is how FAST the spectrum falls. In his engine frequency is only a
gate (21,350-21,650 Hz) and the test underneath is a transition width, used as a
conjunction rather than a threshold: his MP3 positives return 390-519 Hz.

With his own caveat, given unprompted: of 75 lawful files inside that window, 5
do show a sharp wall (409-900 Hz). Width does the work and is still not a
separator on its own, which is why the conjunction exists.

RETRACTED BY HIM 2026-08-20 (evening), stamped wherever we quote the range: the
390-519 was not measured under the gate he quoted it against. It came from a
characterisation sweep that applies NO admission gate; under his own 160 Hz
edge-stability rule the 11 wild MP3s reduce to 4 admissible (398-474 Hz), and
BOTH endpoints of the quoted interval come from files the gate refuses (the 390
carries an edge std of 263.7, the 519 of 363.3). Same species as our Rule 1
residual floor: a statistic computed across a population the rule cannot read —
third instance of the species across the two engines in one week. His lawful
409-900 and drive 373-837 figures were re-checked and stand.

Different smoothing, different reference band, different definition of where a
transition starts and stops. His own standing rule applies to us here: never
quote an absolute edge figure without naming the instrument that produced it. So
`width_hz` is calibrated against our own corpus or not at all, and his 390-519
is context, never a threshold to import.

## MEASURED 2026-08-20: width does not become a rule here

`ml/edge_step_probe.py`, 120 genuine and 40 per arm. Width separates at AUC
0.48-0.62 — 0.48 on `aac_ff320`, i.e. below chance — and at a 5 % genuine cost
it fires on 0-5 % of each arm. Against a stereo family at 92 % and an MDCT rule
at AUC 0.99, that is not an axis.

It was measured twice. The first run reused `detect_cutoff`'s size-100
smoothing kernel and was invalid: at 2.69 Hz per bin that kernel spans 269 Hz,
and every width it produced (137-215 Hz median) sat below its own filter. The
synthetic control passed anyway, because a step function survives any kernel —
the same failure as the MP3-geometry probe that validated against a control
sharing its defect. Fixing it to 9 bins gave the statistic real dynamic range
(a synthetic brickwall went 70 Hz -> 11 Hz against a rolloff at ~200 Hz) and
changed the corpus answer not at all.

So the honest statement is narrow: **width does not work bolted onto our
edge-finder.** Our position comes from a 269 Hz-smoothed curve and the width
search starts 250 Hz below it, so the two halves are not one coherent
instrument. This says nothing about whether it works in Provir's, where it does.

CORRECTED 2026-08-20, by him, before we could build on the contrast: Provir's
is not one coherent instrument either. His edge comes from an 8192-point FFT
(p90 across 5 s chunks, whole file, ref -15 dB), his width from a 32768-point
one (mean power, first 90 s, ref -30 dB); the width search starts at
edge - 300 Hz, his gate admits edges wandering by up to 160 Hz, and the width
is quoted to 1.35 Hz. His fire test (width < 600 Hz) is blunt enough that the
wander "probably" does not reach it — "probably" flagged by him as unmeasured.
So the better-specified question, his phrasing, ours to answer as much as his:
does width fail bolted onto ANY separately-derived edge? Answered by
`ml/edge_width_selfanchored_probe.py`, which finds and measures the
transition on one curve, one pass, no separate edge-finder.

## One thing did fall out, and it is not a result

Exactly 3 of our 39 measurable genuine files read as near-perfect brickwalls —
2.7 Hz, 0.0 Hz and 18.8 Hz, at 21,000 / 21,000 / 20,250 Hz. Either they are
transcodes mislabelled in our own genuine corpus, or the statistic is spurious on
them. **This cannot be settled with the statistic under test**, and excluding them
because they look like transcodes is precisely the circularity this whole exchange
is about. They are adjudication candidates for `ml/wild_fake_ledger.py`, whose
`basis` field exists for this, and nothing more until a human with evidence
rules on them.

For the record, and stated as a bound rather than as a finding: if all three were
transcodes, the 5 %-cost fire rates would rise to 7.5-25 % per arm. Still not an
axis, so the question does not change the decision — which is the only reason it
is safe to write down.

RESOLVED 2026-08-20, the same day, by his two follow-up observations. Both were
right. The roundness is our own reporting grid — `detect_cutoff` returns slice
boundaries, so 21,000 / 21,000 / 20,250 are 250 Hz cells, and two files
"agreeing to the Hz" merely share a cell. And the widths were below the
instrument's own floor because the bolted search window opened already under the
-6 dB level at its first bin — on those three files and on ~98 % of the corpus.
Re-measured self-anchored and off-grid (`ml/edge_width_selfanchored_probe.py`):
their true -6 dB edges sit at 15,735 / 18,755 / 15,291 Hz with falls of 5,020 /
1,973 / 4,729 Hz, resolution-stable — ordinary gentle rolloffs, no walls at all.
The observation is withdrawn as an observation about files (it described the
anchor), the 7.5-25 % bound is moot, and nothing goes to the adjudication
ledger.

## THE TYPED-ABSENCE RULE, registered 2026-08-29 — the species, third instance

This class exists because `detect_cutoff` signals "nothing found" by
returning Nyquist: an absence wearing the clothes of a measurement. Provir's
`width` does the same with `1500.0`. On 2026-08-29 he reported the third
instance, on his side and in the other direction: a guard reading, in effect,
`(edge_std or 999) < 160`, where a measured std of exactly **0.0** is falsy,
becomes the sentinel, and the file leaves the stability window on the
coercion rather than on the measurement. A zero std is a legitimate reading —
every window agreed — and it is the strongest evidence for an edge, not the
weakest.

> An absence is TYPED. It is never a value, and never a falsy value.
> Test `is None` (or `math.isnan`). Never test a measurement for
> truth, and never coerce one with `or`: 0.0, 0 and "" are readings.

Enforced rather than asserted: `ml/typed_absence_audit.py` walks the AST of
every module under `src/` and `ml/` and exits non-zero on either shape.
It is also why `found` is a separate bool here and `width_hz` is `nan`
rather than a magic number — a caller that ignores `found` gets a `nan`,
which poisons a median loudly, instead of a plausible float that poisons it
silently.
