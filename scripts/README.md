# Scripts

Maintainer utilities. Not shipped to PyPI (excluded by `MANIFEST.in`).

End users **do not** need to run anything here — `pip install flac-detective` gives
you the `flac-detective` CLI directly.

## Release

### `prepare_release.py`

Updates the version in `pyproject.toml`, `src/flac_detective/__version__.py`, and
`docs/conf.py`; validates that `CHANGELOG.md` has an entry for the new version;
prints the remaining manual steps (commit, tag, push).

```bash
python scripts/prepare_release.py 0.9.12
python scripts/prepare_release.py 0.9.12 --release-name "Feature Name"
```

### `bump_version.py`

Higher-level wrapper around Commitizen that automates the bump-commit-tag flow.
Requires a clean working tree.

```bash
python scripts/bump_version.py
```

After either of these, the release pipeline runs automatically on tag push:

- `release.yml` → PyPI publish + GitHub Release with checksums
- `docker-publish.yml` → multi-arch image to GHCR
- `ci.yml` → full test matrix on main

## Development

### `setup_precommit.py`

Installs and configures the pre-commit hooks defined in `.pre-commit-config.yaml`
(black, isort, flake8, mypy, bandit, plus assorted file-hygiene checks).

```bash
python scripts/setup_precommit.py
```

### `Makefile`

Standard development commands. Run `make help` for the full list. Common ones:

```bash
make install-dev       # editable install with dev extras
make install-hooks     # install pre-commit hooks
make format            # run black + isort
make lint              # run flake8
make test              # run pytest
make test-cov          # run pytest with coverage report
make clean             # remove build artifacts and caches
```

## Notes

Three legacy shims (`run_detective.py`, `run_windows.bat`, `repair_flac.py`) used
to live here as workarounds for running the tool before `pip install` made the
`flac-detective` CLI work properly. They have been removed — use the installed
CLI (`flac-detective ...`) instead.
