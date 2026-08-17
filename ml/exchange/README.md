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
