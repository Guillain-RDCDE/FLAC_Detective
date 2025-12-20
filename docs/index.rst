FLAC Detective Documentation
============================

.. image:: https://img.shields.io/pypi/v/flac-detective.svg
   :target: https://pypi.org/project/flac-detective/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/flac-detective.svg
   :target: https://pypi.org/project/flac-detective/
   :alt: Python versions

.. image:: https://img.shields.io/github/license/guillainm/flac-detective.svg
   :target: https://github.com/guillainm/flac-detective/blob/main/LICENSE
   :alt: License

FLAC Detective is an advanced FLAC authenticity analyzer that detects MP3-to-FLAC transcodes with high precision.

Features
--------

* Advanced spectral analysis for transcode detection
* Comprehensive metadata extraction and validation
* Automatic FLAC file repair with metadata preservation
* Detailed quality scoring and reporting
* Support for batch analysis
* Rich terminal output with progress tracking

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install flac-detective

Basic Usage
~~~~~~~~~~~

Analyze a single FLAC file:

.. code-block:: bash

   flac-detective path/to/file.flac

Analyze all FLAC files in a directory:

.. code-block:: bash

   flac-detective path/to/directory

Repair corrupted FLAC files:

.. code-block:: bash

   flac-detective --repair path/to/file.flac

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   GETTING_STARTED
   EXAMPLES
   PYTHON_API_GUIDE
   TROUBLESHOOTING

.. toctree::
   :maxdepth: 2
   :caption: Technical Documentation

   ARCHITECTURE
   TECHNICAL_DOCUMENTATION
   REPORT_FORMAT
   RULES
   RULE_SPECIFICATIONS

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
   api/analysis
   api/repair
   api/reporting

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/CONTRIBUTING
   development/TESTING
   development/DEVELOPMENT_SETUP
   CODE_QUALITY_SETUP
   TYPE_HINTS

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
