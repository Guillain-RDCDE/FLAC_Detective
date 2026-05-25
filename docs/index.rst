FLAC Detective Documentation
============================

.. image:: https://img.shields.io/pypi/v/flac-detective.svg
   :target: https://pypi.org/project/flac-detective/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/flac-detective.svg
   :target: https://pypi.org/project/flac-detective/
   :alt: Python versions

.. image:: https://img.shields.io/github/license/Guillain-RDCDE/FLAC_Detective.svg
   :target: https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/LICENSE
   :alt: License

FLAC Detective is an advanced FLAC authenticity analyzer that detects MP3-to-FLAC
transcodes with high precision. Eleven scoring rules, four verdict levels, multi-arch
Docker image, and a CLI that does what the docs say it does.

Features
--------

* Advanced spectral analysis (FFT-based) with cutoff detection and segment consistency
* Eleven scoring rules with protection layers for vinyl, cassette, and high-bitrate MP3
* Automatic FLAC file repair (enabled by default — no flag needed)
* Text and JSON report output
* Rich terminal output with progress tracking
* Batch analysis across directories with progress save/resume
* Multi-arch Docker image (linux/amd64 + linux/arm64)

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install flac-detective

Or via Docker:

.. code-block:: bash

   docker pull ghcr.io/guillain-rdcde/flac_detective:latest

Basic Usage
~~~~~~~~~~~

Analyze a single FLAC file:

.. code-block:: bash

   flac-detective path/to/file.flac

Analyze all FLAC files in a directory:

.. code-block:: bash

   flac-detective path/to/directory

Interactive mode (prompts you for paths, accepts drag-and-drop):

.. code-block:: bash

   flac-detective

CLI Options
~~~~~~~~~~~

.. code-block:: text

   -h, --help                Show help message
   -V, --version             Show version
   -v, --verbose             Verbose output (DEBUG log level)
   --sample-duration SECS    Audio sample duration in seconds (default: 30, range 5–120)
   --output PATH             Path to write the report file
   --format {text,json}      Report format (default: text)

Example: write a JSON report from a 60-second sample with verbose logging:

.. code-block:: bash

   flac-detective --verbose --sample-duration 60 --format json --output report.json /music

Auto-repair of corrupted FLAC files is enabled by default — no flag is needed.

Documentation
-------------

.. toctree::
   :maxdepth: 2

   index
   getting-started
   user-guide
   api-reference
   technical-details

External Resources
------------------

* `GitHub repository <https://github.com/Guillain-RDCDE/FLAC_Detective>`_
* `PyPI package <https://pypi.org/project/flac-detective/>`_
* `Container registry <https://github.com/Guillain-RDCDE/FLAC_Detective/pkgs/container/flac_detective>`_
* `Issue tracker <https://github.com/Guillain-RDCDE/FLAC_Detective/issues>`_
* `Contributing guide <https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/CONTRIBUTING.md>`_

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
