# FLAC Detective Documentation

FLAC Detective is a command-line tool that detects **fake lossless** audio files — MP3s
(and other lossy codecs) re-saved as FLAC, ALAC, APE or WAV so they *look* lossless when
the quality was already thrown away. It scores each file with a multi-rule engine
(plus an optional 12th CNN rule) and gives a clear, four-level verdict, while protecting
genuine vinyl rips, cassette transfers and quiet recordings from false alarms.

```{toctree}
:maxdepth: 2
:hidden:

start-here
getting-started
user-guide
api-reference
technical-details
band-limited-stratum
roadmap-formats
```

---

## 👉 Find your path

Pick the row that sounds like you — each leads straight to the right page.

| If you are… | Start with | You'll get |
|---|---|---|
| 🟢 **New to all this** — just want to check your music | **[Start Here](start-here.md)** | A 5-minute, jargon-free walkthrough: what it does, install, scan, read results. *No command-line experience needed.* |
| 🎧 **A user** ready to scan a real library | **[Getting Started](getting-started.md)** → **[User Guide](user-guide.md)** | Install options (ffmpeg, Docker, ML extra), every flag, real examples, `--deep`, CSV/HTML reports. |
| 🐍 **A developer** integrating it in Python | **[API Reference](api-reference.md)** | The public API, the result dict, and integration examples. |
| 🔬 **Curious how it works** under the hood | **[Technical Details](technical-details.md)** | Every rule, the three evidence families, the corroboration gate, the protection layers. |
| 🧪 **Here for the deep dives** | **[ML case study](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md)** · **[Formats roadmap](roadmap-formats.md)** | How Rule 12's CNN was built (the false-positive audit, the dead-ends, the mono→stereo breakthrough), and why multi-format support is an *input* problem. |

> **New here and not sure?** Start with **[Start Here](start-here.md)** — it's enough for
> day-to-day use, and it points onward when you want more.

---

## The 30-second version

```bash
pip install flac-detective       # needs Python 3.10+
flac-detective /path/to/music    # scan a file or a whole folder
```

Every file comes back with one of four verdicts — read them like traffic lights:

| Verdict | Score | Meaning |
|---------|-------|---------|
| ✅ AUTHENTIC | ≤ 30 | No evidence of transcoding — keep it |
| ❓ WARNING | 31–54 | Borderline — give it a listen |
| ⚠️ SUSPICIOUS | 55–85 | Likely a transcode |
| ❌ FAKE_CERTAIN | ≥ 86 | Multiple strong indicators — replace it |

The scan **only reads** your files — it never edits, moves or deletes anything. The same
thresholds drive the console, the reports and the API.

*(Plain `pip install` won't upgrade an existing install — use `pip install --upgrade
flac-detective`. See [Getting Started → Upgrading](getting-started.md#upgrading-to-the-latest-version).)*

---

## Why a fake is detectable

To save space, an MP3 throws away the highest frequencies — a real recording keeps them,
so the *shape* of the spectrum gives a fake away (it "falls off a cliff" well below where
a real file keeps going). FLAC Detective measures that cliff plus a dozen other clues.
The full story is in **[Start Here](start-here.md)** (the gentle version) and
**[Technical Details](technical-details.md)** (every rule).

---

## Project links

- **GitHub**: <https://github.com/Guillain-RDCDE/FLAC_Detective>
- **PyPI**: <https://pypi.org/project/flac-detective/>
- **Issues**: <https://github.com/Guillain-RDCDE/FLAC_Detective/issues>
- **Discussions**: <https://github.com/Guillain-RDCDE/FLAC_Detective/discussions>
- **Contributing**: [CONTRIBUTING.md](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/CONTRIBUTING.md)
- **Security**: email guillain@poulpe.us (see [SECURITY.md](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/.github/SECURITY.md))

FLAC Detective is released under the MIT License.

---

</content>
