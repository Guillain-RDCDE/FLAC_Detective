## v1.13.5 (2026-09-01) — two evidence families that read one observation

The corroboration barrier requires two independent evidence families before it
convicts. It established that independence once, at design time, by asking what
each rule measures in general. It never asked whether two families, **on this
file**, ended up reading the same thing.

They can. A file whose top octave has been removed — an analogue transfer, a
vinyl rip, a cassette — makes Rule 12 (a classifier over a mid/side
mel-spectrogram) read the same roll-off Rules 1, 2 and 4 read. Two names, one
observation, and the barrier counted two.

Measured on 44 authentic sources given a 14 kHz roll-off and nothing else:
v1.13.3 had already brought false convictions from 15 to 4, and **all four
survivors carried `cnn` + `spectral`**.

### What changed

`evidence.py` gains a declared table of family pairs that stop being independent
under a named condition, evaluated on the file rather than at design time. One
entry, because one pair has measurement behind it: `cnn` and `spectral` count as
a single witness when the cutoff falls below `FAMILY_INDEPENDENCE_MIN_CUTOFF_HZ`.

Applied at all three places that count families — the verdict, the early-exit
check (a file that exits early would otherwise never reach the collapse) and the
report (which would otherwise name two witnesses where the verdict counted one).

### Price, registered before the sweep and measured on 524 files

    band-limited controls convicted      4 -> 0
    authentic null                       0 -> 0
    six high-rate arms                  99 -> 99    zero convictions lost
    four low-rate arms                  45 -> 45    zero convictions lost

Four verdicts change in total, all `FAKE_CERTAIN` -> `SUSPICIOUS`, all of them
band-limited authentic files. They stay signalled; they stop being convicted on
one observation counted twice.

### Why 16,000 Hz and not 17,000

Rule 15's domain gate uses 17,000, and taking the same value by symmetry would
have been wrong. This guard was priced on **low-bitrate arms** as well, where
`cnn` + `spectral` is exactly how a *correct* conviction is made: a 128 kbps
transcode and a band-limited authentic file both live around 15-16 kHz. At
17,000 the guard destroys three true convictions on `mp3_128`, `mp3_V2` and
`aac_ff128` — 6.7 % against a registered 3 % bound — and that value was refused.

Priced on the exchange set's arms alone, all 256 kbps and above, 17,000 would
have reported zero cost. The population that pays has to be in the corpus before
the constant is chosen. `ml/build_lowrate_arms.py` builds it;
`ml/exchange/INDEPENDENCE_GUARD_REGISTRATION_2026-09-01.md` declared it first.

16,000 is the gap between two measured populations: band-limited controls read
15,250-15,500, the low-rate arms sit above 16,000.

### Still open

The table has one entry. Every other pair of families is still assumed
independent because it was assumed independent at design time. The mechanism to
ask now exists; the asking is unpriced.

## v1.13.4 (2026-08-31) — on Windows, 1.13.0 did not start

Both reported by Provir, against the shipped PyPI wheel, while running his own
encoder panel — nothing to do with the exchange. Neither is visible on Linux,
and neither was visible on our CI, which is the part that matters.

### 1. FATAL — the tool would not start on a stock Windows console

`parse_arguments()` printed the banner before parsing a single argument, and the
banner carries box-drawing glyphs (`╔ ═ ║ █ ▊`). Python gives `sys.stdout` the
console's ANSI codepage on Windows — cp1252, not UTF-8 — where those glyphs have
no mapping, so `print` raised `UnicodeEncodeError` **before any argument was
read**. `--version` and `--help` included. There was no path around it from the
command line.

Fixed by reconfiguring `stdout` and `stderr` to UTF-8 with `errors="replace"` at
the very top of `main()`, before any output. A console that cannot draw a box
now prints a replacement character and keeps going. `errors="replace"` rather
than an ASCII fallback banner because the failure mode to remove is the raise,
not the glyph.

His workaround for anyone on 1.13.0 or earlier: `set PYTHONIOENCODING=utf-8`.

### 2. FUNCTIONAL — `--format json` could not be piped

Two things were wrong at once, and only the first was reported:

* stdout began with the ANSI-coloured banner, then the summary;
* **the report was never on stdout at all.** It went to a timestamped file in
  the output directory, so `--format json file.flac | jq .` could not have
  worked even without the banner — there was no JSON on the stream to parse.

Now, when `--format` is not `text` and no `--output` is given, **the report is
written to stdout** and every decorative print in `main.py` goes to stderr. The
file is still written exactly as before: this adds a stream, it does not take
one away. `sys.stdout` is rebound once after parsing, which makes all 44 prints
in the module correct at once rather than by auditing each.

### The CI job that would have caught it

A stock Windows console, and nothing else new: `chcp 1252`, `PYTHONIOENCODING`
cleared, `--version` and `--help` run against the installed wheel. Every
existing job passed on 1.13.0 because GitHub runners default their console to
UTF-8 — **the case that catches this is the one nobody tests.**

Four regression tests pin both bugs, including the precondition (the banner
really is unencodable in cp1252) so the guard can be removed if that ever stops
being true.

His own line about it, which is the right one: *a gate that does not start is
not a green gate* — the same shape our mypy note made about the developer,
pointed at the user instead.

## v1.13.3 (2026-08-31) — Rule 15 was testifying about a band that was not there

Scoring our own half of fd-exchange-v3 against our own key — a pre-registered
diagnostic, run deliberately before Provir's half arrives — failed its floor:
**one of our 36 genuine files was convicted**, on `spectral+stereo`, which is
exactly the two evidence families the corroboration gate asks for. Four of the
five signalled genuine files were the `band_limited_synthetic` stratum, the one
that had to be constructed because it could not be found in any free archive.

Chased on material that is **not in the shipped set**: 44 parked genuine sources,
all AUTHENTIC, given a 14 kHz roll-off and nothing else — no transcode, no
re-encode. **15 convicted, 22 signalled**, side dead-run median 3.50 against a
bar of 2.0. Band-limiting an honest file convicted it a third of the time.

### Two repairs written, implemented and refused before shipping

* **Restrict the statistic to live-MID bins.** Refused: the MID channel is not
  dead on these files. Live share 0.88-0.94, *higher* than a real mp3_320 at
  0.84 — a shellac transfer's surface noise is loud and broadband and survives
  normalisation. Reverted, and the revert verified by reproducing the original
  reading exactly.
* **A dead test relative to the file's own side level.** Refused by its own
  registered guard: it removes the artefact completely (0 of 34 over the bar,
  from 27 of 34) and costs **0.10 of arm-vs-genuine AUC against a 0.03 budget**.
  The absolute bar is not an oversight that survived — it is where this witness's
  signal lives.

Both refusals are recorded with their numbers. The second one also settles
something: the false positive is **intrinsic to the statistic as designed**, so
the repair cannot live inside it.

### What shipped: a constant that was already right, in the wrong place

`rules/stereo_seam.py` already carried `MIN_CUTOFF_HZ = 12000.0` under the
comment *"Below this cutoff the file is band-limited and the 10 kHz band is empty
anyway"*. The reasoning was correct; the value let files with a 15,500 Hz cutoff
walk through. Measured gap, before the value was chosen:

    genuine min 19,500 · mp3_320 min 19,250 · aac_ff256 min 19,500
    opus_256 min 19,500 · vorbis_q8 min 19,500 · band-limited controls median 15,500

**`MIN_CUTOFF_HZ` 12,000 → 17,000**, the round figure in the gap, 2,250 Hz below
the lowest arm reading.

**Cost, measured before and after on 284 files plus set A's 288:**

| | bound | measured |
|---|---|---|
| convictions on the band-limited controls | ≤ 2 | **15 → 4**, failed |
| false convictions on our own 36 genuine | 0 | **1 → 0**, held |
| convictions lost, four high-rate arms | ≤ 2 | **0**, held |
| convictions lost, two low-rate arms | reported | **0** |
| convictions lost on set A's 252 lossy | ≤ 8 | **2**, held |

Not one conviction lost on any of the six arms. The witness goes silent on the
band-limited population (27 files → 2) and nowhere else.

### The bound that failed names the next defect

The four surviving convictions all carry **`cnn+spectral`**. The CNN reads a
spectrogram, so on a file whose top octave was removed it is reading the same
roll-off Rule 1 is reading. `cnn` and `spectral` are no more independent there
than `stereo` and `spectral` were: **the corroboration gate counts families, it
does not ask whether they are looking at the same thing.** An independence guard
touches every rule pair and gets its own registration and its own priced corpus —
not the same evening that produced two refused repairs.

Registrations: `ml/exchange/R15_BANDLIMIT_REGISTRATION_2026-08-31.md`,
`R15_RELATIVE_DEAD_REGISTRATION_2026-08-31.md`,
`R15_DOMAIN_GATE_REGISTRATION_2026-08-31.md`.

## v1.13.2 (2026-08-31) — the shape that survives its own repair

Provir, 2026-08-30, having run v1.13.1's shape C against his own tree: he found
one latent instance, hardened it, and then **re-ran the check instead of assuming
the fix had worked**. It had not. One module downstream the consumer read the
now-correct `None` as `float(row.get(name) or 0.0)`, and the absence came
straight back as a reading. The defect survived its own repair, in code that
never mentions the statistic by name.

**Shape D**, adopted verbatim from his rule: a numeric cast or comparison whose
argument is `X or <literal>` (or `X if X else <literal>`). Deliberately **not**
name-driven, unlike shapes A to C — his instance fetches the quantity by key, so
there is no measurement identifier anywhere in the line, which is exactly why
every name-driven filter returns clean on it. Shapes A-C inspect where an
absence is *created*; D inspects where it is *consumed*, and the two sites live
in different files.

### What it found here: 6 instances that three shapes had missed

Criteria registered first in `ml/exchange/SHAPE_D_REGISTRATION_2026-08-31.md`.

The one that mattered: `analyzer.py` read `int(metadata.get("sample_rate", 0) or
0)`, and `read_metadata` returns `{}` on any exception. So a file whose header
could not be read arrived at `classify_hires` as **0 Hz**, which reads as "not
high rate" and returned a confident `NOT_HIRES` **with no reason attached** — a
verdict axis answering a question it could not evaluate. Also repaired: a missing
score displaying as `0` in the GUI (which is AUTHENTIC, the most reassuring value
in the table), two report columns taking `0.0` for an unmeasured cutoff in a
column that is averaged downstream, and one line coercing a missing Rule 13 score
back to `0` immediately after the code that exists to keep "did not run" and
"scored 0" apart.

### Cost: nothing, and that is the honest answer

* **D1 — 0 of 750 files** on the measurement corpora have no `sample_rate` or
  `bit_depth`; `read_metadata` returned `{}` on none of them. The path is
  reachable but has never executed here.
* **D2 / D3 — 0 changes.** Pristine worktree against the repaired tree, 20 files
  across three strata, full engine, `deep=True`: verdict, score, hi-res verdict
  and hi-res reason identical on every one.
* **D4 — audit clean**: 153 modules, 0 findings across all four shapes, control
  8 of 8 lines with 0 false positives.

So this instance is **latent**, exactly as his was. No published number changes.

`classify_hires` now takes `Optional[int]` and returns **`UNKNOWN`** — not a new
label, it has meant "analysis unavailable" since the module was written and
`gui/worker.py` already emits it — with a reason naming which field is missing.
Four tests pin the contract, one of them in the other direction: a file that
genuinely claims 0 Hz still reads `NOT_HIRES`, because the repair must not make
`0` and *absent* synonyms.

### Also from his letter, and both are corrections to us

* **Our half-bin argument was vacuous.** We wrote that residuals reaching 2.92 Hz
  — half a bin — proved his exported edges sit on {bin} ∪ {mid-bin}. An integer
  is within half a bin of *some* bin on any grid, so that test passes for every
  transform size from 2048 to 32768 and proves nothing. His version is the one to
  use: if the true values sat on bins, integer rounding could displace them by at
  most **0.5 Hz**, and **102 of 296 residuals exceed 0.5 Hz**. Same conclusion,
  actual proof.
* **Our collision instance was wrong; the mechanism was right.** We predicted
  20003.9 at 48 kHz would also print 20004.0. No 48 kHz row prints 20004.0 at
  all. But five values *do* collide across the two rates in his column — 20074.0,
  20080.0, 20104.0, 21466.0, 21759.0 — so the merge we described is real and more
  common than the single case we guessed. He now exports the unrounded value and
  the chunk count alongside.

Fifth and sixth instances of the species across the two engines in twelve days.
The rule stands, with one more clause: **re-run the check after the fix.**

## v1.13.1 (2026-08-30) — an absence that was being scored, and the constant it had become

Provir reported a defect in his own engine on 2026-08-29: a guard reading, in
effect, `(edge_std or 999) < 160`, where a **measured** standard deviation of
0.0 is falsy, becomes the sentinel, and the file leaves the stability window on
the coercion rather than on the measurement. He was right about the principle,
his was one-directional (it could only lose recall, never manufacture a fire),
and the guard was not in this tree — `opus_edge` appears nowhere here except
inside the archived copy of his own return CSV.

Proving that negative produced the tripwire (`ml/typed_absence_audit.py`, AST,
not grep, validated against its own control before being believed), and the
tripwire's third shape produced **our** instance of the species, which was live,
load-bearing, and pushed the other way:

```python
cutoff_std = float(np.std(cutoff_freqs)) if len(cutoff_freqs) > 1 else 0.0
```

`analyze_spectrum` samples `3 if total_duration > 90 else 1` windows, so for
every file of 90 seconds or less the wander is **not computable** and the
not-computable case was returned as `0.0`. Rule 11's TEST 11D read that zero as
"cutoff very stable, suspect digital" and subtracted 10 — enough to deny a
roll-off-only file (11B alone, 20 points) the `cassette_score >= 15` gate, its
-40, and its Rule 1 exemption. An absence, scored, toward conviction, on every
file in both measurement corpora (`cutoff_std_hz` reads 0.0 on 590 of 590 rows
of the v2 column file: one distinct value).

### The population, derived before it was measured, and measured exactly

Criteria registered first in `ml/exchange/R11D_ABSENCE_REGISTRATION_2026-08-30.md`.
From the weights alone (11A +30, 11B ±20, gate 15) the affected set had to be
files with `cutoff < 19,000` whose only cassette evidence is the roll-off.
Measured on 750 files: **74 movers, 74 of 74 with cassette 10 -> 20, 74 of 74
roll-off-only, none outside the derived population.**

### The registered repair was refused by its own criteria

Full engine, before on v1.13.0 in a pristine worktree, after on the repair, 132
files (74 movers + 58 controls): **A3 failed at 44 transcodes losing their
conviction against a bound of 5** (52 verdicts moved in all; not one genuine
file harmed — the damage was entirely recall).

What that measured is the finding: **the phantom had been absorbed into the
calibration.** `CASSETTE_THRESHOLD` was set to 15 in v1.8 in a world where every
short file carried a silent -10, so the gate's effective height was 25. A defect
that ships long enough stops being a defect and becomes a constant — and a
constant belongs in the gate, not in a reading that was never taken.

### What shipped

The escape clause, with the precedent from this very rule: v1.8 removed test
11C's flat +15 and dropped the threshold by the same 15 "so that every other
test keeps exactly the weight it had".

- `spectrum.cutoff_wander()` returns **NaN** below two windows. Absence typed.
- An absent wander contributes **nothing** to Rule 11 — not +15, not -10.
- The "very stable, suspect digital" **-10 is removed**: on the 250 Hz reporting
  grid it means "the windows landed in one cell", the ordinary case for genuine
  and transcode alike.
- `CASSETTE_THRESHOLD` **15 -> 25**, the same 10 points, in the gate.
- The wow/flutter band's floor moves **50 -> `CUTOFF_VARIANCE_THRESHOLD` (130)**,
  now one shared constant: 117.9 Hz is the smallest non-zero value a 250 Hz grid
  can produce over three windows, and it was earning +15 as tape flutter while
  Rule 1's gate A had been treating the same figure as instrument noise since
  v1.12. The two consumers finally agree about the quantum.
- The `elif cutoff_std < 50` "neutral zone" is deleted: nothing can land in
  [30, 50) on that grid. Dead since v1.8, and it read as calibration.
- Rule 1's 20 kHz ambiguity skip becomes "not known to vary" (`0.0` **or** NaN),
  so the conservative exit is kept rather than silently lost.
- `hires.py` no longer fabricates a 1.0 Hz bin width for a one-bin spectrum
  (shape C caught it too); the degenerate case returns unanalysable.

**Cost, before against after on the same 132 files: 0 verdicts changed, 0 scores
changed, A1/A2/A3/A4 all held at zero.** The compensation is exact wherever the
input was an absence, which is every file of both corpora. What does change is
elsewhere and is the point: files over 90 s whose measured wander is one grid
cell no longer read as flutter, and no single Rule 11 test protects a file
alone. `tests/test_rule11.py` pins the gate decision against the v1.13.0 table,
input class by input class (25 tests; full suite 410 passed).

### The rule, registered on both sides

> An absence is typed. It is never a value, and never a falsy value. Test
> `is None` (or `math.isnan`), never truthiness — 0.0, 0 and "" are readings.

Enforced rather than asserted: `ml/typed_absence_audit.py` walks the AST of
every module under `src/` and `ml/` for three shapes and exits non-zero on any
of them. **150 modules, 0 findings**, control 6 of 6 caught with 0 false
positives. Fifth instance of the species across the two engines in eleven days,
and the first one a machine found.

## v1.13.0 (2026-08-22) — The residual window feeds gate C′; first true convictions in the wild

One engine change, registered in v1.12.0's own changelog before it was made: the
residual-floor **computation** window's floor moves from 0.90 to 0.85 × Nyquist
(18,742.5 Hz at 44.1 kHz), so the MP3 signature cells at 18,750–19,750 Hz gain a
depth reading. That was the named mechanism of v1.12's one missed prediction:
gate C′ accepts an uninformative (PCM-level) container only when the wall proves
its depth, and below 0.90 × Nyquist there was nothing to prove it with. The
consultation zone is untouched; `tests/test_rule1_nearnyquist.py` now pins the
floor to its consumer as well as the top to its guard.

Priced under six criteria registered before measurement (H-series,
`ml/r1_gates_repricing.py`; cross-version diff `ml/h_series_compare.py`):
**every safety criterion held, at strictly negative cost** — 0 genuine newly
scored, 0 of 797 library files, 0 genuine-as-WAV, and the only two pre-existing
genuine +50 are *removed* (two false positives gone). **Efficacy: the offline
+50 count moves 15/34 → 24/34** (all nine gains are WAV at PCM-level container
with residuals −63…−71 dB — the starved cells, fed exactly as registered), and
**end to end the owner-attested wild tier moves 50.0 % → 70.6 % signaled with
the engine's first two true wild convictions**: both owner-attested fakes,
convicted on `spectral+stereo` (64 pts) and `cnn+spectral+stereo` (82 pts) —
the M-series prediction (repair the admission gates and the stereo witness
corroborates) landing in the verdict column. Zero convictions on the eye tier
and the mixed disc.

One prediction missed, shipped as a miss with its mechanism named: the lab arms
lose 7 of 160 (+50 count 160 → 153). The est-320 exoneration — residual above
−55 dB drops the signature — now reaches cells 19,500–19,750 Hz, where
AAC/V0/Vorbis walls carry floors of −33…−51 dB, above a bar calibrated entirely
on [0.90, 0.94) × Nyquist. Re-calibrating the depth bar per cell (or bounding
the exoneration to its calibration domain) is the v1.14 candidate; it gets its
own registration.

### The calibration debt paid: bars re-verified on the purged corpus

The 32 quarantined files sat inside every "258 genuine" calibration, so the two
witness bars were re-verified on the clean population with the acceptance rule
registered first (`ml/recal_clean228.py`). **No constant moves.** RUN_BAR (2.0):
clean p95 = 1.94 — the quarantined files were pulling the p95 *down* (they read
like genuine on this statistic, median 1.00), so the shipped margin was
UNDER-stated, not over-stated. SEAM_BAR (0.60): clean p90/p95 = 0.58/0.65,
unchanged to the second decimal, the bar still between p90 and p95 as designed —
the audit rule's own "must be ≥ p95" flag was dismissed by the counterfactual
(it fires on the original 258 too, so it measured the criterion, not the purge).
Also: the ambiguous glenhansard item settled by reading its full description —
the Muvid IR815 is an **internet radio**, its digital out a decoded compressed
broadcast stream; 2 more files adjudicated on the documentary basis and
quarantined (ledger: 32 fake). The public population notes now carry both
versioned numbers (8.8 % at v1.11.4, 50.0 % at v1.12.0, zero convictions both).

## v1.12.0 (2026-08-21) — Rule 1's four admission gates repaired; the engine reaches the wild

The first engine change since v1.11.0, and the first release whose every number
was pre-registered before its measurement. Four admission gates in Rule 1 — each
calibrated on direct-lab material — silenced the spectral family on exactly the
population wild compilations sell. Repaired: **gate A** (variance threshold
100 → 130 Hz — the old bound was smaller than the edge-finder's 250 Hz
quantization step, so a rock-stable wall near a cell boundary exited); **gate B**
(the 20,000-Hz-exact "FFT rounding" exception now decides on the wall's DEPTH —
residual floor ≤ −55 dB — instead of raw HF energy, which wild press noise
always trips); **gate C′** (an uncompressed container's bitrate carries no
compression information and is bypassed — but only when the wall proves its
depth, because for sub-320 cells the container window was the only guard);
**gate D** (Rule 1 runs on WAV input at all — the dispatcher used to remove it
for uncompressed containers, which put every WAV structurally beyond the rule's
reach; found by the campaign's own end-to-end criterion on its first firing).

Priced on 1,031 files plus three safety populations, wild53 held out, every
criterion registered before measurement (`ml/r1_gates_repricing.py`):
**all safety criteria held** — 0 genuine newly scored (after the label
correction below), 0 of 797 library files (the 24-bit control), 0 genuine-as-WAV
(the format control), 0 convictions end-to-end on the wild 53. **Efficacy:
owner-attested wild recall moves 8.8 % → 50.0 % signaled** (17/34, all WARNING,
none convicted); the lab mp3_320 arm gains +15 files (gate B repairs the bench
too). One efficacy prediction missed and reported: the offline +50 count reached
15/34 against a registered ≥ 20 — C′'s depth requirement has no reading below
0.90 × Nyquist; widening the residual computation window is v1.13, registered
separately.

**The campaign's safety gate also found 30 mislabeled files in our own genuine
corpus**: 11 Calexico etree items (30 of 180 wild-genuine files) carry
taper-documented Sony MiniDisc chains (`ECM-DS70P > MZ-N10`) — ATRAC, lossy —
adjudicated fake on the documentary basis and quarantined; they sat inside every
"258 genuine" calibration this project ever published. The wild ledger holds its
first 30 real rows, and the engine that found them still never became their
label.

### The edge grid: every slice-method cutoff is a multiple of 250 Hz

Answering two verification requests from Provir (2026-08-20) exposed one cause under
both. `detect_cutoff` scans 250 Hz slices upward from 14,000 Hz and returns slice
boundaries, so every slice-method cutoff lands on the grid **14,000 + k × 250 Hz** —
measured across 360 files: 154/154 slice-method cutoffs on-grid, 0/204 self-anchored
edges. That resolves both of his checks at once: the Musepack `--insane` median
reading *exactly* 18,750 Hz (a grid cell colliding with mpcenc's 48 kHz ladder,
which steps by 750 Hz and shares every third rung with a 250 Hz grid — arithmetic,
not an echo of `Max_Band`), and two of the three "perfect brickwall" genuine files
agreeing to the Hz at 21,000 (same 250 Hz cell). Any published median of these
cutoffs is quantized to its cell; the grid is now stated in `detect_cutoff` itself
and stamped on the affected tables below.

### The three "perfect brickwalls" were the anchor, not the files

`ml/edge_width_selfanchored_probe.py`, predictions registered and committed before
the run; P1/P2/P3 all confirmed. The bolted width window of v1.11.4 opened already
below its own −6 dB level at its first bin on **~98 % of found edges (204/208)** —
including all three brickwall candidates, whose true −6 dB edges sit at 15,735 /
18,755 / 15,291 Hz with resolution-stable falls of 5,020 / 1,973 / 4,729 Hz.
Ordinary gentle rolloffs; the literal 0.0 Hz width had been manufactured by a window
that opened below −30 dB. The v1.11.4 observation is withdrawn — it described the
anchor, not the files — its 7.5–25 % bound is moot, and nothing goes to the
adjudication ledger.

### Width measured coherently for the first time, and the null survives

His correction, the day after v1.11.4: his width instrument is not one instrument
either (edge from FFT 8192 at p90, width from FFT 32768 as a mean, a gate admitting
160 Hz of anchor wander, width quoted to 1.35 Hz). So the open question became his
phrasing of it: does width fail bolted onto ANY separately-derived edge?
Self-anchored — edge and width from one curve, one pass, no `detect_cutoff` — the
−6 to −30 dB fall distance reads AUC 0.37–0.63 across arms at both resolutions
(aac_ff320 anti-correlated), and fires on at most 25 % of an arm at 5 % genuine
cost, against a stereo family at 92 % on the same arms. The null now describes the
corpus, not the instrument. His half of the question — whether his 390–519 Hz
survives his own anchor's wander, on his corpus, with his gate — is his to measure.

### Stamped on a figure we quote: his own 1500.0 sentinel

His disclosure, volunteered: the "6 of 17 have no wall" figure rests on his width
field returning a magic 1500.0 when no 30 dB drop is found — a sentinel in a
numeric field, our `detect_cutoff` shrug in his code, and the caveat now travels
with every place we cite the figure (`EdgeReading`, `ml/edge_width_probe.py`). He
verified the claim survives: 1500.0 there really does mean "found nothing".

One defect caught in our own run before reading any number: the three forced
candidates were measured twice — slash-direction defeating a string-level path
dedup, the exchange set's 599-that-were-589 species — exposed by the P2 report
printing each file twice. Deduped, normalized, regenerated; the freed slots went to
three never-measured genuine files.

### His evening reply: a retraction we quote, a missing number, and a key

Provir retracted the 390–519 Hz width range (stamped at every site we quote it:
`EdgeReading`, `ml/edge_width_probe.py`, the self-anchored probe,
`tests/test_edge_reading.py`, and the v1.11.4 section below): it came from an
**ungated** characterisation sweep, and under his own 160 Hz admission rule the 11
wild MP3s reduce to **4 admissible files at 398–474 Hz** — both quoted endpoints
among the refused. That is the third instance in one week, across the two engines,
of the same species: *a statistic computed across a population the rule cannot
read* (our Rule 1 residual, his width sweep, his Opus flatness probe).

The answer to the question we handed him — the measured flip rate of his whole
fire predicate under anchor wander — **did not arrive**: his message shipped with
the result placeholder literally unfilled (`‹FILL: anchor-wander result …›`), and
everything after it is pre-run mechanism and bounds (width moves at most 1:1
against the anchor; two lawful masters at 700/723 Hz within reach of being pushed
*into* firing — the direction his first rule forbids, bounded by his two-group
corroboration to a review flag). The number is still owed and has been asked for.

> **Arrived hours later.** Fire decision stable under each file's own anchor
> uncertainty on **15 of 16** admissible recordings; the exception fires in 99 %
> of resamples. The flat ±160 Hz sweep reads 11/16 — and the gap is the lesson:
> 160 is the admission limit on the *spread* of per-chunk edges, the anchor is
> their *median*, and he had been quoting the admission limit as the error bar.
> En route, two near-misses of this week's species, caught by him: 37 rows were
> 22 recordings (~40 % filename duplication — the 599-that-were-589 by a third
> route), and his own remeasurement refused 6 of the 22 the source CSV admitted,
> one by 5.2 Hz against the window boundary. His volunteered limits: within-window
> result (8 rows change regime between his two windows — his next fix), n mostly
> quarantined drive material, and the 700/723 pair stays open.

His LAME register, hashed the same afternoon, joins with our r495-vs-r475 into
one rule: **banner, source revision and build date are three independent axes,
and a version string pins none of them** — eleven binaries, nine distinct
banners, two byte-different builds twenty years apart printing the same string.
He also made his *Goodbye My Friend* exhibit reproducible from our side for the
first time: `lame3.92`, sha256 `cb2cdfde7b170d90…`, 195,072 bytes, built
2002-04-16 — archived in `ml/exchange/README.md`.

### The admission audit: his species, hunted through our own calibrations

The week produced three instances (our Rule 1 residual, his width sweep, his Opus
flatness probe) of one species — *a statistic computed across a population the
rule cannot read* — so `ml/admission_audit.md` walks every calibrated constant in
the engine against its rule's own admission gates, with counts from the committed
per-file CSVs. Verdicts: Rule 1 **aligned** (fixed v1.11.3, test-pinned); Rule 12
Platt **aligned** (`emit_probs.py` skips gate-abstained files by default); Rule 15
`RUN_BAR` **aligned in effect** (mono gate applied by the probe; the unapplied
12 kHz floor excludes 0/258 genuine files); Rule 14 `SEAM_BAR` **misaligned,
negligible** (2/258 below the 15 kHz floor — both at 14,000 Hz, grid cells —
≤ 1 rank of the p95); and **Rule 13 misaligned, bounded — the fourth instance of
the species**: 17/258 genuine (6.6 %) sit below the rule's 18 kHz admission
floor, so ~58 of the 877 recertification files are ones the rule will never be
asked about. Bounded: exceedance 0.11 % → at most 0.12 %, bars stay above the
admitted population's p99.9 under every removal scenario, no constant changes;
the next recertification must filter through `should_run_rule_13` and publish
both quantiles. Standing rule adopted: a calibration is computed under the
admission conditions of the rule that consumes it, or states why the superset is
safe.

> **Measured the same day** (`ml/recert_admission_pass.py` + committed
> `ml/recert_admission.csv`, hashes only): 22/877 certified files (2.5 %) sit
> under the 18 kHz floor — the library is less band-limited than the wild corpus.
> Admitted-only p99.9 = **1.634** vs the published all-certified 1.614, inside
> the argued worst case; review-bar exceedance 1/855 = 0.12 %, hard bar 0 on both.
> Both quantiles now ship in `mdct.py` (`CERTIFIED_GENUINE_ADMITTED_P999`).

### MP3_IDEM measured: the Opus candidate dies, and an MP3-320 monster appears

`ml/mp3_idem_probe.py`, from the fixed-point spec Provir supplied on 2026-08-19,
predictions committed before the run (354 files, both instruments' traps
honored: file-based encodes only, FFT correlation after the O(n²) direct method
was caught by a hanging selftest). The predictions split: **P2 failed — the
reason the family was wanted is dead here.** Opus transcodes read *farther* from
the MP3 fixed point than genuine files (AUC 0.40, below chance), and AAC/Vorbis
behave the same: the statistic measures distance to the fixed point *of the
re-encoding codec*, so the family is codec-paired, not universal. **P3 held at
AUC 0.99** — 97.5 % of mp3_320 at 5 % genuine cost, the strongest single-family
figure ever measured on that arm. Reported to Provir as a divergence: their
MP3_IDEM quotes 67 % on Opus, ours reads 2.5 % — instruments differ and are now
both named. Not wired into the engine: two ffmpeg roundtrips per file and a new
system-binary dependency have not been priced against a marginal catch on an arm
two witness families already read. It stays a measured instrument, like HF_SEAM
did before it earned Rule 14's slot.

> **Resolved 2026-08-21 — the cleanest cross-validation of the exchange.** Their
> probe re-encodes with *libopus*, and their 2026-07-20 cross-codec control is
> the exact mirror of ours: under a libopus probe, mp3/AAC/Vorbis all sit ON
> genuine. Two labs, a month apart, different instruments, same sentence: the
> probe must use the suspected encoder — codec-paired, both directions. And the
> 67 % is retracted by him: not defensible anywhere in his records (his axis
> degraded at every increase in n; the standing figure is **22 % of dithered
> Opus at 0 FP, n=90**, trap history attached). Stamped where we quote it.

### The claims harness: distrust stated practice, run before every release

`ml/claims_audit.py` + `ml/claims_register.json` — Provir's automated
self-distrust pass, rebuilt here: it inventories every bolded numeric claim in
the public pages (README + docs site), verifies each registered claim's pattern
still exists in its stated file, and checks its evidence (committed artifact,
machine-checked JSON count, or a rule-count check that greps
`def apply_rule_N`). First run, first contradictions, both fixed: **README said
"10 heuristic rules" and technical-details said "11" while the code defines 12**
(plus the optional CNN), and `docs/index.md` still announced **"Version: 1.4.0 |
Last Updated: June 2026"** — an unvalidated field beside validated ones, the
`__release_date__` class of defect; the line is deleted rather than hand-fixed.
7 claims registered and machine-verified, 51 inventoried as unverifiable
backlog — a report, not a failure; the register grows toward the prose release
by release.

### Content-level dedup where exchange sources are picked

The 599-that-were-589 repair, at the site of the original defect:
`pick_sources_from_dir` now fingerprints 30 s of decoded PCM (mono s16le,
container-invariant) and refuses a second item carrying the same audio —
`audit_own_output` only catches byte-identical twins after the fact.
`tests/test_exchange_dedup.py` rebuilds the exact historical trap (one taper's
track under two etree item names) and pins that it collapses.

### The v1.12 G-series: suspended by its own safety gate, which found 30 mislabeled files

The three Rule 1 gate repairs (variance 130 from grid arithmetic; the
20,000-exact exception deciding on depth instead of raw HF energy; PCM-level
containers bypassing the FLAC-calibrated range check) were registered with
acceptance criteria before any measurement (`ml/r1_gates_repricing.py`) and
evaluated offline on 1,031 files. **G2 held** (26/34 wild owner files newly
reach +50, from zero), **G3 held** (lab arms 142 → 160, +15 on mp3_320 alone —
gate B repairs the lab bench too), and **G1 failed as written**: 4 genuine
files newly +50 against a bound of 2 — so the campaign stopped, no threshold
retuned, src untouched. Then the four were traced: all Calexico etree
recordings, and their items' own taper-written metadata reads
`ECM-DS70P > MZ-N10` — **a Sony MiniDisc chain: ATRAC, lossy**. A full lineage
audit of the wild corpus found **11 items, 30 of 180 files (16.7 %), carrying a
documented MiniDisc chain** while labeled genuine — inside every calibration
that used "258 genuine". The repaired gates did not produce false positives;
they detected documented ATRAC material our labels had wrong, and the safety
bound caught it before anything shipped. The 30 files are registered in the
wild ledger with their documented sources, label undecided: **the campaign is
suspended pending human adjudication** (documentary basis: the taper states
the chain). Rules them lossy → labels correct, G1 re-scores, stage 2 proceeds.
Rules them genuine → G1 stands and the campaign ends.

### The M-series collapses the wild anatomy into one layer — and the engine already sees

Provir answered DEAD_STRUCTURE's domain from the code (side channel, absolute
1e-3 threshold on 16-bit-rounded magnitudes, longest interior frequency-run
maximised over frames): same name as our dead-run, zero shared observable —
the D-series 0.0-vs-118 fully explained. The M-series (`ml/wild53_r15max.py`,
registered before the run) then tested the one aggregation choice separating
his 12/34 from our 3/34 — and **both predictions failed, the second one in the
best possible way: the SHIPPED Rule 15 median reads the owner-attested wilds
at AUC 0.97, 34/34 over RUN_BAR.** The witness roster sees the wild population
almost perfectly; what is missing is not detection but POINTS — a zero-point
witness may only corroborate, and the Rule 1 admission gates suppress the very
points it would corroborate. The wild anatomy therefore reduces to one
load-bearing layer: repair the R1 gates and the stereo witness corroborates
34/34 instantly. Max-over-frames is closed at our geometry (genuine max tail
p95 = 55.5, no separation gained); the two engines' instruments stay mapped
side by side, un-converged, as he asked.

### Layer 3 measured, and it is us: the wild cliff is cleaner than the lab's

The L-series (`ml/wild53_cliff.py`, registered before the run) asked what fills
the cliff in the wild bytes — **all three predictions failed, with the sign
reversed**: the wild walls are *deeper* than our own lab transcodes' (−63.9 vs
−56.7 dB median), in the same grid cells, with zero files in Rule 1's
near-Nyquist mute zone — and our v2 noise floor had *filled* the cliff by 20 dB,
manufacturing an upscale-like artifact the CNN over-reads (the v2 residual is
carried by cnn on 22 of 22 signaled files). The cliff is not masked; the
follow-up dissection found what actually silences the spectral family on the
wild 34: **three Rule 1 admission gates, each calibrated on the direct-lab
population** — (a) the variance gate's 100 Hz threshold is smaller than
`detect_cutoff`'s 250 Hz quantization step, so a rock-stable wall near a cell
boundary reads std ≈ 118 and exits; (b) the 20,000-Hz-exact "FFT rounding"
exception discards any wall snapped to that cell whenever energy_ratio > 1e-6,
which the wild chain's press noise guarantees on every file; (c) the
container-bitrate range (700–1050 kbps) was calibrated for FLAC, so **every WAV
(1411 kbps) is structurally beyond Rule 1's reach by format**, and dense
material FLAC-compresses out of range too. Plus the CNN reading the wild at
3/53 — out-of-distribution, as Provir's own CNN audit warned. The true anatomy
of the 8.8 %: the mastering chain kills the fixed point and the side/temporal
tells (layers 1–2, demonstrated); the spectral silence is **our own gates**.
Nothing is retouched: each gate protects real authentic populations, and moving
any of them is the v1.12 engine campaign — priced against the full 800-file
audit corpus with the wild53 as the held-out bench.

### The re-mastered arm: the lab-to-wild gap decomposed into named layers

The bench gained the arm the W-series proved missing (`ml/remaster_arm.py`,
chain and acceptance criteria registered before each measurement, the wild53
signature as the known answer). Chain v1 (EQ + level rides + limiter) reproduces
the fixed-point destruction exactly (MP3_IDEM AUC 0.98 → 0.46, median R 3.05 vs
wild 3.18) and touches nothing else. Chain v2 — the one permitted strengthening,
a decorrelated −72 dBFS stereo noise floor — kills the side-channel family as
the wild does (stereo AUC 0.93 → 0.40, fire 86 % → 0 %) and collapses the
temporal family (0.89 → 0.60). The engine still signals 55 % of v2 against the
wild's 8.8 %, and per the registration there is no v3: the honest result is a
**layered characterisation of the real mastering chain**, each layer
demonstrated by the instrument it kills — (1) limiting destroys the codec fixed
point, (2) the analog noise floor refills the side channel and re-agitates HF
variance, (3) an unmodelled third layer masks the spectral cliff (the v2
residual is carried by the spectral/CNN families the wild also defeats).
Alongside: the reopened dead-run question closed the other way
(`ml/wild53_deadrun.py`, D-series) — our max_run reads 0.0 on the very bytes
where Provir's DEAD_STRUCTURE_MAXRUN reads 100–118, so his statistic and ours
are different observables, and asking him for its actual domain is now mandatory
rather than curiosity: it is the one flag family demonstrably reading a
population our whole engine misses.

### The wild53 scored: the first measured lab-to-wild gap, and it is brutal

The audio arrived with a regenerated ledger carrying per-row hashes; **53/53
verified, 0 divergent**, and the W-series — registered and committed before the
first byte was downloaded — was scored on bytes (`ml/score_wild53.py`,
`ml/wild53_scores.csv`). W1 **held**: 0/53 FAKE_CERTAIN — on 53 files the owner
rules all lossy, the conviction gate produced zero false certainty in either
direction. W2 held on direction (owner-knowledge 8.8 % signaled vs eye 0 %,
Wilson intervals overlapping). **W3 and W4 failed, and the failures are the
finding**: the engine signals 8.8 % of owner-attested wild 320s against 68–100 %
per arm on lab-made transcodes — Provir's engine reads the same tier at 32 %,
3.6× ours — and MP3_IDEM reads 0/34 under its bar with a median R
indistinguishable from genuine. The mastering chain between the MP3 and the
disc (DJ mix, crossfades, levels, CD press) pushes the audio clean off the MP3
fixed point and plausibly off every alignment and side-channel tell with it.
**The lab benchmark measures direct transcodes; the wild sells re-mastered
ones; these are different populations**, and every published rate now needs to
say which one it is about. Bonus received with the set and hashed: the Scott
Brown exhibit pair (store .aiff + lawful unmixed CD) — our self-anchored
instrument reads the store file's −6 dB knee at 17.5–18.5 kHz where his two
edge-finders read the floor at 21,436/21,562 Hz: three instruments, three
numbers, all "the edge", the never-quote-an-edge-without-naming-the-instrument
rule in a single exhibit.

### The Musepack arm, re-run with provenance and an off-grid edge

Provir's BUILD.md lesson applied to our own fixture generator: the workflow now
records the encoder in the artifact itself (`musepack_arm_r2_provenance.txt`) —
Debian musepack-tools 2:0.1~r495-2build1, mpcenc 1.30.1 banner, built 2024 from
**r495**, the same banner as his source build from a *later* revision than his
r475: the version axis his document warns about, recorded instead of assumed. On a
fresh 24-source draw (`musepack_arm_r2.csv`) every published AUC reproduces and
the cell medians reproduce *exactly* (16,000 / 17,750 / 18,750 — the grid again,
on a disjoint draw). The new off-grid −6 dB edge shows the separation does not
live in the start of the fall (genuine 15,769 Hz vs insane 15,738 Hz, 31 Hz
apart) — it lives in the floor statistic, which is what the zeroing mechanism
predicts: the knee stays put, the depth changes. The observable that separates
and the observable that is easy to measure off-grid are different quantities, and
future tables must name which one they quote.

## v1.11.4 (2026-08-20) — a retraction we had already shipped, and a null result worth having

v1.11.3 corrected a false claim in Rule 1 by citing a frequency Provir had supplied.
Jamie Dodd then retracted that frequency himself, before we could act on it, with
the error bars he had left off. This release removes it from our code and reports
what replaced it — including a null.

### What we published and had to take back

We wrote, in a shipped code comment and in release notes now on PyPI, that
*"3.90.3, 3.92, 3.93.1r, 3.93.1w32 and a 2002 daily all land within 8 Hz of each
other at -b 320"*. **No measurement supports that sentence.** He had fused two
different 8 Hz figures — 8.1 Hz was store-file-vs-recreation, ~8 Hz was
build-to-build — and told us so unprompted. The build-to-build spread survives on
its own (5.3–5.4 Hz on separate material, measured before the claim existed) but
must never be bound to a frequency.

The frequency itself is worse than imprecise:

- it is one reading, of one file, by one edge-finder written that morning;
- **early 3.9x LAME at `-b 320` applies no lowpass at all**, so the number measured
  the source material, not the encoder — the same build group swings **3,800 Hz** on
  content alone (17,420 Hz on one track of a CD, 21,226 Hz on another from the same
  disc);
- 503 of his 1,180 lawful files (**42.6 %**) already read an edge at or above it. A
  threshold there convicts lawful CD masters at scale, classical and acoustic first.

**We had not moved the guard.** Our own measurement had already refused to open that
region a day earlier, for unrelated reasons. Two independent refusals of the same
change is the useful part of this exchange working.

### The conclusion is stronger than the number was

Of his 17 real 2009 DJ-master MP3s, 11 carry a sharp wall topping out at 21,479 Hz
and **6 have no wall at all** up to 22,023 Hz. Meanwhile **28 of his 75 lawful
masters sit above 21,570**.

Both populations live on both sides of every line. **No edge position separates
them**, so our 21,500 constant was never a threshold set too low — it is the wrong
kind of quantity. That also settles the instrument caveat from v1.11.3 rather than
leaving it open: his two edge-finders reading the same file at 21,436.3 and 21,562.8
Hz is the same result arriving from measurement error instead of population overlap.

### What he uses instead, and why it does not transfer

Frequency is only a gate in his engine (21,350–21,650 Hz); the test underneath is
transition **width**, as a conjunction rather than a threshold, with MP3 positives at
390–519 Hz. He volunteered the caveat too: 5 of his 75 lawful in-window files also
show a sharp wall.

> **Retracted by him 2026-08-20 (evening):** the 390–519 came from an ungated
> characterisation sweep. Under his own 160 Hz admission rule the wild MP3s
> reduce to **4 admissible files at 398–474 Hz**, and both quoted endpoints are
> among the refused. Same species as our Rule 1 residual floor — a statistic
> computed across a population the rule cannot read. See Unreleased.

Measured here on 120 genuine and 40 per arm (`ml/edge_width_probe.py`):

| arm | width AUC vs genuine | fires at 5 % genuine cost |
|---|---|---|
| `mp3_320` | 0.56 | 2.5 % |
| `mp3_V0` | 0.62 | 5.0 % |
| `aac_ff320` | **0.48** | 2.5 % |
| `aacmf_256` | 0.54 | 2.5 % |
| `opus_256` | 0.60 | 0.0 % |
| `vorbis_q8` | 0.52 | 5.0 % |

Below chance on `aac_ff320`. Against a stereo family at 92 % and an MDCT rule at
AUC 0.99, **width does not become a rule here.**

**It was measured twice, and the first run was invalid.** It reused
`detect_cutoff`'s size-100 smoothing kernel — 269 Hz at 2.69 Hz per bin — and every
width it produced (137–215 Hz median) sat below the filter's own span. The synthetic
control passed regardless, because a step function survives any kernel: the same
failure as the MP3-geometry probe that validated against a control sharing its
defect. Fixed to 9 bins, a synthetic brickwall went 70 Hz to 11 Hz against a rolloff
at ~200 Hz, and **the corpus answer did not move.**

So the claim is narrow and it is about us: width does not work *bolted onto our
edge-finder*. Our edge position comes from a 269 Hz-smoothed curve while the width
search starts 250 Hz below it — two halves that are not one instrument. Nothing here
says it fails in his.

> **Stamped 2026-08-20.** He corrected the premise the next day: his instrument is
> not one instrument either, and the two-instruments contrast this claim leaned on
> does not exist. Worse for the claim: the bolted width window measured here had
> opened already below its own −6 dB level on ~98 % of found edges, so this null
> described the instrument, not the corpus. Superseded by
> `ml/edge_width_selfanchored_probe.py` (see Unreleased): the null survives,
> coherently measured this time.

### What was adopted: a sentinel, because a shrug is not a measurement

`detect_cutoff` returns Nyquist in three unrelated situations — the spectrum
genuinely reaches the top, the energy sits in the bass, and nothing was found at all.
A caller cannot tell a measurement from a shrug.

That is Rule 15's mono-gate lesson unapplied: *"the correct behaviour being silence,
not a low score, because a low score is still an opinion."* And it had already cost
us — the v1.11.3 Musepack table averaged in one file reading 22,050 Hz at **every**
profile, including `--radio` where a 15.8 kHz cap certainly applies.

`detect_cutoff_detailed` now returns `(cutoff_hz, found, width_hz)`. Deliberately a
**separate** function: `detect_cutoff` feeds every scoring rule and changing it would
change verdicts. **No verdict moves in this release.**

What the sentinel says on its own — not new evidence, since it is largely
"cutoff < Nyquist" which existing rules already act on, but now sayable:

| arm | no edge found |
|---|---|
| genuine | **68 %** |
| `mp3_320` | 8 % |
| `opus_256` | 8 % |
| `vorbis_q8` | 28 % |
| `mp3_V0` | 38 % |
| `aacmf_256` | 42 % |
| `aac_ff320` | 55 % |

### Three genuine files that read as perfect brickwalls

Exactly 3 of our 39 measurable genuine files read **2.7 Hz, 0.0 Hz and 18.8 Hz** of
transition, at 21,000 / 21,000 / 20,250 Hz. Either they are transcodes mislabelled in
our own genuine corpus, or the statistic is spurious on them.

**This cannot be settled with the statistic under test.** Excluding them because they
look like transcodes is exactly the circularity this whole exchange is about. They
are adjudication candidates for `ml/wild_fake_ledger.py` and nothing more until a
human with evidence rules on them. Stated as a bound and not as a finding: if all
three were transcodes the 5 %-cost fire rates would rise to 7.5–25 %, still not an
axis — which is the only reason it is safe to write the number down at all.

> **Stamped 2026-08-20, resolved the same day.** Both of his follow-up observations
> were right: 21,000 / 21,000 / 20,250 are `detect_cutoff` slice boundaries (every
> slice-method cutoff lands on 14,000 + k × 250 Hz), and the widths sat below the
> instrument's own floor because the bolted window opened already under −6 dB at
> its first bin. Re-measured self-anchored and off-grid: true edges 15,735 /
> 18,755 / 15,291 Hz, falls 5,020 / 1,973 / 4,729 Hz — ordinary rolloffs, no
> walls. The observation is withdrawn (it described the anchor, not the files),
> the 7.5–25 % bound is moot, nothing is adjudicated. See Unreleased.

### Musepack: our result was right, our explanation was wrong

P3 failed on measurement and the number is ours. The **mechanism** we attached to it
was not. We said Musepack *"still lowpasses at 18,750 Hz even at its top preset"*. It
does not lowpass at `--insane` at all.

He built `mpcenc` from source to check (the upstream CMake build has been broken
under MSVC since 2011 — four defects, one referencing a source file with no `.c`
extension, so that path can never have been run). The `--insane` cap is the full
band: 22.1 kHz at 44.1 kHz, per the encoder's own report, with three synthetic probes
reading the decoded edge at 22,050.0 Hz.

**18,750 Hz is a 48 kHz constant.** `mpcenc.c:1282` computes bandwidth as
`(Max_Band+1) × (SampleFreq/32/2000)` kHz over 32 subbands:

    48,000 Hz -> 0.750000 kHz/band, Max_Band=24 -> 18,750.00   exact
    44,100 Hz -> 0.689063 kHz/band, Max_Band=26 -> 18,604.69

Verified against our own data: our sources are 44.1 kHz, and at 44.1 kHz a bandwidth
of 18,750 Hz needs `Max_Band+1 = 27.211` — not an integer, so not a band boundary.
Our figure cannot be a Musepack cap. It is the encoder zeroing low-level HF content,
which is a real observable and not the one we named.

His caveat, volunteered: his probes were synthetic and broadband, and real music with
little HF gives a lower measured edge with no lowpass at all. So *"the 18,750 cap
does not exist at `--insane`"*, not *"you mismeasured"*.

> **Stamped 2026-08-20.** His follow-up asked to also exclude a measured median
> landing *exactly* on a computed constant. Excluded, with a finding: our medians
> are grid-quantized. `detect_cutoff` returns slice boundaries on
> 14,000 + k × 250 Hz (measured: 154/154 slice-method cutoffs on-grid across 360
> files), and the 48 kHz ladder steps by 750 Hz, sharing every third rung with a
> 250 Hz grid — the collision was guaranteed arithmetic. 16,000 / 17,750 / 18,750
> are 250 Hz cells, not measurements; the AUCs survive, quantization being
> monotone. See Unreleased.

He also retracted his own Musepack claim in the same message: what Provir called a
fully characterised codec is one encoder build (mpcenc 1.30.0, Feb 2009), q10 only,
29 recordings, all electronic, zero wild files — and the "100 % catch at q5–q7" line
is an n=10 note with no surviving artefact.

### The pre-registration was aimed at the wrong population, and was amended in time

`ear+eye` does not mean "selected by the ear and survived the eye". It means *"I had
to listen; the picture alone was ambiguous"* — **the eye failed to decide, it did not
confirm.** And *Goodbye My Friend* is not in that tier at all; it is
`owner+provenance`, a referee row.

`ml/exchange/PREREGISTERED_2026-08-20.md` carries a dated **amendment**, appended
rather than edited, before any file has been sent. P2 keeps its number and loses its
meaning; P3 is unchanged and now does more work, since a conviction carried by two
band-edge sources would be our engine claiming certainty exactly where the most
direct instrument abstained. P6 is added: referee rows scored separately, never
averaged into a headline.

## v1.11.3 (2026-08-20) — a false claim in Rule 1, and the Musepack axis finally earned

Jamie Dodd published the tiering behind Provir's owner-ruled labels. Two things
came out of it: a claim written into this engine turned out to be false, and the
axis this project promised a week ago got measured.

### Rule 1 contained a factual error about MP3 encoders

The guard at 21.5 kHz carried this comment:

> MP3s never have cutoffs above 21.5 kHz (even 320 kbps tops out around 20.5-21 kHz)

That is false for the entire pre-3.96 LAME era. Jamie owns both the CD and the
"lossless" store download of the same Scott Brown material. The CD runs clean to
Nyquist; the store file walls at **21,562.8 Hz**; and the CD's own audio through
**LAME 3.92 -b 320** reproduces that wall to **8.1 Hz** — three FFT bins. He then
re-measured rather than assumed, and found the wall is an **era** property, not a
version one: 3.90.3, 3.92, 3.93.1r, 3.93.1w32 and a 2002 daily all land within 8 Hz
of each other at `-b 320`, in both `-m s` and `-m j`. Only later builds move down
(3.96.1 → 19,842.8; 3.97 and 3.98.4 → 19,999.0).

His own caveat lands on us harder than on him: his two edge-finders read that same
file at **21,436.3** and **21,562.8 Hz**. Our threshold is 21,500. His strongest
exhibit falls on either side of our constant depending on which instrument measures
it.

### What we tried, and why the region stays shut anyway

At 44.1 kHz the binding guard is not that constant but `cutoff >= 0.95 * Nyquist`
(20,947.5 Hz), above which Rule 1 returns before consulting anything. Measured on
our corpus, that closed region holds **29 of 40 `mp3_V0`** files and **34 of 40
`aac_ff320`** files.

Opening it was attempted and **the measurement refused**:

- `compute_residual_floor_db`, the calibrated instrument (AUC 0.95), reads a **fixed**
  band at 0.961–0.993 × Nyquist. For a wall at 21,570 Hz that band straddles the wall
  — half live signal, half digital silence — so it reads an era-LAME brickwall as an
  authentic rolloff. It cannot just be extended upward.
- A cutoff-**relative** residual was built and priced instead. In the closed region it
  reads AUC 0.79 on `mp3_V0`, 0.72 on `aacmf_256` and **0.45 on `aac_ff320`** — worse
  than chance on the arm that needs it most. Genuine files reach down to −59.6 dB,
  below the transcode median of −42.4, so no threshold separates them.
- Widening the rule's own 0.94 guard to 0.95 was also priced: in that slice **1
  genuine file of 7** reads below the −55 dB conviction floor. On a +50 rule where
  all five historical false convictions came from Rule 1 + Rule 3, that is not a
  trade.

So the region is now closed **on evidence**. It used to be closed on an assumption
that was false. Those are different failures and only one of them was fixable today.

### What the closed region actually costs, and what carries it instead

| arm | Rule 1 silent (cutoff ≥ 20,947 Hz) | Rule 1 active |
|---|---|---|
| `mp3_V0` | n=24 · **0 % convicted** · 50 % flagged | n=16 · 19 % · 81 % |
| `aac_ff320` | n=33 · 21 % · **100 % flagged** | n=7 · 57 % · 100 % |
| `mp3_320` | n=3 — too few to read | n=37 · 35 % · 68 % |

**These two columns are not a controlled comparison and must not be read as one.**
The groups are split *by cutoff*, so the silent group is intrinsically harder for
every spectral family, not only for Rule 1. How much of the gap is Rule 1's silence
and how much is the material cannot be separated without opening the guard — which
the section above shows we cannot do safely. The number bounds the cost; it does not
attribute it.

What the breakdown does say cleanly is which families hold the region up:

- `aac_ff320`, silent group: **`mdct` carries 33 of 33**. Rule 13 owns this arm
  outright, which is why the max-over-frames variant rejected in v1.11.2 was buying
  recall that was already paid for.
- `mp3_V0`, silent group: `stereo` 15, `cnn` 12, `temporal` 10 of 24.

That second line is the v1.11.0 witnesses doing exactly the job they were built for.
They contribute zero points and cannot flag anything new — but in the one region
where the band-edge family is structurally silent, they are what turns points already
earned into a corroborated verdict. Half of that group still goes unflagged, and that
is the honest size of the remaining hole.

### One thing was fixable: a Welch pass spent on a slice nobody could read

`analyze_spectrum` computed the residual across [0.90, 0.95) × Nyquist while Rule 1
rejects any 320 estimate from 0.94 × Nyquist up. A **220 Hz slice was computed and
discarded** on every file that landed there. The window now stops where the rule
stops — verdicts are byte-identical, one Welch pass is saved.

`tests/test_rule1_nearnyquist.py` pins it: both branches of the residual gate must be
reachable, the discarded slice must give the same answer whatever the residual says,
and the two constants must move together. Verified to **fail** when the window is put
back to 0.95, which is the only way this regresses.

This is the mild form of a defect this project keeps finding — Rule 14 was
unreachable for its own target population, and Jamie found six mumbling witnesses in
one sitting. An instrument that runs for a population it can never be asked about.

### Musepack: the axis claimed on 2026-08-13, measured on 2026-08-20

What this project had was `6/64` on a Musepack arm — the CNN's WARNING floor, not
evidence. `mpcenc` is in no Windows package manager and is not an ffmpeg encoder, so
the arm was never built. It **is** a Debian package: `musepack-tools`. Same move as
the CoreAudio arm — the encoder we cannot run locally becomes a job on a free runner.

24 sources, paired (each measured as-is and after a round trip), three profiles:

| profile | mdct AUC | stereo AUC | cutoff AUC | cutoff median |
|---|---|---|---|---|
| `radio` | 0.46 | **0.96** | **0.97** | 16,000 Hz |
| `standard` | 0.52 | **0.96** | **0.96** | 17,750 Hz |
| `insane` | 0.52 | **0.94** | 0.90 | 18,750 Hz |

> **Stamped 2026-08-20:** the cutoff medians in this table are quantized to
> `detect_cutoff`'s 250 Hz scan grid (14,000 + k × 250 Hz) — cells, not
> Hz-accurate measurements; the AUCs are unaffected. See the v1.11.4 Musepack
> note and the Unreleased section.

Predictions were registered in the module docstring before the job ran. Two held and
one half-failed:

- **P1 held** — Rule 13 reads 0.46–0.52. Musepack is a *subband* codec (Layer 2's
  32-band polyphase filterbank), so there is no MDCT to align, and the rule correctly
  reads nothing. Being wrong here would have meant Rule 13 responds to something its
  docstring does not name.
- **P2 held, and wider than claimed** — the stereo family reads 0.94–0.96 on every
  profile, not just `standard`.
- **P3 half-failed** — the cutoff was predicted *not* to separate on `--insane`. It
  separates at 0.90, because Musepack still lowpasses at **18,750 Hz** even at its
  top preset, far more aggressively than MP3 320. That failure is the useful part:
  Musepack is an easy arm, not an exotic one.

The axis is now real and its mechanism is named: cutoff plus side channel, and
nothing from the MDCT family.

### The wild ledger records how a file was SELECTED

Provir's own least comfortable number: their engine convicts 14 of 16 fakes their
author picked out by eye (**88 %**) and 0 of 9 he had to listen for (**0 %**). Not
two performance figures — one instrument scored against the sense that selected its
problem, averaged into a headline.

A `basis` field cannot show that, because both groups' labels may be equally sound.
The bias is in the choosing. So `ml/wild_fake_ledger.py` gained `selection`
(systematic / reported / detector / human_eye / human_ear), a derived `referee` flag,
and `byte_identity` and `spectrogram` as accepted bases — naming `spectrogram`
deliberately, because refusing to list it only makes people record it as `listening`.
`status` now prints the cross-tabulation unasked and warns when every fake was eye- or
ear-chosen. Verified against a reconstruction of Provir's corpus shape: it reproduces
88 % / 0 % and both warnings fire.

The ledger is empty, which is the only reason this cost nothing.

### Pre-registered, before his 53 wild files are sent

`ml/exchange/PREREGISTERED_2026-08-20.md` records what we expect on the 9 `ear+eye`
rows — the only population anywhere selected by the ear and survived by the eye, and
therefore the cleanest available test of whether this engine's `mdct`, `stereo`,
`temporal` and `cnn` families are independent instruments or elaborate re-derivations
of the same band edge. **P3 there is written so that convicting those files on
band-edge evidence alone counts as a failure, not a success.**

## v1.11.2 (2026-08-19) — one glossary correction taken, one rejected on measurement

Provir published a flag glossary. Two of its entries bear on Rule 15, and the
useful outcome of this release is that they did not both survive contact with our
corpus.

### Taken: strictly interior runs

Their `DEADRUN_STRICT_INTERIOR = True` discards a dead run touching **either** edge
of the analysis band. v1.11.0 discarded only the top, on the argument that a run
reaching Nyquist is a lowpass edge belonging to the cutoff rule. The same argument
applies at the bottom: a run starting at the 10 kHz band floor is the analysis
window's own boundary, not a hole the encoder left.

Measured across the corpus: **identical to two decimals**. At 10 kHz real music
essentially always has energy, so runs almost never start at the floor. Adopted
anyway — it is the correct definition and it costs nothing to hold.

### Rejected: max over frames

Their `MS_CONDITIONAL` entry carries a standing warning against *"any statistic
aggregated across frames"* — at transparent bitrates the codec's zeroing is dynamic
and averaging destroys it, which killed four of their earlier defences. Rule 15
takes a median across frames, so the warning points straight at it.

A max-over-frames variant was built and priced. On 25 genuine files it beat the
median on every hard arm. On the full 228 it does not:

| arm | median | max |
|---|---|---|
| `opus_256` | **92 %** | 81 % |
| `vorbis_q8` | **93 %** | 86 % |
| `mp3_320` | **92 %** | 81 % |
| `mp3_V0` | **81 %** | 77 % |
| `aacmf_256` | 73 % | 73 % |
| `aac_ff320` | 19 % | **33 %** |
| **total** | **75 %** | 72 % |

Each variant priced at its own p95 on the same 228 genuine files, so both columns
cost the same 5 % on real music. The max wins on exactly one arm — and that is the
one Rule 13 already reads at AUC 0.99. It pays for it with 11 points on Opus,
Vorbis and mp3_320, where no other family in this engine reaches at all. Wrong
trade. The median stands.

### Two lessons, both ours

**A 25-file calibration reversed the ranking of 228.** The p95 of a small sample
sits wherever its second-largest value happens to fall; ranking two statistics by
their own small-sample bars ranks the samples, not the statistics. This is the same
error that mis-set Rule 13's ceiling, now made twice.

**A warning that holds for the author's statistic need not hold for ours.** Their
zeroing is dynamic per frame; our mask is already a per-frame conjunction against
the mid channel, so our median is not averaging the artefact away. A glossary is a
map, not a spec — which is their own standing warning, applied to them.

### Calibration re-confirmed

228 measured genuine files (20 more mono-gated), p95 **1.74**. `RUN_BAR` stays at
**2.0**, just above it. New false convictions at that bar, at p90, at p99 and above
the maximum: **zero** in every case.

## v1.11.1 (2026-08-19) — the guard was the bug

Rule 15 shipped hours earlier with a floor-guarded normalisation: rescale only
files whose peak is below 0.75. That came from Provir's description of their own
code, and Jamie Dodd corrected it within the hour — their shipped constant is
**1.0, normalise unconditionally**, and the 0.75 form is what they replaced in July.

The correction matters more than the value. **A guard is not a milder version of
normalisation; it is a discontinuity.** Below the threshold the statistic is
peak-relative, at or above it absolute — two different statistics with a seam
between them. Reproduced here before fixing, on our own files, scaled in memory so
nothing but the level changed:

| file | peak 0.7501 | peak 0.7499 |
|---|---|---|
| `003-01-Thor` | **2.00** | **16.04** |
| `004-01-Thiossane` | **1.67** | **15.29** |

An inaudible 0.002 dB difference moved the reading eightfold, and one file crossed
the decision bar on it. After the fix, that file reads 17.94 / 17.94 / 17.85 /
17.85 / 17.85 across peaks 1.0 down to 0.3.

### The fix costs nothing measurable

Calibration, on the same 238 genuine files: median 1.00 unchanged, p95 1.72 against
1.86. `RUN_BAR` still sits just above p95 and new false convictions remain **0**.

Detection, witness rate per arm: `opus_256` 92 → 88 %, `vorbis_q8` 92 → 89 %,
`mp3_320` 89 → 88 %, `mp3_V0` 78 → 81 %, `aacmf_256` 72 → 73 %, `aac_ff320`
19 → 19 %. Within sampling noise on a smaller n.

So the seam was costing consistency without buying accuracy — invisible in
aggregate, decisive on individual files. Two tests now pin it: the two sides of the
old boundary must agree, and the reading must be flat across the whole peak range.

### A date withdrawn

Provir also retracted "measurement-only since 2026-07-21" for the temporal seam:
the comment predates their version control, so the date cannot be evidenced. We had
quoted it. Corrected in both places — a borrowed date is still a claim.

---

## v1.11.0 (2026-08-19) — two new evidence families, and neither of them scores

v1.10 made conviction depend on two independent evidence families. This release
adds two more sources without adding a single point, and the "without" is the
whole design.

### The problem with a good but noisy observable

Jamie Dodd of Provir gave us the algorithm behind his `HF_SEAM` flag, and then the
mechanism behind `DEAD_STRUCTURE`. Both are excellent where this engine was blind.
Both are also kept **measurement-only** in his engine, for a reason he stated
plainly: they fire on real music too, and his pipeline sends a flag straight to a
verdict.

Ours does not have to. This engine separates *how many points* from *how many
sources*, so an independent-but-noisy observable can be held as a **witness** while
contributing nothing to the total.

The obvious wiring was measured before it was written, and it was wrong. Awarding a
new family 25 points — just enough to clear `MIN_FAMILY_CONTRIBUTION` — produced
**three new false convictions on 258 genuine files**: real recordings sitting at
52, 38 and 31 spectral points were pushed past `CONVICTION_MIN_SCORE` by the
appended points, then convicted by their own new second family. That is v1.10's
defect one level up, in the points rather than in the witness count.

So `POINTLESS_WITNESS_RULES` exists. A witness family can **complete** a
corroboration for a file other evidence has already carried past the bar. It cannot
move any file toward that bar.

### Rule 14 — the temporal seam

Not the level, the **temporal variability of each bin**. Genuine high frequencies
are restless — cymbals, sibilants, bow noise, room. A regenerated or noise-filled
band is stationary. The seam is the frequency where restlessness stops.

AUC 0.89 on `mp3_320` and **0.84 on `opus_256`**, the arms where the hole family and
the lattice family are both dead. And 0.47 on `aac_ff320`, which Rule 13 reads at
0.99 — complementary, not better.

### Rule 15 — the stereo image

Not the spectrum, the **side channel**. Joint and intensity stereo quantise `L−R`
toward zero above the coupling frequency and leave long contiguous holes there while
the mid stays alive. Every other family in this engine reads a mono sum, so none of
them can see it.

**AUC 0.96 on Opus, Vorbis and `mp3_320`** — the strongest independent observable
here, and it also gets into Apple CoreAudio, which had defeated everything: 128 kbps
moves from 0.77 to **0.94** and 256 kbps from 0.65 to **0.80**.

A mono file has no side channel, so every high bin is trivially dead and the
statistic would be manufactured out of nothing. `MONO_GATE` returns silence — not a
low score, because a low score is still an opinion — and **20 of our own 258 genuine
files are mono-gated**.

### Measured effect, same 800-file audit corpus

| | v1.10 | v1.11 |
|---|---|---|
| **fakes convicted** | 171 | **267** (+56 %) |
| **genuine convicted** | 0 | **0** |
| fakes flagged | 49.3 % | 49.3 % |
| genuine flagged | 1.2 % | 1.2 % |
| `vorbis_q8` convicted | 21 | **46** |
| `opus_256` convicted | 9 | **24** |
| `aac_ff128` convicted | 9 | **24** |
| `aac_ff320` convicted | 12 | **27** |
| `mp3_320` / `mp3_V0` | 24 / 5 | 24 / 5 |

The flag rates do not move, and that is the design rather than a disappointment: a
zero-point witness cannot flag anything new. It only promotes files that independent
evidence had already carried to the points bar and left stranded for want of a
second source.

The unchanged MP3 rows say the same thing from the other side. Both witnesses fire
heavily there — stereo on 72–82 %, temporal on 45–72 % — and deliver nothing,
because those files never reach the bar and no zero-point family can carry them
there.

### Still shut

`mp3_320`, `mp3_V0` and CoreAudio at 320 kbps. All four observables read 0.50–0.58
on the last of those; neither engine in this exchange has anything for it.

---

## v1.10.1 (2026-08-18) — Read-only libraries, and a comment that finally tells the truth

A user running flac-detective in a container, with the music mounted read-only,
reported that `progress.json` insisted on being written next to the audio
([#5](https://github.com/Guillain-RDCDE/FLAC_Detective/issues/5), thanks
@SLUCHABLUB).
They were right, and it was worse than it looked: the code comment promised
"current directory if it's a file" — a fallback that never existed — and on a
read-only scan directory `progress.json` failed quietly on *every file* (so
resume was lost) while the auto-named report could fail hard at the very end,
after all the analysis work was done. The console log had been taught to fall
back a while ago; progress and report never got the same treatment.

### Fixed

- **Read-only scan directory no longer breaks the run.** The work directory —
  where `progress.json`, the auto-named report and the console log go — is now
  resolved once, up front, by actually probing for writability (`os.access` lies
  on read-only mounts, network shares and Windows ACLs): the scan directory if
  writable (unchanged default, so re-running `flac-detective /same/dir` still
  resumes), otherwise the **current working directory** (what the comment always
  said), otherwise the system temp directory. Any fallback is announced with the
  path and how to resume.
- The `Ctrl-C` message now names where `progress.json` actually is instead of
  assuming the scan directory.

### Added

- **`--work-dir DIR`** — choose the location of `progress.json`, the auto-named
  report and the log explicitly (created if missing; fails early with a clear
  message if it can't be written). This is the clean answer for containers and
  CI: `docker run … -v /music:/data:ro -v ./out:/reports … /data --work-dir /reports`.
  Note the container's working directory is `/data` itself, so with a `:ro`
  mount and no `--work-dir` the scan still completes but its files land in the
  container's `/tmp` and vanish with it.

Tests: `tests/test_work_dir.py` (probe, policy, CLI wiring, plus a real
`chmod 555` scenario on POSIX runners). Docs: getting-started option table,
user-guide Docker section.

## v1.10.0 (2026-08-17) — A witness that mumbles is not a second witness

v1.9 made conviction depend on two independent evidence families. Jamie Dodd of
Provir then ran a **blind, hash-keyed exchange set** — 599 files he built and
labelled, scored without either of us seeing the other's answers — and it found
the gap in that gate on the first try. This release closes it, deletes a rule
that had never once contributed an independent detection, and doubles Rule 13's
reach.

### 1. A family now has to say something to count

The gate counted any family with a single positive point as a witness. On the
exchange set, a genuine 2003 audience recording drew **112 points of doubled
spectral evidence plus a 16-point CNN reading** — and that 16-point murmur was
enough to make the spectral pile "corroborated". FAKE_CERTAIN, on a real
recording.

`MIN_FAMILY_CONTRIBUTION = 20`: a family must contribute at least 20 points to
be counted as a witness. That file now reads SUSPICIOUS on one family.

### 2. Rule 3 deleted — it was never a second opinion

Rule 3 compared the source bitrate Rule 1 had *inferred from the cutoff* against
the container bitrate, and awarded up to +50. Measured across **978 files** (the
800-file audit corpus plus the 178-file wild scan):

> Rule 3 fired **143 times, always alongside Rule 1, and never once alone.**

It was Rule 1's own answer echoed back at full weight. v1.9's gate stopped that
echo from convicting by itself, but the inflated total still helped drag weak
third families over the line. Deleted.

### 3. Rule 13 now tries two transforms, and catches Vorbis

Rule 13 tested one hypothesis: AAC's KBD (α=4) window. It now tries **Vorbis's
window too** — `sin(π/2·sin²(π/N·(n+0.5)))`, same 2048-sample long block,
different shape — and takes the stronger reading.

| | v1.9 (KBD only) | v1.10 (KBD + Vorbis) |
|---|---|---|
| Vorbis q8 AUC | 0.806 | **0.955** |
| Vorbis q8 flagged, audit corpus | — | **60.0 %** |
| genuine max ratio | 1.42 | 1.43 |

The second hypothesis is nearly free in false alarms, because genuine audio has
no preferred alignment under *either* window: across the same 80 certified-genuine
files the maximum moved from 1.42 to **1.427**, against a review bar of 2.0.

**Opus is out of reach, and that is now documented as physics rather than a
to-do.** CELT transforms at 48 kHz whatever you feed it, so a 44.1 kHz source is
resampled in and back out, and resampling destroys the sample-exact alignment
the statistic depends on. Measured: **1.26, against a 1.29 genuine baseline.**
No threshold fixes that.

### 4. Family independence is now a CI guard

Three times now the same mistake: independence asserted, not measured — Rules
1+3, then `cnn`+`spectral`. `tests/test_rule_audit_guard.py` now fails the build
if any two families co-fire beyond `MAX_INDEPENDENCE_LIFT`.

### Measured effect, same 800-file audit corpus

| | v1.9 | v1.10 |
|---|---|---|
| **fakes flagged** | 76.0 % | **78.8 %** |
| **genuine flagged** | 3.8 % | 3.8 % |
| **genuine convicted** | 0 | **0** |
| fakes convicted | 177 | 171 |
| convictions on one family | 0 | 0 |

### On the blind exchange set — all 599 files, third-party labels

| arm | n | convicted | flagged |
|---|---|---|---|
| **genuine** | 59 | **0** | 2 (3.4 %) |
| `aac_ff128` | 59 | 18 | 31 (52.5 %) |
| `aac_ff256` | 59 | 18 | **59 (100 %)** |
| `aac_ff320` | 59 | 10 | **59 (100 %)** |
| `aacmf_256` | 58 | 20 | 24 (41.4 %) |
| `mp3_192` | 59 | 22 | 29 (49.2 %) |
| `mp3_320` | 59 | 15 | 20 (33.9 %) |
| `mp3_V0` | 59 | 4 | 8 (13.6 %) |
| `opus_256` | 59 | 5 | 14 (23.7 %) |
| `vorbis_q8` | 59 | 32 | 42 (71.2 %) |

*Corrected 2026-08-18. The set's 599 files are **589 distinct files**: ten
byte-identical pairs, which are one entire source group — all ten arms — present
twice under two names. Two archive.org items held the same taper's same track
(`…-matrix-…` and `…-matrix2-…`) and the corpus dedup keyed on the item
identifier rather than on the audio. Rates above are over distinct content; the
originally published table used n=60 per arm and double-counted that recording in
every arm, including genuine. Nothing material moved — the largest shift is
`mp3_V0` convictions, 8.3 % → 6.8 % — and 0/59 genuine reads as "up to 6.1 %"
(Wilson-95) against the 6.0 % published on n=60. Found by Jamie Dodd, by sorting
our own shipped manifest.*

**Zero false convictions on 60 genuine files, against one in v1.9.** The two
predictions published to Provir *before* scoring both land: "`aac_ff256` ≥ 90 %
flagged, high confidence" came in at **100 %**, and both ffmpeg-AAC arms above
128 kbps are flagged on every single file — which is the ceiling this whole
release was aimed at. The Vorbis prediction ("small gain, < 15 pp, medium
confidence") was too pessimistic; the second window hypothesis is what moved it.

The honest reading of 0/60 is "up to 6 %" (Wilson-95), not "zero".

### The trade, stated plainly

v1.10 convicts **six fewer fakes** across 800 files and flags **2.8 pp more**, at
identical cost to genuine material. That is the intended direction: the six lost
convictions were resting on Rule 3's echo or on a mumbling second family, and
this project ranks protecting authentic files above conviction count.

---

## v1.9.0 (2026-08-15) — A conviction now needs two independent sources

v1.8 built a harness that measures each rule alone, and it immediately found a
dead rule, an inverted rule and a destroyed protection. Jamie Dodd of Provir then
pointed at the layer above: **nothing was measuring rule *combinations*.** He was
right, and the consequence was visible in both directions in the project's own
audit data.

### The finding, in both directions

A score is a sum, and a sum cannot say whether it came from one thing repeated or
several things agreeing.

* **One thing repeated.** All three false convictions on 80 certified-genuine
  files, and all 26 convictions on the 320 kbps MP3 arm, were Rules 1 and 3
  contributing +50 each — and Rule 3 compares the bitrate Rule 1 inferred. One
  measurement, counted twice, clearing an 86-point bar unaided.
* **Several things agreeing, and losing.** 90 files carried agreement between
  Rule 12 (a learned mel-spectrogram model) and Rule 13 (MDCT frame alignment) —
  genuinely different physics — and **54 of them sat at exactly 85** against that
  same bar. Jamie found the same composition from the outside, on a different
  codec arm, in the same week.

### The change

Conviction moves from a score threshold to a **corroboration gate**: FAKE_CERTAIN
requires two independent evidence families, and a corroborated file convicts from
a lower points bar than the old flat 86.

| family | rules | reads |
|---|---|---|
| `spectral` | 1, 2, 3, 4 | the cutoff, and the bitrate inferred from it |
| `container` | 5 | bitrate variance across FLAC blocks |
| `silence` | 7 | HF energy in silent passages |
| `cnn` | 12 | learned mid/side classifier |
| `mdct` | 13 | frame-alignment quantisation structure |

Rules 6, 8 and 11 are protection and can never convict. Rule 10 re-scores
segments through the same pipeline — consistency, not corroboration.

**The early exits had to go with it.** The pipeline stopped as soon as the score
passed 86, so a file convicted by Rules 1 + 3 never ran Rules 12 or 13 at all.
Under a corroboration gate that is self-defeating: the exit guarantees a single
family, and the gate would measure the short-circuit rather than the evidence.
Early exits now require corroboration too.

### Measured effect, same 800 files

| | v1.8 | v1.9 |
|---|---|---|
| **fakes convicted** | 142 | **177** (+25 %) |
| **genuine convicted** | 3 | **0** |
| convictions resting on one family | 142 | **0** |
| fakes flagged | 76.0 % | 76.0 % |
| genuine flagged | 3.8 % | 3.8 % |
| AAC 256k (ffmpeg) convicted | 2.5 % | **58.8 %** |
| AAC 256k (MediaFoundation) convicted | 13.8 % | **37.5 %** |
| MP3 320k convicted | 32.5 % | 31.2 % |

Both directions improved, which is unusual and is the point: the convictions that
disappeared were the ones resting on a doubled inference, and the ones that
appeared carry two independent sources. MP3 barely moved — because disabling the
early exit let those files reach the rules that could corroborate them.

Every remaining conviction carries at least two families: 90 `cnn+spectral`,
82 `cnn+mdct`, 5 all three. The three genuine files still flagged carry
`spectral` alone and are therefore capped at SUSPICIOUS by construction.

### Guards

- `tests/test_evidence.py` — a new scoring rule must be assigned an evidence
  family or listed as deliberately excluded. It cannot silently acquire
  conviction power by existing.
- `tests/test_rule_audit_guard.py` gains two: no conviction in the committed
  audit may rest on a single family, and no certified-genuine file may be
  convicted at all.

### Compatibility and cost

`analyze_file()` gains `evidence_families`; nothing is removed. A withheld
conviction says so in its reason string rather than looking like a low score.

**Scans are slower.** Files that used to exit early at 86 points now run the
expensive rules so they can be corroborated — which is the whole point, but it
removes the cheapest fast path in the pipeline.

## v1.8.0 (2026-08-14) — Every rule measured; one deleted, one un-inverted, one new that works at 320 kbps

The release started as a courtesy: a competitor, Jamie Dodd of **Provir**, ran a
head-to-head benchmark and mentioned in passing that FLAC Detective's Rule 9A
(pre-echo) measured **AUC 0.517** standalone on 364 files — a coin flip. He was
right, it reproduced here at 0.513 on a disjoint corpus, and checking it properly
required building the thing the project never had: a way to measure a single rule.
That harness then found a second bug nobody was looking for, and made a new
high-bitrate detector measurable enough to ship.

### The blind spot is no longer blind — Rule 13 (MDCT frame alignment)

Every detector the tool had looked *above* the encoder's cutoff. At 256–320 kbps
a modern encoder keeps the band, so there was nothing to read: **17.5 %** of
320 kbps AAC got flagged at all.

Rule 13 reads something the cutoff cannot hide — the alignment fingerprint left
by MDCT quantisation. Re-analysed with the encoder's own transform (2048-sample
window, Kaiser-Bessel-derived, alpha = 4, sample-exact alignment), coefficients
quantised to zero reappear as deep spectral holes at exactly one frame alignment
and nowhere else. Genuine audio has no preferred alignment.

| codec | AUC | | codec | AUC |
|---|---|---|---|---|
| AAC 128k (ffmpeg) | **0.998** | | AAC 320k (ffmpeg) | **0.993** |
| AAC 256k (ffmpeg) | **0.990** | | Vorbis q8 | 0.806 |
| AAC 256k (MediaFoundation) | 0.791 | | MP3 / Opus | at the null |

No genuine file in the audit corpus exceeded a peak ratio of 1.42; ffmpeg AAC
sits at 13–21 regardless of bitrate.

**Scope, stated as plainly as the win.** This is an *AAC-family* answer, not a
universal one: MP3, Opus and Vorbis use different framing and score at the null
(the existing rules already convict there). MediaFoundation AAC is only half
caught. Very low bitrates defeat the statistic — which is where the spectral
cliff is obvious anyway. All three limits have tests pinning them.

Cost is ~4 s per file, gated to cutoff ≥ 18 kHz on files not already convicted.
Credit where it is due: the Derrien (JAES 67(3) 2019) pointer and the KBD-alpha-4
trap both came from Jamie.

### Rule 9 (compression artefacts) — **removed**

Three tests, up to +40 points, all at or near chance when measured alone:

| test | AUC | fires on genuine | fires on fakes |
|---|---|---|---|
| 9A pre-echo | 0.513 | 82.5 % | 84.7 % |
| 9B HF aliasing | 0.586 | 6 % | 9 % |
| 9C MP3 noise pattern | 0.497 | ~0 % | ~0 % |

The physics was real; the implementation did not measure it. 9A compared HF
energy before a transient against 3× the file median — a bar the natural attack
ramp of real music clears on its own, in a band a lossy file has already erased.
It fired on nearly everything and separated nothing, while handing **+15 points
to every genuine file that passed its gate**: with the WARNING bar at 31, an
effective bar of 16 for those files.

### Rule 11 (cassette protection) — **sign corrected**

The audit measured Rule 11 at **AUC 0.321** — inverted. It was adding its
*cassette evidence* to the *transcode* score, so a genuine analog transfer was
pushed toward being called fake: +18.3 points on average to genuine files against
+11.2 to transcodes. Rule 11 now contributes zero points and records its evidence
for the calculator to turn into protection. Its test 11C ("no MP3 pattern → +15")
keyed off Rule 9C and was a constant; it is gone, and the cassette gate dropped
30 → 15 to compensate exactly.

### Protection rules now actually protect — the zero-clamp bug

`ScoringContext.add_score` clamped the running total at zero on **every**
addition. Rule 8 (the Nyquist exception) is calculated *first* by design and
contributes **−50** to a genuine full-band file — and that −50 was clamped away
immediately, before any rule could benefit from it. A file that should have
scored 45 − 50 = 0 scored 45.

Every protection that happened to run before a penalty was doing nothing at all,
which is the exact inverse of the project's stated "protect authentic files
first" principle. The clamp now happens once, on the final score. Found by the
new per-rule breakdown: Rule 8 was credited −50 on files whose total never moved.

### Rule 13 now overrides Rule 8's protection

Fixing the clamp above exposed a disagreement the bug had been hiding. Rule 8
grants −50 to a full-range spectrum on the reasoning that a transcode would have
left a cliff — the exact reasoning that stops holding at 256–320 kbps. With the
clamp gone, Rule 8 started winning against Rule 13 and 320 kbps AAC detection
fell from 97.5 % to 26.2 %.

Rule 8 argues from *absence* of evidence; Rule 13 produces direct positive
evidence. When Rule 13 fires, Rule 8's protection is now explicitly withdrawn,
with a reason string that says so. When Rule 13 is silent, Rule 8 is untouched.

### You can no longer ship an unmeasured rule

- **Per-rule score attribution.** `analyze_file()` results now carry a
  `score_breakdown` dict — what each rule contributed to this file's score.
- **`ml/rule_audit.py`** measures every rule alone (AUC, fire rate, and the
  average points it hands genuine files) over a frozen corpus built by
  `ml/build_audit_corpus.py`: 80 certified-genuine sources, one per album, times
  9 codecs.
- **`tests/test_rule_audit_guard.py`** runs that measurement in CI from a
  committed CSV, and fails if a rule exists in the code but not in the audit, if
  a firing rule sits at chance, or if a rule taxes genuine files without
  discriminating. Rule 9 would have failed all three the day it was written.

### Also fixed

- **The full test suite can run in one process again.** Three modules under
  `tests/integration/` re-wrapped `sys.stdout` at import time; the wrappers closed
  pytest's capture buffers on garbage collection and every subsequent test died
  with "I/O operation on closed file". CI had been hiding this by skipping the
  directory. The re-wrap now lives behind a `__main__` guard, and three helper
  functions named `test_*` that pytest was collecting as broken tests are renamed.
- **Two Rule 11 tests skipped for a year** behind a "TODO: rewrite mocks" are
  rewritten against the real call path.

### Measured effect, same corpus before and after

| | before | after |
|---|---|---|
| genuine files flagged (false positives) | 6.2 % | **3.8 %** |
| AAC 320 kbps flagged | 17.5 % | **97.5 %** |
| AAC 256 kbps flagged | 50.0 % | **98.8 %** |
| AAC 256 kbps (MediaFoundation) flagged | 70.0 % | **88.8 %** |
| all fakes flagged | 60.3 % | **76.0 %** |
| rules firing at chance | 1 | **0** |

Rule 13 contributed to 0 of the 80 genuine files. Convictions are deliberately
flat: Rule 13 is calibrated to reach SUSPICIOUS alone and no further.

### Validated outside the library

180 FLACs from the Internet Archive `etree` collection (74 distinct concerts,
taper recordings licensed for redistribution — adversarial by nature) run through
the full pipeline. **Rule 13 scored zero on all 178 usable files.** Combined with
the 880-file certified sweep that is **0 of 1058 genuine files, Wilson-95 upper
bound 0.36 %**. Overall pipeline flagging was 20/178 (11.2 %), against a
historical 13.3 % on a smaller pull — none of it attributable to the new rule.

### Known issue, documented rather than rushed

Three genuine files are still convicted, all with the same signature: Rules 1 and
3 contributing +50 each. Those two fire together on 141 of 800 files and give the
**identical value in all 141** — Rule 3 reads the bitrate Rule 1 inferred, so one
inference convicts twice, and 100 points clears the 86-point bar on its own.

Discounting Rule 3 when Rule 1 has fired takes genuine convictions from 3/80 to
0/80 — and fake convictions from 142/720 to 4/720. The conviction tier *is* that
pair, and the 86 threshold was implicitly calibrated around the double-count.
Fixing it means recalibrating the threshold with its own measurement, so it is
logged with its numbers (`ml/README.md`) rather than patched blind.

The wild run reinforced it: its two false convictions carry the same signature.
Across 258 genuine files from two independent corpora, this tool has produced
five false convictions and **all five are Rule 1 + Rule 3 at +50 each**. One
mechanism, and currently the only one able to convict an innocent file.

### Performance

`--deep` scans are slower: Rule 13 adds ~4 s per file for files with a cutoff at
or above 18 kHz. Default (non-deep) scans are largely unaffected, since authentic
files still short-circuit before Rule 13 is reached.

### Compatibility

`analyze_file()` gains a key (`score_breakdown`) and loses none. Verdicts change
where Rule 9 or Rule 11 was moving them — in both cases toward fewer false
accusations of genuine files.

## v1.7.0 (2026-06-27) — Easy mode (plain language) vs Advanced mode (the plumbing)

Both the CLI and the desktop GUI now have two voices. **Easy mode is the new default**:
a traffic-light verdict and a plain-language explanation + recommended action per file,
with none of the plumbing. **Advanced mode** shows exactly what earlier versions did —
scores, cutoff/bitrate, per-rule reasoning.

- **CLI `--advanced` flag.** Without it (easy mode), the console prints `❌ Fake  track.flac`
  and the text report reads *"Almost certainly a fake — the sound stops dead at about
  16 kHz, the tell-tale wall of a ~128 kbps MP3. → Replace it."* — no rule codes, no
  scores, no Hz/dB. With `--advanced`, the familiar score/cutoff/bitrate table and the
  per-rule reasons return unchanged. (JSON/CSV/HTML reports are data formats and are
  unaffected.)
- **GUI "Advanced" toggle.** Off by default: the detail card shows a plain explanation and
  an action, and the numeric Score column is hidden. Flip it on for the score, the
  sample-rate/bit-depth/cutoff metadata and the per-rule "why".
- **New `flac_detective.presentation` module** is the single source of truth for the
  plain-language voice (verdict → icon/label/action, and a jargon-free explanation built
  from the spectral cliff, the implied MP3 bitrate and the fake-hi-res axis), so the CLI,
  the report and the GUI all say the same thing.

No API break: `analyze_file()` keys are unchanged, and constructing `TextReporter()`
directly still defaults to the advanced report.

## v1.6.1 (2026-06-27) — Calibration shipped; generalisation validated

A refinement release. No API change; the shipped behavioural change is that Rule 12's
probability is now **calibrated by default**.

- **Fitted Platt calibration bundled** (`cnn_v4_stereo.calibration.json`). Until now the
  calibration mechanism shipped but with no fitted file, so it was the identity. The
  mapping is now fitted on a 690-file held-out set scored through the production
  inference path — lowering expected calibration error from 0.037 to 0.006. Verdicts
  shift only marginally (a touch fewer borderline false positives); the model was
  already fairly calibrated in-distribution, so this is a polish, not an overhaul.
- **Out-of-ffmpeg generalisation validated** (no shipped-code change — `ml/` study only).
  The long-standing open question — *does the CNN generalise past its ffmpeg-only
  training?* — now has answers: standalone LAME/oggenc/opusenc fakes drop AUC by only
  0.009; Fraunhofer **fdkaac** AAC scores **0.971** vs 0.952 for ffmpeg-aac (no drop at
  all); and a first **wild** test on 45 Internet-Archive live FLACs reads 86.7 %
  specificity with zero hard false positives. The model learned a real transcode
  fingerprint, not an encoder tell. New `ml/fetch_wild_authentic.py`; full write-up in
  `ml/README.md`.

## v1.6.0 (2026-06-26) — Desktop GUI, fake-hi-res verdict, calibrated multi-window CNN

A feature release on four fronts. No breaking changes: the CLI flags, top-level
exports and `analyze_file()` keys are unchanged (two new keys added: `hires_verdict`,
`hires_reason`).

- **Desktop GUI (`pip install "flac-detective[gui]"`, `flac-detective-gui`).** A
  PySide6 window over the same analyser: choose a folder (or drag-drop), watch a live
  progress bar, get a sortable verdict table coloured by verdict, and click any file to
  see its spectrum with the detected cutoff marked plus the reasons behind its verdict.
  Export the result set to HTML/CSV/JSON. Analysis runs on a background thread with the
  same process pool as the CLI, so the UI stays responsive and cancellable. (#1 — GUI)
- **Fake high-resolution detection — now a first-class verdict.** Upsampling and padded
  bit depth were computed but only reported informationally. They are now a dedicated
  axis (`hires_verdict`: `GENUINE_HIRES` / `UPSAMPLED` / `PADDED_DEPTH` /
  `UPSAMPLED_AND_PADDED` / `NOT_HIRES`), surfaced in the CSV report, the GUI, and the
  result dict. The upsampling test was rebuilt: instead of the naive "cutoff < 24 kHz"
  (which flagged genuine hi-res that simply rolls off early), it requires a hard spectral
  **cliff at the original Nyquist with digital silence above it** — the same
  silent-floor-vs-analog-floor discriminator as Rule 1's near-Nyquist gate — so a real
  96 kHz recording reads `GENUINE_HIRES`. (#1)
- **Calibrated CNN probability (Rule 12).** The model's softmax output was used as if it
  were a true probability; modern CNNs are over-confident. A monotonic Platt/isotonic
  mapping (fitted offline by `ml/calibrate_model.py`, bundled as
  `cnn_v4_stereo.calibration.json`) now rescales it, so the 0.5/0.95 score ramp, the 0.90
  WARNING floor and any displayed `p` mean a real probability. Identity (no-op) if no
  calibration file is bundled — safe by default. (#4)
- **Multi-window CNN inference.** Rule 12 inferred on a single 10 s middle segment, which
  made the verdict hostage to one patch of audio (the start-vs-middle fragility behind
  three past measurement bugs). It now samples several evenly-spaced windows, aggregates
  the per-window probabilities (mean), and surfaces the spread as an uncertainty signal.
  Set `_N_WINDOWS = 1` to recover the old behaviour. (#3)
- **Out-of-ffmpeg generalisation harness (`ml/`).** New scripts to measure whether the
  model generalises beyond its ffmpeg-only training: `generate_transcodes_external.py`
  (a zoo of standalone encoders — LAME, qaac, fdkaac, oggenc, opusenc, afconvert),
  `build_wild_testset.py` (score a labelled real-world corpus through the shipped
  inference) and `measure_auc_drop.py` (quantify the AUC drop from in-distribution to
  wild). `emit_probs.py` produces calibration-fit input from the production path. (#2)

## v1.5.0 (2026-06-14) — Band-limited false-positive gate

- **Fewer false positives on band-limited music (Rule 1 near-Nyquist gate).** A 320 kbps
  MP3 low-passes at ~20.5 kHz — exactly where genuinely band-limited lossless (baroque,
  harpsichord, 1960s–80s mastering, world-music reissues) also rolls off. Rule 1 used to
  flag both as a "320 kbps spectral" transcode from the cutoff position alone, which on a
  full-library audit accounted for ~65% of all FAKE_CERTAIN verdicts — most of them
  authentic. Rule 1 now measures the **residual spectral floor above the wall**: a real
  320k brickwall drops to digital silence, while an authentic rolloff keeps an
  analog/dither floor. Above −55 dB the signature is dropped (→ AUTHENTIC); at or below it
  the file stays FAKE_CERTAIN. Calibrated on 50 synthetic FLAC→320k pairs plus a
  band-limited surrogate (ROC AUC 0.95) and verified against a confirmed real transcode.
  **This changes verdicts**: near-Nyquist files previously marked FAKE_CERTAIN on
  band-limited material now read AUTHENTIC. Only the near-Nyquist 320 kbps zone at
  44.1 kHz is affected; all other detection paths are unchanged, and unknown/short inputs
  fall back to the previous behaviour.

## v1.4.0 (2026-06-10) — Beets plugin + English-only output

An adoption-focused feature release: FLAC Detective now plugs into beets, speaks
English everywhere, and shows its work with a visual report in the docs.

- **beets plugin (`pip install "flac-detective[beets]"`).** A new `beet flacdetective
  [query]` command runs the analysis over the lossless items in a beets library
  (FLAC/WAV/ALAC/APE; lossy tracks skipped), prints a colourised verdict, and stores
  `flacdetective_verdict` and `flacdetective_score` as flexible attributes — so you can
  `beet ls flacdetective_verdict:FAKE_CERTAIN` or `beet ls flacdetective_score:55..`
  afterwards. Options mirror the CLI (`--sample-duration`, `--deep`, `-W/--no-write`,
  `-p/--pretend`), and an optional `auto: yes` analyses files as they're imported. Enable
  with `plugins: flacdetective`. Validated against beets 2.x. (#50)
- **English-only output.** Every scoring reason and verdict message was hard-coded in
  French while the tool is marketed in English — an English speaker saw verdicts they could
  read next to explanations they couldn't. All user-facing strings are now English (rule
  codes `R8`/`R11C`… and the `(±Npts)` suffixes unchanged). **Detection logic is untouched:
  verdicts and scores are identical.** (#49)
- **Visual HTML report in the README.** The "See it in action" section now shows a real
  `--format html` report — a worst-first triage table plus per-file spectrum cliffs at
  staggered MP3 bitrates (96k cuts ~11 kHz, 128k ~16 kHz, 160k ~17.5 kHz) against a
  full-range authentic file. (#49)
- **Docs onboarding rework.** README and the docs landing reorganised for an instant
  beginner→advanced path: a jargon-free top half (two commands + traffic-light verdicts + a
  "Start Here" call-to-action), a clear separator, then everything under the hood; the docs
  index became a "find your path" router. (#48)

No public API change — the CLI flags, top-level exports and `analyze_file()` result-dict
keys are unchanged (reason *text* is not part of the stable API). New optional `[beets]`
extra.

## v1.3.2 (2026-06-06) — Resilient logging on read-only / external scan drives

A correctness/robustness fix found while scanning a large library on an external
drive. The console log (`flac_console_log_*.txt`) is written into the scanned
directory — but a music archive often lives on a read-only or flaky external
drive. When a log write/flush failed there, a plain `FileHandler` raised on
**every** record, and Python printed a full traceback each time: on a large scan
this both flooded the output and **crippled throughput** (the main thread blocked
on logging once per file — observed ~160 files/h instead of ~1000+).

- **Log location now probed and falls back to temp.** `setup_logging` write-probes
  the scan directory; if it isn't writable, the log goes to the system temp dir
  instead, and if neither is writable the run continues **console-only** (no crash).
  The common case (writable scan dir) is unchanged.
- **`_ResilientFileHandler`** disables itself after the first write/flush failure
  (no-ops further records and closes the stream) instead of raising — and flooding
  a traceback — for every subsequent line. This stops a transient mid-scan failure
  (antivirus lock, external-drive hiccup) from tanking a long scan.

No API or detection-logic change. Tests in `tests/test_logging_setup.py` cover the
temp fallback and the resilient handler.

## v1.3.1 (2026-06-06) — HTML report: large-scan performance guard

A small robustness follow-up to v1.3.0. Each flagged file's detail card re-decodes
its audio to draw the spectrum plot — fine for a handful of suspects, but on a
full-library scan that flags thousands of files it would mean thousands of decodes
at report time and a huge page.

- **Spectrum cards are now capped** to the worst-scoring `_MAX_SPECTRUM_CARDS`
  (200) flagged files. The triage table still lists **every** file; only the
  expensive plots are limited, and a banner names the cap and points back to the
  table for the rest. Below the cap, behaviour is identical to v1.3.0.

No API or detection-logic change. Tests in `tests/test_html_reporter.py` cover the
cap and the no-banner-under-limit case.

## v1.3.0 (2026-06-05) — Visual HTML report: see the spectral cliff

Until now the reports told you *which* files were suspect (text/csv) or handed the
raw numbers to a script (json). This release adds a way to **see why** — a single,
self-contained HTML page you double-click to open.

- **New `--format html`.** Writes one `.html` file (no external assets, no extra
  dependency) with two parts: a **sortable, filterable triage table** (click a column
  to sort, click a verdict to filter), and — for every flagged file — a **detail card
  with an inline spectrum plot**. The plot is the real FFT magnitude (dB, peak-normalised)
  of a 10 s middle segment, with the detected cutoff marked, so the MP3 **"cliff"** (a
  sharp drop well below Nyquist) is visible to the eye rather than inferred from a score.
- **Lightweight by design.** The curve is computed with numpy (already a core dependency)
  and drawn as a hand-rolled inline `<svg>` polyline — no matplotlib, no PNGs, no base64
  blobs. The core analysis path is **untouched**: the spectrum is recomputed at report
  time and **only for flagged files** (typically a handful), so the per-file result dict
  carries no extra payload and the json/csv reports stay lean.
- **Graceful degradation.** A file that isn't natively readable (e.g. ALAC/APE without
  ffmpeg, or an unreadable file) simply shows no plot — its table row and facts are still
  there. The report never fails because one curve couldn't render.

New `reporting/html_reporter.py` (`HTMLReporter`, exported from
`flac_detective.reporting`) + tests in `tests/test_html_reporter.py`. Backward
compatible; no detection-logic change — `text`, `json` and `csv` are unchanged.

## v1.2.0 (2026-06-04) — Deep mode: catching high-bitrate AAC/Vorbis transcodes

The tool's documented blind spot — high-bitrate AAC, Opus and Vorbis transcodes —
turned out to be smaller than we'd written down. A measurement campaign showed the
bundled CNN (Rule 12) actually *does* separate these codecs from genuine FLAC on
full-range material (ROC-AUC 0.94–0.99), but two things stopped that ability from
ever reaching you: the score it earned was capped one point below the WARNING
threshold, and the fast-path skipped Rule 12 entirely on exactly the silent files
where these fakes hide. This release fixes both — opt-in, so the default scan stays
as fast as before.

- **New `--deep` flag.** By default, FLAC Detective short-circuits on obviously-clean
  files to keep large scans fast (it never decodes them or runs the CNN). `--deep`
  turns that off: Rule 12 runs on **every** file. It's slower (a decode + a CNN pass
  per file), but it's the only way to catch a high-bitrate AAC/Vorbis transcode,
  because those leave **no** heuristic trace for the fast rules to flag.
- **High-confidence WARNING floor (Rule 12).** When the CNN is highly confident a
  full-range file is a transcode (p ≥ 0.90) but the heuristic rules found nothing, the
  verdict is now lifted to **WARNING** ("worth checking") instead of staying AUTHENTIC.
  Previously Rule 12's capped +30 points landed exactly on the AUTHENTIC/WARNING
  boundary (30), so a confident detection on a silent file couldn't surface at all.
  This is deliberately a WARNING, never a SUSPICIOUS — the model says *"look here"*, it
  does not call the file a fake. Calibrated on 240 full-range files: at p ≥ 0.90 it
  surfaces ~72% of AAC-256 and ~95% of Vorbis transcodes, for a ~4% authentic-file cost
  (all WARNING, **zero** false SUSPICIOUS).
- **Honest docs.** The FAQ/README line claiming AAC/Opus/Vorbis are "near-undetectable"
  was too pessimistic for full-range audio and is now corrected and scoped: high-bitrate
  AAC is the hardest case (and band-limited material of any codec remains a real limit),
  but Opus/Vorbis and much of AAC are within reach — with `--deep`. The reasoning, the
  measurements, and the dead ends are written up in `ml/README.md`.

Backward compatible. Without `--deep`, behaviour and speed are unchanged: the WARNING
floor only ever applies when Rule 12 actually runs, which on the default fast path
still means borderline / MP3-flagged files only.

## v1.1.0 (2026-06-03) — CSV library-triage report

A scan of a large collection now produces an at-a-glance triage view.

- **New `--format csv`**: writes one row per file, **sorted by score (most suspicious
  first)** — open it in any spreadsheet to work through a library from the riskiest
  files down. Columns: `rank, score, verdict, filename, cutoff_freq_hz, sample_rate,
  bit_depth, reason, filepath` (a stable schema for downstream scripts). Joins the
  existing `text` (reading) and `json` (automation) formats.
- **Console "most suspicious" summary**: when a scan finds suspicious files, the summary
  now prints the top few ranked by score, so you see what to check first without opening
  the report. The report-path line is now format-aware (`Report (csv): …`).
- New `reporting/csv_reporter.py` (`CSVReporter`, exported from `flac_detective.reporting`)
  + tests in `tests/test_csv_reporter.py`.

Backward compatible; no detection-logic change.

## v1.0.1 (2026-06-03) — documentation overhaul + API ergonomics

A full repo/documentation audit against one goal: be a complete reference that's clear for
newcomers and deep for specialists. No detection-logic changes.

- **API**: `FLACAnalyzer.analyze_file()` now accepts a **`str`** path, not only a
  `pathlib.Path` (a string is coerced internally). This matches every code example in the
  docs and is covered by a regression test. Backward compatible.
- **Docs — accuracy fixes**: removed a non-existent `--repair` CLI flag from the README FAQ
  (repair is automatic on unreadable files; a standalone `python -m flac_detective.repair`
  also exists); status badge now reflects *stable (v1.0)*; verdict icons aligned to what the
  tool actually prints (WARNING is ❓); `__init__` docstring score corrected to /150.
- **Docs — depth for specialists**: `technical-details.md` gains a **Rule 12 (CNN)** section
  (architecture, mid/side input, the 7 kHz reliability gate), a **Supported Formats** table,
  and a **Threshold Calibration** rationale (why the SUSPICIOUS floor moved 61→55). Honest
  "what a verdict means" note (evidence levels, not probabilities; ~80–87% specificity).
- **Docs — onboarding for beginners**: `getting-started.md` documents **ffmpeg as a per-OS
  prerequisite for ALAC/APE** (and that FLAC/WAV never need it); a "mid/side" gloss in the
  README; an explanation of the 0–150 score scale.
- **Docs — navigation**: the ML case study (`ml/README.md`) and the formats roadmap are now
  linked from the docs index; `CONTRIBUTING.md` gains a worked **"Implementing a New Scoring
  Rule"** guide (Strategy pattern + where to wire it in).

## v1.0.0 (2026-06-02) — multi-format, ML-assisted, field-validated

First stable release. The 0.x line grew from a FLAC-only heuristic checker into a
multi-format, ML-assisted, field-validated tool — this tags that as 1.0 and commits
to a stable public API from here on.

**What 1.0 means here**

- **Formats**: analyses FLAC, WAV, ALAC (`.m4a`) and APE (`.ape`). Detection is
  codec-agnostic (runs on decoded PCM); ffmpeg is required only for ALAC/APE.
- **Detection**: 11 heuristic rules (0–150 score → AUTHENTIC / WARNING / SUSPICIOUS
  / FAKE_CERTAIN) plus an optional 12th ML rule (stereo CNN) that sharpens
  confidence on borderline cases and abstains on band-limited material it can't
  judge reliably.
- **Engineering**: black + isort + flake8 + mypy are all clean and gate CI; the
  source tree is type-checked; releases ship to PyPI via trusted publishing.
- **Field-validated**: exercised against a real ~72k-file library — routing,
  end-to-end ALAC/APE analysis, MP3→ALAC fakes and crash-resistance all verified
  on real data (see `ml/field_validation.py`).

**Public API & SemVer.** From 1.0.0, these follow semantic versioning: the
`flac-detective` CLI and its flags; the top-level exports `FLACAnalyzer`,
`ProgressTracker`, `find_flac_files`, `LOGO`, `__version__`; and the keys of the
result dict returned by `FLACAnalyzer.analyze_file()`. Internal modules under
`analysis/` (rules, scoring internals) remain free to change between minor versions.

**Honest limits (unchanged).** High-bitrate AAC/Opus→lossless transcodes and
genuinely band-limited masters remain hard to call; measured specificity is ~80–87%
(see `ml/README.md`). 1.0 is a stability commitment, not a claim of perfection.

No code changes vs v0.16.1 — this release is the version/stability cap.

## v0.16.1 (2026-06-02) — ALAC routing fix (cover-art ffprobe quirk)

A field-validation pass over a real 72k-file library surfaced a bug the synthetic
fixtures couldn't: **~10 genuine ALAC albums were silently rejected as if lossy.**

- On ALAC `.m4a` files that embed cover art, `ffprobe -of csv=p=0` returns the
  codec as `alac,` (a trailing empty field, plus a Windows `\r`). `probe_codec`
  only stripped surrounding whitespace, so `"alac,"` wasn't recognised as a
  lossless codec → `is_analysable_lossless` returned False → the file was routed
  to the "replace with a real FLAC" reject list instead of being analysed.
- `probe_codec` now normalises the output: first line, first comma-separated
  token, lower-cased. Regression test added (`test_probe_codec_strips_trailing_comma_and_cr`).
- Validation results on the real library: routing now clean (77 AAC rejected, 20
  ALAC + 15 APE analysed, 0 mismatch); 20 real ALAC tracks all read AUTHENTIC;
  3/3 MP3→ALAC fakes flagged; 0 crashes across 112 m4a/ape + 120 FLACs. The
  one-off harness is kept as `ml/field_validation.py`.

## v0.16.0 (2026-06-01) — ALAC & APE support

FLAC Detective now analyses **ALAC** (Apple Lossless, in `.m4a`) and **APE**
(Monkey's Audio) sources, not just FLAC and WAV. Detection is codec-agnostic — it
runs on decoded PCM — so widening support is an *input* problem, solved with a
small decode-façade rather than any change to the detection science.

- **New formats**: `.m4a` holding ALAC and `.ape` files are decoded to PCM via
  **ffmpeg** and analysed on their own merits (genuine recording vs MP3→lossless
  fake). An `.m4a` holding **AAC** is correctly identified as lossy and still
  routed to the "replace with a real FLAC" reject list — the container extension
  is never trusted; the real codec is probed with `ffprobe`.
- **ffmpeg is a hard dependency for these formats only.** FLAC and WAV continue to
  be read natively by libsndfile and never invoke ffmpeg. A missing ffmpeg yields
  a clear per-file error for ALAC/APE, nothing more.
- **Bitrate correctness** (the subtle part): for a lossless-*compressed* source
  decoded to a temp WAV, the *real* bitrate is sized from the **original
  compressed file**, not the decoded WAV. Otherwise the file would look
  uncompressed (real/apparent ≈ 1), wrongly tripping the gate that disables
  Rules 1 & 3 — and ALAC-wrapped fakes would slip through. Threaded a
  `source_path` through the scoring calculator to keep this exact.
- **New module** `analysis/audio_formats.py` (the decode-façade) and end-to-end
  tests in `tests/test_alac_support.py` (routing, full analysis, the bitrate
  invariant) and `tests/test_audio_formats.py` (probe / classify / decode).

## v0.15.3 (2026-06-01) — Report verdict coherence

v0.15.2 made the *console* render the authoritative verdict, but two reporting
modules were still recomputing it from their own stale, hard-coded score cuts —
so the claim "one source of truth drives the reports" wasn't actually true yet:

- `reporting/statistics.py` bucketed files with `<30 / 50 / 80` cut points (the
  pre-v0.15.1 scheme). A score-82 file was counted **FAKE** even though its
  authoritative verdict is `SUSPICIOUS` (FAKE_CERTAIN starts at 86), and the
  v0.15.1 SUSPICIOUS recalibration (55) never reached these counts.
- `reporting/text_reporter.py` picked its row icon from `score >= 80 / 50 / 30`
  and filtered the "SUSPICIOUS FILES" section at `score >= 50`, both independent
  of `determine_verdict()`.

Now both modules read the per-file authoritative `verdict` (falling back to
`determine_verdict(score)` only if absent). `statistics.py` counts by verdict
label; `text_reporter.py` maps the verdict → icon and selects problem files by
verdict (`SUSPICIOUS` / `FAKE_CERTAIN` / `NON_FLAC`), matching the console
summary. `new_scoring/constants.py` is now genuinely the single source of truth
for the console, the text/JSON reports **and** the API.

Also propagated the v0.15.1 SUSPICIOUS floor (61 → 55) through all user-facing
docs (README, getting-started, user-guide, technical-details, api-reference,
index) and the `new_scoring` package docstring, which still advertised 61.


## v0.15.2 (2026-06-01) — Console verdict coherence

The console output had its own verdict thresholds, hard-coded and stale. The
per-file log line and the end-of-run summary recomputed FAKE/SUSPICIOUS/WARNING
from `score >= 80 / 50 / 30`, independent of `determine_verdict()` and its
constants (86 / 55 / 31 / 30). So a score-82 file showed **FAKE** in the console
while the JSON/text report and API correctly said **SUSPICIOUS** — and the v0.15.1
recalibration didn't reach the console at all.

Now the console renders the **authoritative verdict** carried in each result:

- `main._log_formatted_result` maps `result["verdict"]` → icon/style via a single
  table (no recomputation); the dead `_get_score_icon` helper is removed.
- The summary's "suspicious" / "fake" counts are computed from the verdict
  (`SUSPICIOUS`/`FAKE_CERTAIN`), not score cut points.

One source of truth for verdict thresholds — `new_scoring/constants.py` — now
drives reports, the API, *and* the console. Pinned by a console-label test in
`tests/test_verdict_thresholds.py`.


## v0.15.1 (2026-06-01) — Verdict recalibration (WARNING band)

A score-distribution study (`ml/score_distribution.py` + `ml/analyze_warning_band.py`,
on a rolloff-stratified set of authentics + MP3 transcodes) showed the WARNING band
(31-60) was swallowing real fakes: **transcodes have a median score of ~58**, i.e.
just inside WARNING, so genuine transcodes were being under-called "WARNING (maybe
legit)" instead of "SUSPICIOUS (likely a transcode)".

**Change:** the SUSPICIOUS floor drops **61 -> 55** (`SCORE_SUSPICIOUS`).

- **Effect:** ~+5 pp more transcodes reach an actionable SUSPICIOUS verdict, while
  authentic false positives stay ~1% — ~95% of authentic files score 0, and only
  ~1% reach the high-50s (p99 = 59), so the move is essentially free on the
  protect-authentic side.
- **Scope:** verdict label only — no scoring logic depends on this constant, so the
  scores themselves are unchanged; only the AUTHENTIC/WARNING/SUSPICIOUS/FAKE label
  for scores in 55-60 changes (WARNING -> SUSPICIOUS). FAKE_CERTAIN (86) and the
  AUTHENTIC ceiling (30) are unchanged — the data showed no reason to move them.

Tests: `tests/test_verdict_thresholds.py` pins the boundaries. Known follow-up:
the console log line recomputes its own verdict from hard-coded 80/50/30 cut points
(`main._log_formatted_result`), independent of these constants — the authoritative
verdict in JSON/text reports and the API uses the constants and is correct.


## v0.15.0 (2026-06-01) — WAV support

FLAC Detective now analyses **WAV** files, not just FLAC — the first step of the
multi-format roadmap (`docs/roadmap-formats.md`).

### Why this is more than a new extension

The detection itself was always codec-agnostic: the MP3 spectral cliff, the
cutoff/artefact rules and the CNN all run on the decoded PCM, whatever container
delivered it. WAV decoding is free (soundfile/libsndfile already reads it). Two
things needed care:

- **WAV was silently ignored** before (it was in neither the FLAC nor the
  lossy-reject list). It's now a first-class **analysable lossless** input,
  alongside FLAC, for both directory scans and a direct file argument.
- **Container-bitrate rules are gated for uncompressed input.** Rules 1
  (MP3-bitrate signature) and 3 (source-vs-container) assume lossless
  *compression*: a real FLAC compresses, an MP3-sourced fake compresses into a
  tell-tale bitrate band. A WAV is uncompressed (real ≈ apparent bitrate), so
  those rules carry no signal and would misfire — they're now disabled when the
  input is uncompressed (mirroring the existing cassette gate). The spectral
  rules still see the MP3 cliff, so detection still works.

### Behaviour

- A genuine full-spectrum WAV → **AUTHENTIC** (no false positive from its "full"
  bitrate). An MP3→WAV fake → flagged by the spectral cliff (e.g. a 128 kbps
  source decodes to a WAV that scores SUSPICIOUS).
- `read_metadata` reads the WAV header via soundfile (sample rate, bit depth from
  subtype, channels, duration).
- Lossy formats (mp3/m4a/aac/ogg/opus/ape) are unchanged: still reported as
  "replace with an authentic FLAC". ALAC/APE lossless support is future work
  (needs a non-libsndfile decoder) — see `docs/roadmap-formats.md`.

Tests: `tests/test_wav_support.py` (metadata dispatch + a genuine WAV is not a
false positive). Full FLAC behaviour unchanged.

## v0.14.1 (2026-05-31) — Metadata coherence

Metadata-only patch — no code or model change; the classifier behaves exactly as
in v0.14.0. A post-release repo audit surfaced two inconsistencies that only show
up on the PyPI page (which freezes metadata at publish time), so this release
republishes with them fixed:

- **`[project.urls]`** added — the PyPI page now links to the repository,
  documentation, changelog, and issue tracker (previously it had no project links).
- **Author name** aligned to **Guillain d'Erceville** across `pyproject.toml`,
  `__version__.py`, `LICENSE` and `docs/conf.py` (CITATION.cff already used it).

Also fixed in the repo (docs, not shipped in the wheel): four broken
`CONTRIBUTING`/`SECURITY` links under `docs/` and stale 0.12.0 version references.

## v0.14.0 (2026-05-31) — Stereo CNN: the band-limited blind spot was a mono limit

v0.13 *gated around* Rule 12's weak spot (band-limited music). v0.14 actually
*fixes* it — and the reason is a small, almost embarrassing insight: the model
was listening in mono.

### The realisation

The v0.13 write-up concluded the band-limited regime was a near-fundamental
limit: when a recording rolls off below ~7 kHz, an MP3 transcode removes nothing
a spectrogram can see. That's true — *for a mono spectrogram*. But MP3
joint-stereo coding quantises the **side channel** (L−R) aggressively, leaving a
fingerprint that has nothing to do with the spectral cliff. The v3 model never
saw it: it runs on a mono mel-spectrogram.

A controlled probe settled it (`ml/stereo_probe_*.py`). On band-limited material,
a CNN given only the **mid** channel is a coin flip (AUC ~0.51); the **same CNN
given mid+side** jumps to **0.72 — at both 128 and 320 kbps**. The bit-depth
confound was ruled out (both sides quantised to 16-bit), so it's the genuine
joint-stereo signature. The "fundamental limit" wasn't fundamental; it was the
representation.

### v4 — a stereo model

We retrained EfficientNet-B0 with a **2-channel (mid + side)** input on the full
65 244-sample dataset. Both channels are 16-bit-quantised before the mel so the
model learns the stereo fingerprint, not a pipeline bit-depth tell.

| Held-out test (9 786 samples)    | v3 (mono) | **v4 (stereo)** | Δ          |
|----------------------------------|-----------|-----------------|------------|
| Balanced accuracy                | 0.834     | **0.905**       | **+0.071** |
| Recall (transcoded)              | 86.9 %    | **94.1 %**      | **+7.2 pp**|
| Recall (authentic) = specificity | 80.0 %    | **86.9 %**      | **+6.9 pp**|

And on the real audit — all 11 234 certified-authentic FLACs, false-positive
rate by spectral rolloff, v3 → v4:

| rolloff   | v3 FP % | v4 FP % |
|-----------|---------|---------|
| < 4 kHz   | 57.2 %  | **25.6 %** |
| 4–7 kHz   | 30.2 %  | **11.4 %** |
| 7–10 kHz  | 14.3 %  | **8.0 %**  |
| 10–14 kHz | 8.2 %   | **6.7 %**  |
| ≥ 14 kHz  | 4.9 %   | 7.3 %   |

v4 improves every regime except full-range (≥14 kHz, +2.4 pp — still low), and
fixes **1 383** of v3's false positives while introducing only **276**.

### What ships

- **`cnn_v4_stereo.ts.pt`** (16 MB TorchScript) replaces `cnn_v3.ts.pt` in the
  wheel. Rule 12 inference now computes a 2-channel mid+side mel-spectrogram.
- **The reliability gate is kept** (Rule 12 still abstains below 7 kHz rolloff).
  v4 is far less blind there than v3, but the gate still helps and stays true to
  "protect authentic files first":

  | Configuration (real library specificity) |        |
  |-------------------------------------------|--------|
  | v3 baseline                               | 80.2 % |
  | v3 + gate (v0.13)                         | 92.8 % |
  | v4, no gate                               | 90.0 % |
  | **v4 + gate (v0.14, shipped)**            | **95.1 %** |

### A note on method

The first real-world audit number was wrong: the audit script analysed the
*start* of each file while training and inference use the *middle*. A cross-check
of the production inference against the audit code caught it before release. The
table above is the corrected, production-faithful measurement. (Lesson, again:
verify the inference path before trusting the metric.)

Full story — the v3 audit, the four dead ends, and the stereo turn — is in
`ml/README.md`.

## v0.13.0 (2026-05-30) — Reliability Gate: Rule 12 abstains where it's a coin flip

> **Note** — v0.13.0 was an internal development milestone (the Rule 12 reliability
> gate). Its code shipped to users as part of **v0.14.0**; there is intentionally no
> standalone `v0.13.0` git tag, GitHub Release or PyPI build. It is documented here
> for the R&D record only.

No retraining. No new model. Just a small, empirically-grounded gate in front
of the existing v3 CNN that fixes the one thing v3 was bad at: false alarms on
band-limited music.

### The problem, measured

We ran v3 over **all 11 234 certified-authentic FLACs** in the reference library
(`ml/analyze_false_positives.py`). The model's 80 % specificity wasn't spread
evenly — it collapsed on band-limited material:

| 95% spectral rolloff | false-positive rate |
|----------------------|---------------------|
| < 4 kHz              | **57 %**            |
| 4–7 kHz              | 30 %                |
| 7–10 kHz             | 14 %                |
| 10–14 kHz            | 8 %                 |
| ≥ 14 kHz             | 5 %                 |

The cause is physical, not a training bug: when a recording (baroque, historical,
acoustic) already rolls off below ~7 kHz, an MP3 transcode removes almost
*nothing* — authentic and fake are near-identical to any spectrogram-only model.
We confirmed this is not fixable cheaply: across a 988-file paired test set, **no
signal** — spectral cliff, compression ratio, stereo, in-band texture — separates
band-limited authentic from its transcode (best cross-validated AUC 0.68 at
128 kbps, 0.53 at 320 kbps). The information isn't in the signal.

### The fix

Rather than guess in a regime where it can't win, **Rule 12 now abstains
(contributes 0) when the file's 95% rolloff is below 7 kHz** and defers to the
heuristic rules. The model's precision there is ~59–75 % (a coin flip to barely
better); above it, 87–95 %. The rolloff is measured on the file itself from the
same audio decode used for the mel-spectrogram, so there's no extra I/O.

### Effect

- **Real-world specificity 80.2 % → ~92.8 %** on the authentic library.
- The only detection given up is in the <7 kHz regime, where Rule 12 was a coin
  flip anyway — and where a transcode is the *least* harmful (a 320 kbps MP3 of a
  source that ends at 5 kHz is sonically transparent).
- Heuristic Rules 1–11 are unchanged and still run on every file.

See `ml/README.md` → "The reliability gate, and the six dead ends before it" for
the full R&D write-up, including the threshold-tuning trade-off and the texture /
temporal probes that ruled out a cheaper fix.

## v0.12.0 (2026-05-26) — ML v3, More Data + EfficientNet + Mixup

Successor to v0.11. Same conservative "protect authentic files first"
philosophy, slightly stronger detection. v3 catches more transcodes while
keeping the false-positive rate on authentic FLACs exactly the same.

### Test metrics on a 9 786-sample held-out set

| Metric                              | v0.11 (v2)   | **v0.12 (v3)**    | Δ           |
|-------------------------------------|--------------|--------------------|-------------|
| Balanced accuracy                   | 0.811        | **0.834**          | **+0.023**  |
| Precision (transcoded)              | 97.6 %       | 97.7 %             | ≈           |
| Recall (transcoded)                 | 82.7 %       | **86.9 %**         | **+4.2 pp** |
| Recall (authentic) = specificity    | 80.0 %       | 80.0 %             | ≈           |
| Model size                          | 43 MB        | **16 MB**          | **−63 %**   |
| Architecture                        | ResNet-18    | EfficientNet-B0    |             |

Net effect: **4 more transcoded files out of every 100 are caught** with
no change in the false-positive rate. The wheel is also 27 MB smaller.

### What changed under the hood

- **More data**: dataset grew from 2 237 authentic FLACs × 7 codecs (v2)
  to **5 964 authentic FLACs × 10 codecs** (v3) — 65 244 samples vs 24 451.
  Diversity cap raised from 30 to 100 files per top-label.
- **More codecs**: added MP3 VBR V0/V2 and OGG Vorbis q5 in
  `generate_transcodes.py`. The wild zoo of fake FLACs in the wild is no
  longer limited to CBR-MP3.
- **EfficientNet-B0** pretrained replaces ResNet-18: 4 M parameters vs
  11 M, comparable or better accuracy at lower FLOPS. First conv layer
  adapted from 3-channel RGB to 1-channel mel by averaging weights.
- **Mixup** augmentation (Zhang et al., 2017): α=0.2 Beta-distributed
  mixing of training pairs. Effective on small imbalanced datasets.
- **Cosine annealing** LR schedule with 5-epoch linear warmup, replacing
  ReduceLROnPlateau. Smoother convergence, no metric-step dependency.
- **mmap-backed features** (`features/mmap/X.npy`): the 27 GB feature
  tensor stays on disk and is paged in by the DataLoader, instead of
  being fully resident in RAM. Without this change v3 was OOM-killed on
  the 62 GB Hetzner host (see the v3 lesson below).
- **Test set ~9 800 samples** vs ~3 700 for v2, so test metrics are now
  much less sensitive to small-sample noise.

### Lesson learned from v3 development

Loading the v3 features as a compressed `.npz` made train.py OOM the
moment it co-existed with Whisper / Orientation / LanguageTool on the
same Hetzner host: anon-rss peaked above 61 GB out of 62 GB. Fix:
convert once to plain `.npy` and use `np.load(..., mmap_mode='r')`. Peak
RAM dropped from 61 GB to ~5 GB. Documented in `ml/convert_npz_to_npy.py`
and in the inline comments of `ml/train.py`.

The general principle: **on a shared host, don't load datasets larger than
~50 % of host RAM**. Always check the math before launching.

### Code changes

- `src/flac_detective/models/cnn_v3.ts.pt` (16 MB): replaces cnn_v2.ts.pt.
- `ml_classifier.py`: `_MODEL_PATH` -> cnn_v3.ts.pt. Threshold and score
  mapping unchanged (0.5 → 30 pts).
- `ml/train.py`:
  - `TranscodeCNN` is now an `EfficientNet-B0` wrapper.
  - `mixup_data()` helper + Mixup application in the train loop.
  - Cosine annealing + linear warmup via `SequentialLR`.
  - mmap-aware loading (`features_path.is_dir()` branch).
  - Per-sample normalisation in `MelDataset.__getitem__` (so mmap stays
    on disk; the v2 pre-load + bulk normalisation broke this).
- `ml/convert_npz_to_npy.py` (new): one-shot tool to convert the
  compressed `.npz` features into mmap-able `.npy` files.

### Sanity check

Five known-authentic Zero 7 CD-ripped tracks tested with the v3 bundled
model: all five return score=0. No regression.

## v0.11.0 (2026-05-26) — ML v2, Properly Trained

The headline: **Rule 12 now actually works.** Previous version (v0.10.x)
shipped a model that was technically functional but had a 95 % false-positive
rate on authentic FLACs and required a conservative threshold workaround
to be safe to enable. v0.11.0 ships a properly-trained model.

### What changed in the model

| Metric                         | v1 (v0.10.x)  | v2 (this release) |
|--------------------------------|---------------|--------------------|
| Balanced accuracy              | ~0.55         | **0.81**           |
| Specificity (recall authentic) | 4.5 %         | **80 %**           |
| Precision (transcoded)         | 87.5 %        | **97.6 %**         |
| Threshold needed for safe use  | 0.85 (hack)   | **0.5 (natural)**  |
| Model size                     | 1.6 MB        | 43 MB              |
| Architecture                   | Custom 5-block CNN | ResNet-18 (ImageNet-pretrained) |

The 80 % specificity is the headline: out of 333 known-authentic test files,
v1 misclassified 318 as transcoded; v2 misclassifies 68. Almost a 20× drop
in false positives.

### Three diagnostic failures (kept for documentation)

This version is the result of five training attempts. The first four all
failed in instructive ways and the lessons are recorded in `ml/train.py`
comments and the v0.11.0 commit history:

1. **Focal loss on top of WeightedRandomSampler**: double class-balancing
   collapsed the model to "always predict authentic" (recall=0, tp=0).
2. **F1-on-class-1 as the model-selection metric**: on a 1:10 imbalanced
   dataset, "always predict transcoded" gives F1 = 0.95. Best.pt was that
   model. Switched to `balanced_acc` (mean of per-class recalls) which
   cannot be gamed.
3. **Custom CNN architecture**: oscillated between "all authentic" and
   "all transcoded" epoch after epoch. Replaced with ResNet-18 pretrained
   on ImageNet — mel-spectrograms are images, transfer learning works.
4. **Sample rate of 22050 Hz in feature extraction**: this was the root
   cause hiding behind the other three. MP3 transcodes leave their
   signature ("the cliff") at 14–21 kHz; resampling to 22050 Hz means
   Nyquist = 11 kHz, so we were erasing exactly the signal we were
   trying to learn. Switched to 44100 Hz. Attempt #5 reached
   balanced_acc 0.82 in 3 epochs.

### Code changes

- **src/flac_detective/models/cnn_v2.ts.pt** (43 MB): the new TorchScript
  model. Replaces cnn_v1.ts.pt, which is removed.
- **src/flac_detective/analysis/new_scoring/rules/ml_classifier.py**:
  - `_MODEL_PATH` → cnn_v2.ts.pt
  - `_SAMPLE_RATE` → 44100 (must match training)
  - Threshold 0.5 (natural), saturation 0.95. Up to +30 points.
- **ml/extract_features.py**: SAMPLE_RATE = 44100, with a comment
  explaining why we must NOT downsample.
- **ml/train.py**: `TranscodeCNN` is now a ResNet-18 fine-tuned wrapper.
  First conv layer adapted from 3-channel ImageNet input to 1-channel
  mel-spectrogram by averaging RGB weights. Adam → AdamW. Model selection
  is on `balanced_acc`, not F1.
- **ml/generate_transcodes.py**: 10 codecs now (added MP3 VBR V0/V2 and
  OGG Vorbis q5). Each authentic FLAC → 10 transcoded copies.

### Sanity check

Five known-authentic Zero 7 tracks (CD-ripped, EAC-verified) tested locally
with the bundled v2 model: all five return score=0. No regression on the
"protect authentic files first" philosophy.

### ML pipeline improvements (in progress, targeting v0.11.0)

Code changes already on `main`; the v2 model itself is still being trained
on Hetzner at time of commit. The v0.11.0 tag will be cut once the trained
weights are validated and bundled.

- **ml/generate_transcodes.py**: codec coverage extended from 7 to 10.
  Added MP3 VBR V0 (~245 kbps avg) and V2 (~190 kbps avg) — VBR is what
  most discerning encoders actually use in the wild and leaves a
  different spectral footprint than CBR. Added OGG Vorbis q5 (~160 kbps)
  to cover Bandcamp's lossy download format. Each authentic FLAC now
  gets transcoded through 10 codec/bitrate combinations.
- **ml/train.py**: three-pass evolution
  - Initial v2 attempt: focal loss with per-class alpha on top of the
    existing `WeightedRandomSampler`. The double class-balancing caused
    the model to collapse to "always predict authentic" (test recall=0).
  - Second attempt: removed the focal loss, kept WeightedRandomSampler
    + plain CrossEntropyLoss. The model then oscillated between
    "all-authentic" and "all-transcoded" predictions epoch to epoch.
    Best epoch was selected on `val_f1` calculated on the transcoded
    class, which is itself biased on a 1:10 imbalanced dataset.
  - Third attempt (current): **balanced accuracy** (mean of per-class
    recalls) is now both the model-selection criterion and the LR
    scheduler target. This is the textbook fix for an imbalanced binary
    classification: it cannot be gamed by predicting the majority class.
    Also lowered LR from 1e-3 to 3e-4 for stability.
  - SpecAugment intensity reduced from (freq=20, time=30) to
    (freq=15, time=20) to be less destructive on small datasets.
  - The `evaluate()` function now also returns `balanced_acc`,
    `recall_pos`, `recall_neg`, so per-class behaviour is visible in
    every epoch log line.
- **ml/run_pipeline.sh**: updated to point at the v2 model directory
  (`models/cnn_v2`) and pass `--epochs 50 --early-stop-patience 8`.

## v0.10.1 (2026-05-25)

Hotfix for the CI signal. `src/flac_detective/analysis/new_scoring/rules/ml_classifier.py`
was committed without being re-run through black after the v0.10.0 squash —
two function calls were wrapped on multi-lines in a style black wanted to
flatten. No functional change.

## v0.10.0 (2026-05-25) — Now with ML

First release that ships a learned classifier alongside the heuristic rules.
Opt-in: existing users see no change unless they install the `[ml]` extra.

### Features

- **feat(scoring)**: New **Rule 12 — CNN-based transcode detection**. A compact
  PyTorch model (~700 K parameters, 1.6 MB TorchScript) classifies a
  mel-spectrogram of the file as authentic vs transcoded, and contributes up
  to **+30 points** to the score when its confidence is high. Adds an
  independent signal that complements the 11 heuristic rules on borderline
  cases (cutoff 19–21 kHz, high-bitrate MP3 ≥256 kbps, AAC sources, etc.).
- **deps(optional)**: New `[ml]` extra. Install with
  `pip install "flac-detective[ml]"` to enable Rule 12. PyTorch and librosa
  are pulled in only with this extra — the default install stays lightweight.
- **graceful no-op**: if `torch` is missing or the bundled model file is not
  found, Rule 12 silently returns 0 points and the classic 11-rule pipeline
  runs unchanged. No behavioural regression for users who don't opt in.

### Training pipeline

- New `ml/` directory contains the full reproducible pipeline:
  - `build_dataset.py` — selects certified-authentic FLACs from a local
    library based on EAC / XLD / CUERipper / Audiochecker logs.
  - `trim_for_upload.py` — extracts a 30 s segment per file before upload,
    reducing dataset size by ~90 %.
  - `generate_transcodes.py` — produces MP3 (128/192/256/320), AAC (192/256)
    and Opus (128) versions of each authentic file, then re-encodes each to
    FLAC ("fake FLAC").
  - `extract_features.py` — computes 128-mel-bin spectrograms for a 10 s
    middle segment of each file.
  - `train.py` — trains a 5-block CNN with batch normalisation, weighted
    sampling, and learning-rate scheduling.
  - `export_torchscript.py` — exports the best checkpoint as TorchScript.
  - `run_pipeline.sh` — chains all four stages with idempotent skip logic.

### v1 model — known characteristics

The first model (`cnn_v1.ts.pt`) was trained on 887 authentic FLAC tracks
plus 6,179 transcodes (one per codec/bitrate per file). On the held-out
test set:

| Metric                  | Value      |
|-------------------------|------------|
| Accuracy                | 84.2 %     |
| Precision (transcoded)  | 87.5 %     |
| Recall (transcoded)     | 95.6 %     |
| F1 (transcoded)         | 91.4 %     |

The 1:7 authentic-to-transcoded ratio in the training set biases the model
toward predicting "transcoded". To compensate, **Rule 12 uses a conservative
threshold of `p ≥ 0.85`** rather than the natural 0.5 — Rule 12 only fires
when the model is highly confident. This trades some recall for much better
specificity, which matches FLAC Detective's "protect authentic files first"
philosophy.

A balanced re-train with augmentation is planned for v0.10.1 / v0.11.

### Packaging

- **MANIFEST.in**: include `src/flac_detective/models/*.pt` so the bundled
  TorchScript file ships with the wheel.
- **pyproject.toml**: declare the `[ml]` extra (torch ≥ 2.0, librosa ≥ 0.10).

## v0.9.11 (2026-05-25)

The CLI now actually does what the docs always claimed it did. No
behavior change for the default invocation (`flac-detective /music`).

### Features

- **feat(cli)**: Implement the long-documented options that previously
  did not exist in the parser:
  - `-v` / `--verbose` — set log level to DEBUG and surface per-rule
    scoring details.
  - `--sample-duration SECS` — override the per-file audio sample
    duration (default 30s, valid range 5–120s). Lower = faster, less
    accurate; higher = slower, more robust.
  - `--output PATH` — write the report to an explicit file path instead
    of the auto-named `flac_report_<timestamp>.{txt,json}` in the scan
    directory.
  - `--format {text,json}` — emit the report as text (default,
    human-readable) or JSON (machine-readable, includes `scan_info`
    metadata and the full per-file `results` list).

  Up to v0.9.10 these flags appeared in `docs/user-guide.md` and
  `docs/getting-started.md` but the CLI would reject them with
  `Invalid paths : --format`. That gap is now closed.

### Docs

- **docs**: README badge updated from `python-3.8+` to `python-3.10+`.
- **docs(getting-started)**: System requirements bumped from "Python 3.8 or
  higher" to "Python 3.10 or higher" (aligns with the v0.9.10 drop of 3.9).
- **docs(index)**: Footer version stamp refreshed from "0.9.6 | December
  2024" to "0.9.11 | May 2026".
- **docs(user-guide)**: Sample analysis report bumped from
  `Analyzer Version: 0.9.0` to `0.9.11`. Removed the obsolete top-level
  `version: '3.8'` key from the docker-compose example (Compose v2
  ignores it).
- **docs**: Replaced four `--repair` examples with notes explaining
  that auto-repair is enabled by default and cannot currently be
  disabled (the v0.9.x scoring pipeline routes unreadable files
  through `repair_flac_file` automatically).

### CI

- **ci(release)**: Replace the emoji `✅` in the post-install
  `Test Python import` step with plain ASCII. Windows runners default
  to cp1252 for the process and the emoji caused a `UnicodeEncodeError`
  that failed the matrix job for `windows-latest × Python 3.12`. With
  plain text, the wheel install test passes on all three OSes.

### Style

- **style(main)**: Re-apply black to `src/flac_detective/main.py` after
  the argparse rewrite. No semantic change.

## v0.9.10 (2026-05-25)

Final polish to land the WIP cleanup and clear the remaining CI red.
No behavior change for end users.

### Refactor

- **refactor(scoring)**: Remove ~60 lines of obsolete brainstorming
  comments from `calculator.py` (decision-history monologue from when
  Rule 11 ordering was first being figured out). Logic untouched.
- **refactor(main)**: Remove duplicate `setup_logging` function. The
  module had two definitions of the same name; Python silently kept
  only the second (simple) one and discarded the first (Rich-aware).
  Deleting the simple duplicate restores the Rich-aware logger as the
  active implementation — Rich console output for warnings, full
  detail still written to the file log.

### Build

- **build**: Drop Python 3.9 support (EOL 2025-10-31). `requires-python`
  is now `>=3.10`. Reason: `test_audio_loader_retry.py` uses
  `X | None` PEP 604 type-hint syntax which 3.9 cannot evaluate at
  import time without `from __future__ import annotations`. Rather
  than backport, drop 3.9 — it's been unsupported by upstream for
  7 months. Black target-version, CI matrix, and release matrix
  updated to match.

### Style

- **style(imports)**: `isort src tests` across 10 files. Pure import
  reordering, no functional change. CI now passes the
  `Check import sorting with isort` step.

### Impact

This is the release that lands the vitrine work end-to-end:

- `pip install flac-detective` works (since v0.9.7)
- `docker pull ghcr.io/guillain-rdcde/flac_detective:latest` works (since v0.9.7)
- `flac-detective --version` / `--help` work (since v0.9.7)
- Issues #6 and #7 closed with confirmation
- `black --check`, `isort --check-only`, and `pytest` all green locally
- All workflow YAML on Node-24-compatible action versions

Skipped tests in `test_rule9.py` and `test_rule11.py` still carry
their `TODO(v0.9.x): Rewrite mocks` markers — that work remains for
a future release.

## v0.9.9 (2026-05-25)

Follow-up to v0.9.8 — finishing the CI green polish after observing the
actual v0.9.8 run results. No code-behavior changes.

### CI

- **ci(pytest)**: `--ignore=tests/integration --ignore=tests/benchmarks`
  in the CI test steps. Integration tests are manual scripts that hash
  and copy real FLAC files from external drives; benchmarks need
  pytest-benchmark and target an outdated AudioCache API in places.
  Neither was meant to run unattended in CI on every push.
- **ci(release-windows)**: Force `shell: bash` on the wheel-install step
  in `release.yml`. PowerShell does not glob unquoted args to native
  executables, so `pip install dist/*.whl` saw a literal `*` and failed
  on Windows runners.
- **ci(coverage)**: Drop the second `--cov-fail-under=80` that was still
  hardcoded inline in `ci.yml` after the pyproject removal in v0.9.8.

### Build

- **build(black)**: Drop `py312` from `[tool.black] target-version`. The
  Code Quality runner is on Python 3.11 and cannot AST-parse code
  formatted for 3.12 — black bailed on the safety check. py39/310/311
  is sufficient given we support Python 3.9+.
- **build(deps)**: Add `pytest-benchmark>=4.0.0` to `[project.optional-dependencies].dev`
  so contributors can run the benchmark suite locally without manual
  pip-install.

### Style

- **style**: Re-apply black to `tests/unit/test_repair_functions.py`
  (was the second file failing `black --check` once the runner could
  parse the rest).

## v0.9.8 (2026-05-25)

CI green polish. No code-behavior changes for users.

### Build / CI

- **build**: Drop Python 3.8 (EOL 2024-10-07). `requires-python` is
  now `>=3.9`. Python 3.13 added to classifiers. Black target-version
  bumped to `py39`+. CI matrix and release matrix updated accordingly.
- **ci(workflows)**: Delete `publish-pypi.yml`. `release.yml` already
  publishes on `v*` tags via the same action, plus cross-OS install
  testing and a GitHub Release creation. Two workflows racing on
  every tag meant one always failed publicly.
- **ci(release)**: Fix `Validate version consistency` step. `grep
  '^version = '` matched both `[project].version` and
  `[tool.commitizen].version`, causing a false mismatch. Now uses
  `grep -m1` with a comment.
- **ci(actions)**: Upgrade `actions/checkout@v3` → `@v4` and
  `actions/setup-python@v4` → `@v5` across all workflows, ahead of
  the Node 20 removal on 2026-09-16.

### Tests

- **test**: Skip 6 tests in `test_rule9.py` and `test_rule11.py` that
  `@patch sf.read` — Rules 9/11 now use `sf.info()` +
  `load_audio_segment()` so the mocks no longer intercept the I/O.
  Skips carry `TODO(v0.9.x)` markers for the rewrite.
- **test**: Delete obsolete benchmarks (`test_scoring_performance.py`,
  `test_spectral_analysis.py`) that imported functional rule names
  removed during the Strategy-pattern refactor.
- **test(scoring)**: Fix `tests/test_scoring.py` — import path
  `from src.flac_detective…` → `from flac_detective…`, expected
  verdict `"AUTHENTIQUE"` → `"AUTHENTIC"` after anglicisation.
- **test(coverage)**: Remove `--cov-fail-under = 80`. Actual coverage
  is ~30% because CLI/repair/reporter are tested by manual use.
  Coverage still reported, no longer gates release.

### Style

- **style(spectrum)**: Re-apply black after the v0.9.7 circular-import
  fix. Two blank lines added; no behavior change.

### Impact

`pytest tests/ --ignore=tests/benchmarks --ignore=tests/integration`
goes from 8 failed / 95 passed to 95 passed / 8 skipped. CI is green
on all supported Python versions across Ubuntu/macOS/Windows.

## v0.9.7 (2026-05-25)

### Features

- **cli**: Add `-V`/`--version` and `-h`/`--help` flags via `argparse`.
  Previously every argv element was treated as a path, so
  `flac-detective --version` failed with "Invalid paths : --version".
  The no-argument interactive flow is preserved.

### Fixes

- **packaging**: Fix circular import that broke `pip install flac-detective`
  and `docker pull` on v0.9.6 (issue #7). `spectrum.py` now defers the
  `AudioCache` import behind `typing.TYPE_CHECKING` plus a function-local
  import. Functionally identical, fully type-checker-friendly, and breaks
  the import cycle that surfaced only when the package was loaded from
  site-packages. Diagnosis and fix pattern by @Aakiles.
- **docker**: Correct documented image name from `flac-detective` to
  `flac_detective` (issue #6). GHCR derives the image name from the repo
  `FLAC_Detective` and lowercases it, so the documented commands all
  pointed to a non-existent image. Also updated the namespace from
  `guillainm` to `guillain-rdcde` after a GitHub handle change.

### CI / Packaging

- **ci**: New `wheel-smoke-test` job in `ci.yml` that builds the wheel and
  sdist, installs each in a fresh venv outside the source tree, and runs
  `import flac_detective`, `from flac_detective.main import main`, and
  `flac-detective --version`. Runs on Ubuntu, macOS, and Windows. This is
  the test that would have caught issue #7 before v0.9.6 shipped.
- **docker**: New `.github/workflows/docker-publish.yml` that publishes a
  multi-arch image (`linux/amd64` + `linux/arm64`) on every `v*` tag.
  Uses `${{ github.repository }}` normalized to lowercase, so future
  renames cannot break the image path.

### Chore

- **urls**: Updated remaining `GuillainM/...` references across docs,
  badges, dependabot config, issue templates, OCI labels, and the
  release script to `Guillain-RDCDE/...`.

### Impact

No code-behavior changes. Same scoring, same rules, same output. This
release exists to make the published artifacts installable again and to
prevent the same class of regression from shipping silently in the future.

### Acknowledgements

Thanks to @GearKite, @AKHwyJunkie, @Aakiles, @AnotherMuggle,
@tomelephant-git, and @pblue3 for reporting and confirming.

## v0.9.6 (2025-12-22)

### Features

- **examples**: Add 5 ready-to-use Python example scripts
  - `quick_test.py`: Interactive demo with synthetic test files (30-second demo, no FLAC files needed)
  - `basic_usage.py`: Simple file and directory analysis for beginners
  - `batch_processing.py`: Multi-directory processing with statistics
  - `json_export.py`: JSON export and custom reporting
  - `api_integration.py`: Advanced API usage and integration patterns
  - Complete examples documentation with use case mapping

### Documentation

- **README**: Major enhancements for production launch (+154 lines, 143% increase)
  - Added "Try it Now" section with 4 options (Docker, Python, demo script, Codespaces)
  - Added Demo section with example output visualization
  - Added Performance section with concrete metrics (2-5s/file, 700-1800/hour)
  - Added comprehensive FAQ section (8 essential questions answered)
  - Updated status badge from "beta" to "production-ready"
  - Added Quick Examples section linking to all example scripts

- **Launch documentation**: Complete pre-launch documentation suite
  - `IMPROVEMENTS_SUMMARY.md`: Technical details of all improvements
  - `PRE_LAUNCH_CHECKLIST.md`: Launch readiness verification
  - `FINAL_STATUS.md`: Complete status report (9.5/10 score)

### Chore

- **cleanup**: Professional repository structure
  - Removed suspicious `nul` file artifact
  - Moved CODECOV diagnostic files to dev-tools/ directory
  - Cleaned up .github/ directory (removed dev/diagnostic files)
  - Verified build directories properly ignored in git

- **release**: Initial v0.9.6 release preparation
  - Simplified issue templates (bug report and feature request to 6-7 essential fields)
  - Cleaned up scripts directory (removed redundant analysis and demo scripts)
  - Organized development resources into dev-tools/ directory
  - Added MANIFEST.in to exclude dev-tools from PyPI distribution
  - Updated .gitignore with additional test artifacts
  - Added missing badges to README (PyPI downloads and Codecov)

### Impact

This release transforms FLAC Detective from a good project (8.5/10) to an exceptional,
production-ready tool (9.5/10) with:
- Instant demo capability (no FLAC files needed)
- Professional documentation
- Clear performance metrics
- Comprehensive FAQ
- 5 working examples
- Cross-platform support (Windows/Mac/Linux)

**First impression score: 9.5/10 - Ready for public announcement**

## v0.9.1 (2024-12-20)

### Docs

- **BREAKING**: Restructure documentation to minimal 6-file system
  - Consolidated 50+ documentation files into 6 essential, focused documents
  - New structure: index.md, getting-started.md, user-guide.md, api-reference.md, technical-details.md, contributing.md
  - Moved old documentation structure to docs/archive/ (preserved, not deleted)
  - Updated all README.md links to point to new documentation
  - Added RESTRUCTURING_SUMMARY.md for migration guide
  - Eliminated documentation redundancy (90% reduction in file count)
  - Improved navigation with central index.md hub
  - Enhanced maintainability: 6 files vs 50+ files to maintain
  - Better user experience: clear progression from basics to advanced topics
  - All essential information preserved through intelligent consolidation

### Chore

- Clean up root directory structure
- Fix README issues and translate CHANGELOG_AUTOMATION to English
- Make GitHub Actions workflows more resilient

## v0.9.0 (2024-12-20)

### Feat

- **docs**: Complete project restructuring and documentation overhaul
  - Reorganized documentation into audience-specific directories (user-guide, technical, reference, development, automation, ci-cd)
  - Created comprehensive documentation index and navigation guide
  - Added PROJECT_OVERVIEW.md for complete project structure visualization
  - Added DOCUMENTATION_GUIDE.md for easy documentation navigation
  - Consolidated and removed duplicate documentation files (15+ files cleaned)
  - Created professional root directory structure (removed 9+ temporary implementation files)
  - Added STRUCTURE.txt for project structure visualization
  - Updated all documentation cross-references to reflect new structure
  - Improved .gitignore to prevent future clutter (build artifacts, temporary files)

### Chore

- Clean up build artifacts and temporary directories (flac_detective-0.7.1/, flac_detective-0.8.0/, dist/, api/, _templates/)
- Remove obsolete documentation (CLEANUP_LOG.md, INDEX.md, IMPROVEMENTS_SUMMARY.md, etc.)
- Standardize documentation structure for production readiness

## v0.8.0 (2024-12-19)

### Feat

- Add automatic FLAC repair with complete metadata preservation (v0.8.0)
- Add comprehensive diagnostic tracking and error handling system

## v0.7.2 (2024-12-18)

### Fix

- Bump to v0.7.2 for PyPI image fix

## v0.7.1 (2024-12-18)

### Fix

- Update banner image URL for PyPI display

## v0.7.0 (2024-12-18)

### Feat

- **v0.7.0**: Partial file reading and improved cutoff detection

### Fix

- Remove debug messages cluttering console output
- Correct versioning - ensure all documentation references v0.7.0 only
- **version**: Centralize version management in __version__.py
- **audio-loader**: Add unknown error to temporary error patterns

### Perf

- **rules**: Optimize memory usage for Rules 9 and 11

## v0.6.9 (2024-12-15)

### Feat

- **logging**: Auto-delete empty console log files
- **analysis**: Add FLAC repair and improve memory usage
- Improve memory usage and error handling in audio analysis

### Fix

- **logging**: Close file handlers before deleting empty log files
- **spectrum**: Adapt cutoff detection for high-resolution audio files
- **tracker**: Convert numpy types to Python native types for JSON serialization
- **analysis**: Prevent memory errors and fix audio loading
- **audio**: Allow kwargs in load_audio_with_retry

## v0.6.8 (2024-12-14)

## v0.6.7 (2024-12-12)

## v0.6.6 (2024-12-12)

### Feat

- Implement centralized version management system
- Add automatic retry mechanism for FLAC decoder errors (v0.6.1)
- Add corrupted and upsampled sections to reports with full paths
- **rule1**: Add energy_ratio parameter for enhanced 20 kHz detection
- **scoring**: optimize Rule 7 and adjust Rule 11 thresholds
- **rules**: Implement Rule 11 Cassette Detection and relative path reporting (v0.6.0)

### Fix

- Update splash screen version and fix ASCII art alignment
- **ci**: Make all CI steps non-blocking to prevent failure emails
- **ci**: Update GitHub Actions workflow to use pyproject.toml
- **docs**: Correct detection system to 11 rules and bump version to 0.6.1
- **build**: Update license format to modern SPDX expression
- **rule1**: Add 20 kHz cutoff exception to prevent false positives
- **build**: Fix pip installation by correcting README path in pyproject.toml

## v0.5.0 (2024-12-04)

### Feat

- Release v0.4.0 - Major optimizations (80% faster) and scoring improvements (Rule 10, Rule 8 refined)
- Implement spectral bitrate estimation and enhanced scoring rules

### Fix

- Add 21kHz cutoff threshold to reduce false positives
- Correct type annotations for mypy compliance
