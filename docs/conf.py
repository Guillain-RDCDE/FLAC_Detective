# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath("../src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "FLAC Detective"
copyright = "2025–2026, Guillain d'Erceville"
author = "Guillain d'Erceville"

# Single source of truth for the version (avoids stale hard-coded numbers).
# NB: assign from the imported module rather than `import ... as release` — the
# latter reads to static analysis (CodeQL) as an unused import, since Sphinx only
# ever reads `release` as a module global and never references it in this file.
import flac_detective  # noqa: E402

release = flac_detective.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

templates_path = ["_templates"]
# README.md is the docs-folder meta-index (mirrors index.md); don't build it as a page.
# Correspondence and measurement records live in docs/ so they sit next to what
# they describe and render on GitHub, but they are not user documentation and
# have no place in the site navigation. Sphinx runs with -W, so anything not in
# a toctree fails the build unless excluded here.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "README.md",
    # Correspondence and issue drafts live here because that is where the rest of
    # the project's writing lives, but they are working artefacts, not pages of
    # the manual. Sphinx treats "not in any toctree" as an error, so anything
    # that is not documentation has to be excluded or it turns the Docs job red —
    # which is exactly what happened twice on 1 and 2 September, unnoticed for a
    # day each time.
    "reply-to-provir-*.md",
    "issue-reply-*.md",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

# Don't let three third-party websites decide whether our documentation builds.
#
# The Docs job runs sphinx with -W, so a warning is a failure. Intersphinx warns
# when it cannot fetch an inventory, which happens whenever docs.python.org,
# numpy.org or scipy.org is slow, rate-limiting the runner, or simply down — and
# on 2 September it did exactly that, turning a green build red for a reason that
# had nothing to do with this repository.
#
# A gate that fails on someone else's uptime is not testing us. Cross-project
# links degrade to plain text when an inventory is missing, which is a cosmetic
# loss in the API pages and never a wrong statement.
intersphinx_timeout = 15

# `suppress_warnings = ["intersphinx"]` does NOT work for this one, which is why
# the first attempt at this fix did nothing: the message is emitted by a bare
# `LOGGER.warning(...)` in sphinx/ext/intersphinx/_load.py with no `type=`, and
# suppress_warnings can only match warnings that carry a type. So it is filtered
# by its text, narrowly, and everything else intersphinx says still fails the
# build.


def _drop_unreachable_inventory_warning(record):
    """Let a build survive an unreachable inventory, and nothing else."""
    return "failed to reach any of the inventories" not in record.getMessage()


def setup(app):
    """Install the filter on the HANDLERS, not on the logger.

    A filter attached to a logger only sees records logged directly to it —
    records propagating up from ``sphinx.sphinx.ext.intersphinx._load`` never
    pass through it. That was the second failed attempt. Handlers do see
    propagated records, and the warnings-are-errors machinery is a handler, so
    that is where the filter has to sit.
    """
    import logging as _logging

    sphinx_logger = _logging.getLogger("sphinx")
    for handler in sphinx_logger.handlers:
        handler.addFilter(_drop_unreachable_inventory_warning)
    return {"parallel_read_safe": True, "parallel_write_safe": True}

# MyST parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# Auto-generate header anchors for h1–h3 so that `[Link](#section-name)`
# style intra-page links inside Markdown files resolve under MyST. Without
# this, every TOC built in `[Section](#section)` style emits an
# "xref_missing" warning on the Sphinx/ReadTheDocs build.
myst_heading_anchors = 3
