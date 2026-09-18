# Reply for issue #11

Written 2026-09-18, for 1.14.0. The feature and the reasoning are in the
CHANGELOG (v1.14.0) and in the user guide; this is the short version the
reporter gets. Paragraphs are kept on one line each, as GitHub renders them.

---

Hey, thanks for this — fair complaint, and it's fixed in 1.14.0.

You put your finger on exactly the right spot: the bar and `progress.json` only ever counted finished files, so a one-hour track was a single tick that landed when it was already over. Nothing was lying to you, there was simply nothing being said in between.

There's now `--progress-events`, which reports the stages *inside* each file, one JSON object per line. `--progress-events -` sends them to stderr, or give it a path and you get a clean file you can tail. A line looks like `{"event": "stage", "file": "...", "stage": "spectrum", "index": 3, "total": 6}`. The stages are always prepare, metadata, spectrum, quality, scoring, done — scoring is the long one, that's where the re-encode, the heavy rules and the CNN live. `done` arrives exactly once per file including files that fail, so your UI never ends up waiting on something that already went wrong. From Python it's a callback instead, same stages: `analyze_file(path, on_progress=my_func)`.

About the percentage: I left it out on purpose, and I'd rather tell you why than quietly ship a fake one. Which rules run depends on what the earlier ones found — a file that looks clean early gets out before the expensive half, `--deep` changes that, and several rules only run at certain cutoffs. So when a file is opened, the engine honestly does not know how much work is left in it. `index`/`total` is "stage 3 of 6", not a fraction of the time. A number would have looked nicer and been wrong a lot of the time, which is the problem you already have.

One practical note if you read stderr: the banner and the log are on there too, so match the lines starting with `{"event"` and ignore the rest. A file path gives you a stream with nothing else in it.

Thanks for the clear report — "my UI looks stuck" told me more than a feature request would have :)
