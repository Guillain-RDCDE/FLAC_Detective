# Shape D — the absence coerced where it is CONSUMED. Registered before the repair

Written and committed **before any of the six sites is touched and before the
measurement runs**. Same discipline as R11D: criteria fixed while the answer is
unknown.

---

## Where this shape came from

Provir, 2026-08-30. He ran our shape C against his own tree, found one latent
instance, hardened it — and then **re-ran the check afterwards instead of
assuming the fix had worked**. It had not. One module downstream, the consumer
read the now-correct `None` like this:

```python
value = float(row.get(name) or 0.0)
```

`or 0.0` coerces a correctly-returned absence straight back into a reading. **The
defect survived its own repair**, in code that never mentions the statistic by
name.

Our three shapes all inspect the site where an absence is **created**. This one
is at the site where it is **consumed**, and the two sites are in different
files — an AST pass over the producer's module returns clean. His detection
rule, adopted verbatim:

> a call to `float()` / `int()` / a numeric comparison, whose argument is
> `X or <literal>` or `X if X else <literal>`, where `X` can be `None`

Deliberately **not** name-driven: his instance has no measurement identifier in
it at all, because the quantity is fetched by key. That is exactly why every
name-driven filter — ours included — returned clean.

## What it found here: 6 instances, 153 modules

Implemented, control extended to 8 must-fire lines and 9 must-not-fire lines,
0 false positives. Findings:

| site | line | what the coercion does |
|---|---|---|
| `analysis/analyzer.py` | 153, 157 | `int(metadata.get("sample_rate", 0) or 0)` and the same for `bit_depth` — feeds `classify_hires`, i.e. **a published verdict axis** |
| `gui/main_window.py` | 478 | `int(r.get("score", 0) or 0)` — a missing score displays as **0, the most reassuring value there is** |
| `ml/wild_audit.py` | 230 | `float(r["Rule13MDCTAlignment"] or 0) != 0` — merges "the rule did not run" with "the rule scored 0" |
| `ml/rule_audit.py`, `ml/wild_audit.py` | 138, 119 | `round(float(... or 0.0), 1)` — an absence enters a column that is later averaged |

**The analyzer pair is reachable, and that is the finding.** `read_metadata`
returns `{}` on any exception — an unreadable or corrupt header yields no
`sample_rate` at all — and the coercion then hands `classify_hires` a rate of
**0 Hz**, which reads `is_high_rate = False`, `is_high_depth = False` and returns
`NOT_HIRES` with no reason attached. A file whose header could not be read is
told, with confidence, that the hi-res axis does not apply to it.

## The repair

1. `sr_int` / `depth_int` become `Optional[int]`, `None` when the key is absent
   or unparseable. The bare `except: … = 0` goes with them.
2. `classify_hires` accepts `Optional[int]` and, when either is unknown, returns
   `NOT_HIRES` **with an explicit reason naming the absence** rather than
   silently. The label vocabulary does **not** change: reports, the CSV writer
   and the exchange format all consume these labels, and inventing an
   `UNKNOWN_HIRES` would be a second change riding on the first.
3. The four report/GUI sites take `is None` tests. A missing score is not 0.

## Criteria, registered before the measurement

| # | criterion | bound |
|---|---|---|
| **D1** | files on the two measurement corpora (590 + 160) where `read_metadata` returns no `sample_rate` or no `bit_depth` | **reported, not bounded** — this is the size of the reachable population |
| **D2** | `hires_verdict` values that change on those corpora | **0** if D1 is 0; if D1 > 0, every change must be a file in the D1 set and nothing else |
| **D3** | any other verdict field that changes | **0**, no tolerance — this repair may not touch the transcode axis |
| **D4** | the audit, after the repair | **0 findings across all shapes**, control still 8/8 with 0 false positives |

If D1 comes back 0 the repair is **latent**, exactly as Provir's was, and the
honest report is that no published number of ours is affected. That is the
boring answer and it is the one worth giving if it is true.

Results appended below, dated after the fact.

---

# RESULTS — appended 2026-08-31, criteria unedited above

| # | bound | measured | |
|---|---|---|---|
| D1 files with no `sample_rate` / no `bit_depth` | reported | **0 of 750** (590 exchange + 80 genuine + 80 mp3_320); `read_metadata` returned `{}` on none of them | — |
| D2 `hires_verdict` changes | 0 if D1 is 0 | **0** | held |
| D3 any other verdict field changes | 0 | **0** — verdict and score identical on every file | held |
| D4 audit after the repair | 0 findings, control 8/8 | **153 modules, 0 findings**, control 8 of 8 lines with 0 false positives | held |

D2 and D3 were measured the way R11D was: a pristine worktree at the previous
commit against the repaired tree, same 20 files (12 drawn deterministically from
the v2 exchange set plus 4 genuine and 4 from set A), full engine, `deep=True`.
Every field identical — verdict, score, hi-res verdict, hi-res reason.

**So our instance is latent, exactly as Provir's was.** No published number of
ours is affected. That is the boring answer, and it is the true one; the
alternative was to leave a path that hands a confident `NOT_HIRES` to a file
whose header could not be read.

## What shipped

* `analyzer._optional_int()` — `None`, never `0`, for an absent or unparseable
  header field. The two bare `except: … = 0` blocks are gone with it.
* `classify_hires()` takes `Optional[int]` and returns **`UNKNOWN`** with a
  reason naming which field is missing. **This deviates from the registered
  repair**, which said `NOT_HIRES` with a reason, on the stated ground that the
  label vocabulary must not grow. It does not grow: `UNKNOWN` was already there,
  and the registration was written without checking the module's own label list
  first — a small piece of carelessness, recorded rather than smoothed over. `UNKNOWN` is not a new label: it has
  meant "analysis unavailable" since the module was written, and `gui/worker.py`
  already emits it on its own failure path, so no consumer meets a value it has
  not seen.
* `gui/main_window.py` shows an em dash for a missing score instead of `0` —
  which is `AUTHENTIC`, the most reassuring value in the table.
* `ml/rule_audit.py` and `ml/wild_audit.py` write an **empty cell** for an
  unmeasured cutoff rather than `0.0`, because that column is averaged
  downstream and a fabricated zero moves a mean silently.
* `ml/wild_audit.py` no longer coerces a missing Rule 13 score to `0` one line
  after the code that exists to keep "did not run" and "scored 0" apart.

Four tests pin the new contract, including one that pins the *other* direction:
a file genuinely claiming 0 Hz still reads `NOT_HIRES`, because 0 and absent must
not become synonyms in the repair.
