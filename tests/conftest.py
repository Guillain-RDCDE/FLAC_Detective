"""Test-suite wiring shared by every test module.

``src/`` is on the path through ``[tool.pytest.ini_options] pythonpath`` in
pyproject.toml. The research scripts under ``ml/`` are not a package and are
imported by a handful of tests (the exchange harness, the freeze audit, the
free-format decoder, the offset probe, the SBR arm), so their directory is put
on the path here, once, instead of in each of those files.
"""

import sys
from pathlib import Path

_ML = Path(__file__).resolve().parent.parent / "ml"
if str(_ML) not in sys.path:
    sys.path.insert(0, str(_ML))
