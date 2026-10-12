# Replies posted on issue #11

The replies on the issue, reproduced from GitHub as posted — rebuilt from
GitHub on 2026-09-21 because an earlier edit of this file had corrupted it (see
the note at the end). The reasoning and the numbers live in the CHANGELOG
(v1.14.0 to v1.16.0) and in `ml/exchange/QUALITY_SINGLE_PASS_*`. Paragraphs are
kept on one line each, as GitHub renders them.

---

## First reply, 1.14.0 (2026-09-18)

Hey, thanks for this — fair complaint, and it's fixed in 1.14.0.

You put your finger on exactly the right spot: the bar and `progress.json` only ever counted finished files, so a one-hour track was a single tick that landed when it was already over. Nothing was lying to you, there was simply nothing being said in between.

There's now `--progress-events`, which reports the stages *inside* each file, one JSON object per line. `--progress-events -` sends them to stderr, or give it a path and you get a clean file you can tail. A line looks like `{"event": "stage", "file": "...", "stage": "spectrum", "index": 3, "total": 6}`. The stages are always prepare, metadata, spectrum, quality, scoring, done — scoring is the long one, that's where the re-encode, the heavy rules and the CNN live. `done` arrives exactly once per file including files that fail, so your UI never ends up waiting on something that already went wrong. From Python it's a callback instead, same stages: `analyze_file(path, on_progress=my_func)`.

About the percentage: I left it out on purpose, and I'd rather tell you why than quietly ship a fake one. Which rules run depends on what the earlier ones found — a file that looks clean early gets out before the expensive half, `--deep` changes that, and several rules only run at certain cutoffs. So when a file is opened, the engine honestly does not know how much work is left in it. `index`/`total` is "stage 3 of 6", not a fraction of the time. A number would have looked nicer and been wrong a lot of the time, which is the problem you already have.

One practical note if you read stderr: the banner and the log are on there too, so match the lines starting with `{"event"` and ignore the rest. A file path gives you a stream with nothing else in it.

Thanks for the clear report — "my UI looks stuck" told me more than a feature request would have :)

---

## Second reply, 1.14.1 (2026-09-18)

Posted after measuring what 1.14.0 had claimed: `scoring` is not the long stage
on a long track, `quality` is. He had also asked whether the account is run by
an LLM.

Ha — human, obviously assisted by an LLM, and above all a fairly obsessive audiophile. That last part is the one that writes the rules :)

And since we're being honest: I got something wrong in that message. I told you `scoring` was the long stage. Then I measured it on your actual case, a long track, and it's `quality` — 87% of the analysis on a 20-minute file, because it's three separate passes over the audio. `scoring` only dominates on short library files. So 1.14.0 moved you from "stuck at nothing" to "stuck at stage 4 of 6", which isn't what I promised you.

1.14.1 fixes it: `quality` now reports each step as it starts (`clipping`, `dc_offset`, `silence`, `bit_depth`, `upsampling`) as a second kind of line, `"event": "substage"`. On that same 20-minute file the longest gap between two events drops from 39.3 s to 12.7 s.

If you already wrote against 1.14.0, filter `event == "stage"` and nothing changes for you — same six events, same order, same indices, same keys. I checked that against the published wheel, not just the source.

Still on my list: those three passes each read the whole file and could share one read. That would actually make long tracks faster rather than just better narrated, but it changes what the engine reads, so it needs proper measurement first.

---

## Third reply, 1.15.0 and 1.16.0 (2026-09-21)

The optimisation promised in the second reply, and the position events that
repaired what it cost.

Quick follow-up: the thing that was "still on my list" is shipped, plus one more.

**1.15.0** — those three passes now share one read of the file. Complete tracks went from 16.4 s to 7.5 s each here, with identical results: 196 files compared field by field and a full before/after on 92 files, zero verdicts moved.

**1.16.0** — that single read is one long step, and 1.15.0 briefly made the silent gap *worse* because of it. So it now tells you where it is: `{"event": "scan", "frames": ..., "frames_total": ...}`, every 5% of the audio, always ending exactly at the total. On a 20-minute track the longest silence between two events went from 39.3 s in 1.14.0 to 4.6 s now.

`pip install -U flac-detective`. If you already filter on `event`, nothing you wrote changes. Curious how it behaves in your app :)

---

*Note on this file.* Commit `825d724` rewrote it through PowerShell 5.1, whose
`Get-Content` decodes a BOM-less UTF-8 file as cp1252: every em dash became
three characters of mojibake, in the repository only — the comments on GitHub
were never affected. It is now generated from the GitHub comments themselves
and checked against them.
