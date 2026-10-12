# Reply to post on issue #6

Thanks for this — and genuinely, thank you for pasting the whole traceback
instead of a summary. It's what let me find this in about ten minutes, and it
points somewhere neither of us would have guessed from the symptom.

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
so each of your 16 workers is a brand-new interpreter that re-imports the whole
stack — numpy, scipy, soundfile and torch — before it looks at anything. Sixteen
of those starting in the same instant open thousands of file handles at once, and
Windows says no. Your "it works under 10 files" observation is the clincher: with
fewer files than workers, fewer processes get spawned and the import storm never
hits the ceiling.

So your report is completely valid, your reproduction steps are right, and the
number that actually matters is your core count rather than your file count.

**You found three separate bugs, and all three are mine.**

1. The worker count was just `os.cpu_count()`, with no cap. That's the right
   number when workers are cheap. It's the wrong number when every worker pays a
   heavy import first — that cost is per *process*, not per core.
2. **There was no `--workers` flag at all.** You had a 16-core machine, a crash
   caused by using 16 workers, and no supported way to ask for fewer. That's the
   one I'm least happy about.
3. A dead pool killed the whole run instead of falling back. The obvious
   response — stop asking for workers and just finish the job here — was
   available the entire time.

**Now the part I owe you before anything else.** You ticked "I am using the
latest version", and you were right: 1.13.0 is the only release on PyPI. Eight
versions of fixes have been sitting on `main` unreleased, including two other
Windows bugs that would have bitten you — the CLI wouldn't start at all on a
console using the cp1252 code page, and `--format json` couldn't be piped
anywhere. You did everything right and there was nothing for you to upgrade to.
That's a packaging failure on my side and it's being fixed with this.

**What's on `main` now:**

- Default worker count capped at 8. It's a declared ceiling, not a measured
  optimum: past that the throughput gain is small anyway, and the start-up cost
  is per process regardless.
- `--workers N` exists. **`--workers 1` runs everything in the main process and
  spawns nothing at all** — the reliable escape hatch on any machine where
  workers struggle to start.
- If the pool dies anyway, the run no longer dies with it: what finished is
  saved, the rest is analysed in the main process, and you get a log line naming
  the cause instead of a wall of traceback about futures.

**And the honest part: I could not reproduce your crash.** This machine has 4
cores, so it never spawns 16 workers, and it doesn't have the Microsoft Store
build of Python — whose packages live behind the WindowsApps virtualisation
layer, which I suspect makes those concurrent directory listings noticeably more
expensive than on a normal install. The fix is built on your traceback and the
mechanism it points to, not on a crash I watched happen.

Which means I might be wrong, and there's one test that would settle it. Once
the release is up, if you have five minutes:

1. Upgrade and run your folder again with default settings. If capping the
   workers was enough, it just finishes.
2. If it still dies, try `flac-detective --workers 1 ".\my-folder"`. If **that**
   works, the diagnosis is right and 8 is still too generous for your setup —
   tell me and I'll derive the cap from available memory instead of picking a
   number.
3. If even `--workers 1` dies, then worker start-up isn't the cause at all, I've
   fixed the wrong thing, and I'd really like to see that new traceback.

Any of the three helps, and the third would be the most interesting of all.
