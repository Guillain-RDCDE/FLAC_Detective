# FLAC Detective v0.9.7 — Patch release

A small but important patch that makes `pip install flac-detective` and `docker pull` Just Work again, and adds CI guardrails so the same class of regression cannot ship silently in the future.

This release contains **no code-behavior changes** — same scoring, same rules, same output. It restores correct packaging and installability.

---

## Fixes

### Circular import on fresh install (issue [#7](https://github.com/Guillain-RDCDE/FLAC_Detective/issues/7))

`pip install flac-detective==0.9.6` and `docker run ghcr.io/.../flac_detective:0.9.6` both blew up on the very first command with:

```
ImportError: cannot import name 'AudioCache' from partially initialized module
'flac_detective.analysis.audio_cache' (most likely due to a circular import)
```

Root cause: `spectrum.py` imported `AudioCache` at module top level, and the new scoring pipeline transitively re-imported `spectrum` before `AudioCache` had been bound. The bug was invisible in CI because pytest exercises the editable `src/` layout, which resolves imports in a different order than a `site-packages` install.

Fixed by deferring the `AudioCache` import behind `typing.TYPE_CHECKING` and a function-local import (commit [`3966b48`](https://github.com/Guillain-RDCDE/FLAC_Detective/commit/3966b48)). Huge thanks to **@Aakiles** for nailing both the diagnosis and the fix, and to **@GearKite**, **@AKHwyJunkie**, **@AnotherMuggle**, and **@tomelephant-git** for reporting and confirming across OSes.

### Docker image name and namespace (issue [#6](https://github.com/Guillain-RDCDE/FLAC_Detective/issues/6))

Two compounding mistakes meant every documented `docker pull` command pointed to a non-existent image:

1. The image is `flac_detective` (underscore — GHCR derives it from the repo name `FLAC_Detective` and lowercases it), not `flac-detective`.
2. The GitHub handle moved from `guillainm` to `guillain-rdcde`.

Every Docker reference in `README.md`, `docs/`, and the v0.9.6 release notes now points to the correct path:

```bash
docker pull ghcr.io/guillain-rdcde/flac_detective:latest
docker run --rm -v "$(pwd)":/data ghcr.io/guillain-rdcde/flac_detective:latest /data/sample.flac
```

Thanks to **@pblue3** and **@GearKite** for the report.

---

## Packaging & CI

### New: multi-arch Docker publish workflow

`.github/workflows/docker-publish.yml` builds the image on every `v*` tag (and on manual dispatch) for both `linux/amd64` and `linux/arm64` — so Apple Silicon and Raspberry Pi users get a native image with no extra effort. The workflow uses `${{ github.repository }}` normalized to lowercase, so any future repo rename can't break the image path the same way it did this time.

### New: wheel/sdist install smoke test in CI

A new `wheel-smoke-test` job in `.github/workflows/ci.yml` builds the wheel and sdist, installs each into a fresh venv **outside** the source tree, and then runs:

- `python -c "import flac_detective"`
- `python -c "from flac_detective.main import main"`
- `flac-detective --version`

Runs on Ubuntu, macOS, and Windows. This is the test that would have caught issue #7 before publishing v0.9.6, and it now runs on every PR and push to `main`.

### URL hygiene

All remaining `GuillainM/...` references across docs, badges, dependabot config, issue templates, and the release script were updated to `Guillain-RDCDE/...`.

---

## Upgrade

```bash
pip install --upgrade flac-detective
# or
docker pull ghcr.io/guillain-rdcde/flac_detective:latest
```

No migration steps. No config changes. No breaking changes.

---

## Contributors

Thanks to everyone who reported, diagnosed, and confirmed: **@GearKite**, **@AKHwyJunkie**, **@Aakiles**, **@AnotherMuggle**, **@tomelephant-git**, and **@pblue3**. First community issues, handled (very late) with care.
