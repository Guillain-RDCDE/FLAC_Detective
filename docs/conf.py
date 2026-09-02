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
