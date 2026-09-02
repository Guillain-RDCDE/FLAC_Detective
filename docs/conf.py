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
    # "sphinx.ext.intersphinx" — removed 2026-09-02, see the note further down.
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

# Intersphinx is deliberately NOT enabled — see the extension list above.
#
# The Docs job runs sphinx with -W, so any warning fails the build, and
# intersphinx warns whenever it cannot fetch an inventory, which happens when
# docs.python.org, numpy.org or scipy.org is slow, rate-limiting the runner, or
# simply down. On 2 September that turned the build red for a reason that had
# nothing to do with this repository.
#
# Three narrower fixes were tried first and all three are recorded here, because
# each of them looked right:
#
# 1. `suppress_warnings = ["intersphinx"]` does nothing. The message comes from a
#    bare `LOGGER.warning(...)` in sphinx/ext/intersphinx/_load.py with no
#    `type=`, and suppress_warnings can only match a warning that carries one.
# 2. A logging filter on the "sphinx" logger does nothing either: a filter on a
#    logger only sees records logged directly to it, and this one propagates up
#    from a child logger.
# 3. A filter on that logger's HANDLERS hides the message but does not stop the
#    build failing — the warning is still counted where the filter cannot reach.
#    It passed locally only because the inventories happened to be reachable that
#    minute, which is exactly the kind of green that means nothing.
#
# So the dependency goes rather than being worked around. The loss is real and
# small: cross-project references render as plain text instead of links into the
# Python, numpy and scipy manuals. The gain is a documentation build that does
# not depend on three websites being up.

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
