# Reply to post on the issue

Thanks for this — and genuinely, thank you for pasting the whole traceback
instead of a summary. It's what let me find the bug in about ten minutes, and it
points somewhere other than where either of us would have guessed from the
symptom.

**Your diagnosis is off, but only because the real cause is hiding.** The tool
isn't loading your FLACs into memory. Look at where it actually dies:

```
File "<frozen importlib._bootstrap_external>", line 1652, in _fill_cache
OSError: [WinError 1450] Insufficient system resources
```

`_fill_cache` is Python's import machinery listing a package directory. The
worker died **while importing FLAC Detective**, before it opened a single audio
file. Nothing had been decoded yet, so nothing was in memory.

Here's what's really going on. Windows spawns workers instead of forking them,
so each of your 16 workers is a brand-new interpreter that has to re-import the
whole stack — numpy, scipy, soundfile and torch — before it looks at anything.
Sixteen of those starting at the same instant open thousands of file handles at
once, and Windows says no. Your "it works under 10 files" observation is the
clincher: with fewer files than workers, fewer processes get spawned, and the
import storm never hits the ceiling.

So: your bug report is completely valid, your reproduction steps are right, and
the number that matters is your core count rather than your file count.

**You found three separate bugs, and all three are mine.**

1. The worker count was just `os.cpu_count()`, with no cap. That's the right
   number when workers are cheap. It's the wrong number when every worker pays a
   heavy import first — that cost is per *process*, not per core.
2. **There was no `--workers` flag at all.** You had a 16-core machine, a crash
   caused by using 16 workers, and no supported way to ask for fewer. That's the
   one I'm least happy about.
3. A dead pool killed the entire run instead of falling back. The obvious
   response — stop asking for workers and just finish the job here — was
   available the whole time.

**Fixed in v1.13.8:**

- Default worker count is capped at 8. It's a declared ceiling, not a measured
  optimum: past that the throughput gain is small anyway, and the start-up cost
  is paid per process regardless.
- `--workers N` now exists. **`--workers 1` runs everything in the main process
  and spawns nothing at all** — the reliable escape hatch on any machine where
  workers struggle to start.
- If the pool dies anyway, the run no longer dies with it. Whatever finished is
  saved, the rest is analysed in the main process, and you get a log line naming
  the cause instead of a wall of traceback about futures.

**Now the honest part: I could not reproduce your crash.** This machine has 4
cores, so it never spawns 16 workers, and it doesn't have the Microsoft Store
build of Python — whose packages live behind the WindowsApps virtualisation
layer, which I suspect makes those concurrent directory listings noticeably more
expensive than on a normal install. So the fix is built on your traceback and the
mechanism it points to, not on a crash I watched happen.

Which means I might be wrong, and there's one test that would tell us. If you
have five minutes:

1. `pip install -U flac-detective`, then run your folder again with default
   settings. If capping the workers was enough, it just finishes.
2. If it still dies, try `flac-detective --workers 1 ".\my-folder"`. If **that**
   works, the diagnosis is right and 8 is still too generous for your setup —
   tell me and I'll look at deriving the cap from available memory rather than
   picking a number.
3. If even `--workers 1` dies, then worker start-up isn't the cause at all, I've
   fixed the wrong thing, and I'd really like to see that new traceback.

Any of the three answers helps, and honestly the third would be the most
interesting.

One last thing, unrelated but worth knowing since you're on v1.13.0: two other
Windows bugs have been fixed since then — it wouldn't start at all on a console
using the cp1252 code page, and `--format json` couldn't be piped anywhere. Both
are fixed in the same upgrade.
