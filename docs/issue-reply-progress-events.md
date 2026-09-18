# Reply for issue #11

Written 2026-09-18, for 1.14.0. The feature and the reasoning are in the
CHANGELOG (v1.14.0) and in the user guide; this is the short version the
reporter gets. Paragraphs are kept on one line each, as GitHub renders them.

---

Hey, thanks for this â€” fair complaint, and it's fixed in 1.14.0.

You put your finger on exactly the right spot: the bar and `progress.json` only ever counted finished files, so a one-hour track was a single tick that landed when it was already over. Nothing was lying to you, there was simply nothing being said in between.

There's now `--progress-events`, which reports the stages *inside* each file, one JSON object per line. `--progress-events -` sends them to stderr, or give it a path and you get a clean file you can tail. A line looks like `{"event": "stage", "file": "...", "stage": "spectrum", "index": 3, "total": 6}`. The stages are always prepare, metadata, spectrum, quality, scoring, done â€” scoring is the long one, that's where the re-encode, the heavy rules and the CNN live. `done` arrives exactly once per file including files that fail, so your UI never ends up waiting on something that already went wrong. From Python it's a callback instead, same stages: `analyze_file(path, on_progress=my_func)`.

About the percentage: I left it out on purpose, and I'd rather tell you why than quietly ship a fake one. Which rules run depends on what the earlier ones found â€” a file that looks clean early gets out before the expensive half, `--deep` changes that, and several rules only run at certain cutoffs. So when a file is opened, the engine honestly does not know how much work is left in it. `index`/`total` is "stage 3 of 6", not a fraction of the time. A number would have looked nicer and been wrong a lot of the time, which is the problem you already have.

One practical note if you read stderr: the banner and the log are on there too, so match the lines starting with `{"event"` and ignore the rest. A file path gives you a stream with nothing else in it.

Thanks for the clear report â€” "my UI looks stuck" told me more than a feature request would have :)

---

## Second reply, 1.14.1 (2026-09-18)

Posted after measuring what 1.14.0 had claimed: `scoring` is not the long
stage on a long track, `quality` is. He had also asked whether the account is
run by an LLM.

---

Ha â€” human, obviously assisted by an LLM, and above all a fairly obsessive audiophile. That last part is the one that writes the rules :)

And since we're being honest: I got something wrong in that message. I told you `scoring` was the long stage. Then I measured it on your actual case, a long track, and it's `quality` â€” 87% of the analysis on a 20-minute file, because it's three separate passes over the audio. `scoring` only dominates on short library files. So 1.14.0 moved you from "stuck at nothing" to "stuck at stage 4 of 6", which isn't what I promised you.

1.14.1 fixes it: `quality` now reports each step as it starts (`clipping`, `dc_offset`, `silence`, `bit_depth`, `upsampling`) as a second kind of line, `"event": "substage"`. On that same 20-minute file the longest gap between two events drops from 39.3 s to 12.7 s.

If you already wrote against 1.14.0, filter `event == "stage"` and nothing changes for you â€” same six events, same order, same indices, same keys. I checked that against the published wheel, not just the source.

Still on my list: those three passes each read the whole file and could share one read. That would actually make long tracks faster rather than just better narrated, but it changes what the engine reads, so it needs proper measurement first.
