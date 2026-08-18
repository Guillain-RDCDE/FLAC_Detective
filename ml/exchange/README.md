# The 2026-08 blind exchange set — committed bytes for a published hash

`MANIFEST.sha256` lists all 599 files of the FLAC Detective side of the blind
exchange with Provir (Jamie Dodd): SHA-256 and byte length per file, produced by
`ml/freeze_exchange_set.py` on 2026-08-15.

Self-hash of this manifest, for citing in correspondence:

```
0318d5faa24b82286f97dff346346ad2707be6c903674686daa6c7e0e8400c24
```

## Why this file is in the repository and the audio is not

The audio is ~3 GB and lives in the gitignored `Temp/` directory. Until v1.10 the
manifest lived there too — which means the hash chain for a sealed artefact had
no committed anchor at all. Any cleanup of `Temp/` would have destroyed the only
authoritative copy of what was sealed, and there would have been no way to prove
after the fact what the published hashes referred to.

That gap was not hypothetical. Jamie hit the same one from the other side on
2026-08-17: his arm-2 spec no longer matched the hash he had published, because a
project-wide rename (VerifID -> Provir) had rewritten a path inside it along with
376 other files. He recovered the sealed bytes only because LinkedIn had retained
his own sent attachment. His conclusion, which applies here word for word:

> Publishing a hash is worth nothing if you don't commit the bytes in the same
> action.

And the failure mode behind it:

> A bulk rename is a content edit to every sealed document it touches.

## Verifying

Re-verified in full on 2026-08-17 against the frozen audio: **599 files checked,
0 missing, 0 divergent.**

```bash
cd Temp && sha256sum -c ../ml/exchange/MANIFEST.sha256
```

## What is deliberately absent

The answer key (`fd-exchange-2026-08-LABELS.json`, which maps each file id to its
codec arm) is **not** in this repository and must never be. It is covered by the
`*-LABELS.json` rule in `.gitignore`. A blind exchange stops being blind the
moment the key is published, and the manifest is exactly the artefact that lets
the other side verify integrity *without* it.


## Known defect: 599 rows, 589 distinct files

Disclosed 2026-08-18, found by Jamie Dodd by sorting this manifest.

Ten digests appear twice. They are not ten scattered accidents: they are **one
entire source group** — the genuine file and all nine of its transcodes —
present twice under two sets of ids.

```
0104 == 0219   0178 == 0295   0179 == 0305   0190 == 0494   0202 == 0408
0270 == 0303   0293 == 0573   0365 == 0491   0478 == 0547   0562 == 0577
```

**Cause.** Two Internet Archive items hold the same taper's same track — one
named `…-matrix-…`, the other `…-matrix2-…`. The corpus dedup keyed on the item
identifier, so both passed as independent recordings. Clustering by content gives
57 groups of ten, one of nine, and one of twenty; the set is 59 source recordings,
not 60.

**Consequences, both mild and both real.** Per-arm denominators read 60 when one
recording is counted twice in every arm, genuine included — the corrected rates
are in `CHANGELOG.md` and `ml/README.md`, and nothing material moved. And the
repeated hashes are a leak in themselves: sorting this file reveals that those
twenty ids carry only ten distinct labels, without touching the audio.

**Why it is not re-frozen.** Verdicts have already been exchanged against these
exact ids. Re-freezing would invalidate a comparison that is already made, so the
set stays as shipped and the defect is published instead.

**The fix, at the level of the class.** `ml/freeze_exchange_set.py` had already
*computed* every digest — it writes them here — and never compared them to each
other. It ran a careful check for metadata tags, which looks outward at what might
leak, and no check at all on what it had just produced. `audit_own_output()` now
refuses to ship a set whose digests repeat, and warns when a source contributes
fewer arms than its peers. `tests/test_exchange_set_integrity.py` pins the shipped
counts so this defect cannot be quietly widened.
