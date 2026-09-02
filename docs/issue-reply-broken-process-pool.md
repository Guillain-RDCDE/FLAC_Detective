# Reply — BrokenProcessPool / WinError 1450 on folders with more than a few files

Thank you for the report, and particularly for pasting the whole stack trace
rather than a summary of it. The trace is what identifies the bug, and it points
somewhere other than where you concluded — which is not a criticism, because the
symptom you saw genuinely looks like the cause you named.

## What is actually happening

Your diagnosis was that FLAC Detective loads every FLAC into memory at once. It
does not, and the trace shows it: the failure happens in

```
File "<frozen importlib._bootstrap_external>", line 1652, in _fill_cache
OSError: [WinError 1450] Insufficient system resources exist to complete the requested service
```

`_fill_cache` is the import machinery **listing a package directory**. The
worker died while importing `flac_detective`, before it had opened a single
audio file. Nothing had been decoded, so nothing was in memory.

The real cause is start-up cost, multiplied. Windows spawns rather than forks,
so each of your 16 workers is a fresh interpreter that re-imports the entire
stack — numpy, scipy, soundfile and torch — before it looks at any file. Sixteen
of those importing in the same instant open thousands of file handles at once,
and Windows answers with `WinError 1450`. Once a worker dies during start-up the
pool is broken, and every remaining file goes down with it.

Your "less than 10 files" observation fits: with fewer files than workers, the
pool spawns fewer processes, and the import storm never reaches the threshold.

## Three defects, not one

Your report exposed three, and all three are ours:

1. **No cap on the worker count.** It was `os.cpu_count()`, which is the right
   number for CPU-bound work with cheap workers and the wrong one when every
   worker pays a heavy import first. The cost that matters here is per process,
   not per core.
2. **No way for you to lower it.** There was no `--workers` flag. You had a
   16-core machine, a failure caused by using 16 workers, and no supported way
   to ask for fewer. That is the part of this I am least happy about.
3. **No recovery.** `BrokenProcessPool` reached you as a bare traceback with
   nothing analysed, when the obvious response — stop asking for workers and
   finish the job here — was available the whole time.

## What is fixed in v1.13.8

- The default worker count is capped (8). Declared as a ceiling, not measured as
  an optimum: past it the marginal throughput gain is small on any machine we
  have, and the start-up cost is paid per process regardless.
- **`--workers N`** exists. `--workers 1` analyses in the main process and
  spawns nothing at all, which is the reliable answer on any machine where
  workers cannot start.
- If the pool dies anyway, the run no longer dies with it: what is already
  recorded is saved, and the remaining files are analysed in the main process.
  You get a complete report, more slowly, plus a log line that names the cause
  instead of showing you a traceback about futures.

## What I could not do, stated plainly

**I could not reproduce your failure.** This machine has 4 cores, so it never
spawns 16 workers, and it does not run the Microsoft Store build of Python whose
package directory lives behind the WindowsApps virtualisation layer — which I
suspect makes those concurrent directory listings more expensive than they are
on a normal install. The fix is therefore built on your trace and on the
mechanism it points to, not on a reproduction I can show you.

So the fix could be wrong, and there is one measurement that would tell us. If
you are willing:

1. `pip install -U flac-detective` (v1.13.8 or later), then run your folder
   again with the default settings. If the cap alone is enough, it completes.
2. If it still dies, run `flac-detective --workers 1 ".\my-folder"`. If **that**
   completes, the diagnosis is right and only the cap was too generous for your
   machine. If it dies too, the diagnosis is wrong and I would want the new
   trace, because then the problem is not worker start-up at all.

Either answer is useful and the second is more useful. Thank you again.

## One aside

You reported against v1.13.0. Two other Windows bugs in that version have been
fixed since — it could not start at all on a console using the cp1252 code page,
and `--format json` could not be piped. Neither is related to this, but they are
reasons to upgrade beyond this fix.
