<p align="center">
  <img src="docs/social-preview.jpg" width="100%" alt="FLAC Detective — lossy transcodes hiding inside lossless files: MP3, AAC, Vorbis, Opus">
</p>

# 🎵 FLAC Detective

> **A lossy file renamed to .flac looks lossless, weighs lossless, and fools every player you own. It can't fool the arithmetic the encoder left behind — and this reads it for you.**
>
> MP3, AAC, Vorbis and — partially — Opus, through three independent kinds of evidence. A conviction needs two of them to agree.

[![PyPI version](https://img.shields.io/pypi/v/flac-detective)](https://pypi.org/project/flac-detective/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/flac-detective)](https://pypi.org/project/flac-detective/)
[![CI](https://github.com/Guillain-RDCDE/FLAC_Detective/actions/workflows/ci.yml/badge.svg)](https://github.com/Guillain-RDCDE/FLAC_Detective/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://guillain-rdcde.github.io/FLAC_Detective/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Find the fake FLACs in your music library.**

A lossy codec throws away the top of the spectrum and never gives it back. FLAC Detective reads
each file, spots the fingerprints that loss leaves behind, and tells you which files are real and
which are fakes.

```bash
pip install flac-detective       # needs Python 3.10+
flac-detective /path/to/music    # scan a file or a whole folder
```

Every file gets a verdict, like a traffic light:

```
✅ AUTHENTIC      real lossless         → keep it
❓ WARNING        borderline            → give it a listen
⚠️  SUSPICIOUS     probably a transcode  → likely a fake
❌ FAKE_CERTAIN   definitely a fake     → replace it
```

The scan only **reads** your files — it never changes anything.

> 🟢 **New to all this?** → **[Start Here — the 5-minute beginner's guide](docs/start-here.md)**
> No command line, no jargon. From *"what is this?"* to *"I checked my music"*.

---

## 📚 More

- 📕 **[Reference](docs/REFERENCE.md)** — how it works, the three kinds of evidence, full usage, the ML case study
- 📖 **[Full documentation site](https://guillain-rdcde.github.io/FLAC_Detective/)** — getting started, user guide, technical details, API
- 🚀 **[Getting Started](docs/getting-started.md)** — install, first analysis, accuracy & file-safety notes
- 📋 **[Changelog](CHANGELOG.md)** · 🤝 **[Contributing](.github/CONTRIBUTING.md)** · 🔒 **[Security](.github/SECURITY.md)**
- 💬 **[Issues](https://github.com/Guillain-RDCDE/FLAC_Detective/issues)** · **[Discussions](https://github.com/Guillain-RDCDE/FLAC_Detective/discussions)**

---

Licensed under the **[MIT License](LICENSE)**.

