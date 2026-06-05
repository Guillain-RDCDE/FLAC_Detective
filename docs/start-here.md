# Start Here — a 5-minute guide for newcomers

New to FLAC, transcodes, or the command line? You're in the right place. This page
takes you from *"what is this?"* to *"I checked my music"* with no jargon and no wall of
theory. The deep technical docs are there when you want them — but you don't need any of
them to start.

---

## 1. What does this actually do?

A **FLAC** file is meant to be *lossless* — a perfect copy of the original sound, with
nothing thrown away.

The catch: anyone can take a low-quality **MP3**, re-save it as a FLAC, and now it
*looks* lossless even though the quality was thrown away long ago. It's a **fake**, and
you usually can't tell by double-clicking it.

**FLAC Detective spots those fakes for you.**

---

## 2. Why a fake is detectable (just one idea)

To save space, an MP3 **throws away the highest frequencies** — the part hardest to
hear. A real recording keeps them. So the *shape* of the sound gives a fake away:

```
   A REAL FLAC                      A FAKE (it was an MP3)
   high ^                           high ^
        | ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁                | ▁▂▃▄▅▆▇█
        | sound goes                     | ▕ <- falls off a cliff
        | all the way up                 | ▕    (the MP3 cut it here)
    low +---------------> freq       low +---------------> freq
```

That cliff is the fingerprint. FLAC Detective measures it — plus a dozen other clues —
automatically. That's the whole idea; everything else is detail.

---

## 3. Install it (one command)

You need **Python 3.10 or newer**. Then, in a terminal:

```bash
pip install flac-detective
```

That's it. *(There's an optional AI-powered rule too — `pip install "flac-detective[ml]"` —
but you don't need it to start.)*

---

## 4. Scan your music (one command)

Point it at a single file **or a whole folder** — it walks through everything inside:

```bash
flac-detective "/path/to/your/music"
```

```
   Your music folder            FLAC Detective             A verdict per file
    ♫ Album A/                                              ✅ ✅ ✅ ✅
    ♫ Album B/        ----->   [ checks each file ]  ----->  ✅ ⚠️ ✅ ❌
    ♫ Album C/                                              ✅ ✅ ✅ ✅
```

---

## 5. Read your results (a traffic light)

Every file gets **one of four verdicts** — read it like traffic lights:

```
  ✅ AUTHENTIC      Real lossless. Nothing to do — keep it.
  ❓ WARNING        Borderline. Could be fine; give it a listen.
  ⚠️  SUSPICIOUS     Probably built from a lossy file. Likely a fake.
  ❌ FAKE_CERTAIN   Several clues agree. It's a transcode — replace it.
```

```{note}
**One promise:** the scan **only reads** your files. It never edits, moves, or deletes
anything. You can safely run it across your entire collection.
```

Got a big library? Add `--format csv` for a spreadsheet, sorted worst-first so you start
with the riskiest files:

```bash
flac-detective "/path/to/music" --format csv --output report.csv
```

---

## 6. "I think I found a fake" — now what?

FLAC Detective tells you *what looks suspicious*, not *what to do about it* — that part
is your call. A sensible next step:

1. **Listen** to the track — some genuinely old or quiet recordings just look that way.
2. **Re-download or re-rip** it from a source you trust if you want a clean copy.
3. For a visual second opinion, open the file in a free tool like **Spek** and look for
   the cliff yourself.

One honest caveat: **no tool catches everything.** Very high-quality fakes, and
transcodes of naturally muffled recordings (old jazz, classical, field recordings), can
slip through. An **AUTHENTIC** verdict means *"no evidence of a transcode found"*, not an
iron-clad guarantee. *(Want it to dig harder on tricky AAC/Vorbis files? There's a
`--deep` mode — see the User Guide.)*

---

## 7. Ready for more?

You already know everything you need for day-to-day use. When you get curious about
*how* it works under the hood:

- **[Getting Started](getting-started.md)** — install options, ffmpeg, first analysis in detail.
- **[User Guide](user-guide.md)** — every flag, real-world examples, `--deep`, reports.
- **[Technical Details](technical-details.md)** — all the detection rules, explained.
- **[The ML detective story](https://github.com/Guillain-RDCDE/FLAC_Detective/blob/main/ml/README.md)** — a genuinely fun R&D read, even if you never enable the AI part.

Welcome aboard. 🎧
