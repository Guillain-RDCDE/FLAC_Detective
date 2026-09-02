# Set B — our two columns, and the control that makes their null readable

2026-09-02. Written before either key moved. The hashes below are the
commitment; everything after them is explanation and cannot change them.

## The commitment

| Column | File | SHA-256 |
| --- | --- | --- |
| v1.13.6 — K1-K5 are read on this one | `ml/verdicts_setB_v1136.csv` | `376bcc89436cfeece6bd8b58c7112e0a1df580bea85498fb978a8b9051c1df91` |
| v1.13.4 — reported alongside | `ml/verdicts_setB_v1134.csv` | `7e1abf9212137718a4fb6d96199df72462192b0a56a70fe4a7e4d91e056989e3` |

Both engines were pinned before his files arrived. The second column exists
because his half is the only corpus neither party built, and therefore the only
honest place to measure what the band-limited repair actually did.

Both verdict files are CRLF and are hashed as they stand. A `.gitattributes`
entry marks them, and everything under `ml/exchange/received/`, as `-text`, so a
clone reproduces the bytes these hashes describe whatever the local line-ending
configuration. This exchange has been bitten twice by line endings already — his
`.sha256` seals the CRLF form, and his set B manifest is LF while its selfhash
file is CRLF — and a published hash that only matches on the machine that
produced it is not a commitment.

## The set as received

Zip `fd-exchange-v3-setB-2026-08-31.zip`, 2,963,597,744 bytes, sha256
`f53cc86188298ba7a2c5a8f1963b71f7a15f25f6201d4ffc84ef01f4df0ceffb`, matching the
`SHA256SUMS.txt` shipped beside it. 282 entries, all stored, none compressed.

- Manifest self-hash `b0bb5410cde39caa3ac33ecd0254275a1ff750accd3364b98d5072607946eaea`,
  identical to the value declared on 31 August. The manifest is LF and hashes as
  it stands; `MANIFEST.selfhash` carries the bare hex with CRLF. Two files, two
  line-ending rules.
- 280/280 files match on hash **and** on the declared size column. His manifest
  has three columns (hash, path, size); `run_engine_on_set.py` already read the
  third.
- One single length: every file is exactly 10,584,078 bytes — 2,646,000 samples,
  44.1 kHz / 16-bit stereo. His repair of the length leak holds.
- The WAV headers carry a `LIST/INFO` encoder string that is byte-identical on
  all 280, so it separates no class from another. Had it varied by class it
  would have leaked the answer key.

## The result

Both files: 280 rows, 280 unique ids, manifest verified at read time, 0 ERROR,
0 `NOT_ASSESSED`, longest contiguous ERROR run 0, `evidence_families` serialised
with `|` and no residual `+`. Distribution identical in both: 143 AUTHENTIC,
75 FAKE_CERTAIN, 55 WARNING, 7 SUSPICIOUS. `hires_verdict` is `NOT_HIRES` on all
280, which is expected of 44.1/16 excerpts and says nothing about that axis.

**The two columns are identical on all 280 rows, verdict for verdict.** The
independence guard (1.13.5) and `NOT_ASSESSED` (1.13.6) change nothing on his
corpus.

None of these counts are rates until the key moves.

## Why the null is reportable

A perfect zero is also the signature of a harness fault: two passes that loaded
the same engine. Three checks, the third decisive.

1. **The virtual environment carries an editable install pointing at the
   repository.** With no `PYTHONPATH`, `flac_detective` resolves to
   `…/Flac_Detective/src`. The worktree path does win when set — verified as
   1.13.4 from `C:\Users\loutr\fd-v1134\src` — but the check that settles it is
   the module's file path, never the version string, which reports whichever
   module actually loaded.
2. The two trees genuinely differ: 13 files, 308 insertions between `9199d45`
   and `HEAD` under `src/`.
3. **Positive control** (`ml/positive_control_two_columns.py`): the four
   band-limited files that the registered 1.13.5 measurement says must move come
   back **4/4 FAKE_CERTAIN under 1.13.4** and **4/4 SUSPICIOUS under 1.13.6**,
   the log printing `CONVICTION WITHHELD: score 105 but only 1 evidence family
   (cnn&spectral)`. Results in `ml/positive_control_v1134.json` and
   `ml/positive_control_v1136.json`.

Today's chain separates the two engines. The null is a measurement.

## Two traps recorded so they are not repeated

**A version number is not a provenance check.** See point 1 above: the editable
install makes it possible to run one engine twice while printing two different
version strings. Assert on the module path.

**`file` is not unique in `independence_guard_*.csv`.** The same filename recurs
in every arm, so the join key is `(file, population)`. Joining on the name alone
compares one arm against another and reports 60-69 changes where there are 4.

## One defect caught before the second column ran

The worktree's copy of `ml/run_engine_on_set.py` still joined
`evidence_families` with `+`, the bug found during the 1 September rehearsal —
and since 1.13.5 a collapsed pair is itself named `cnn&spectral`, so a
`+`-joined column cannot be read back. The two columns would have been
serialised differently and therefore not comparable. The runner was aligned on
the repository's copy before the pass; `src/` in the worktree was left untouched,
so the 1.13.4 engine is the committed one.
