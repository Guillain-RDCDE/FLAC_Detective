# Era-paired idem battery — registration for mirroring (FLAC Detective, 2026-08-22)

Sealed in the FLAC Detective repository as the docstring of `ml/era_battery.py`
(commit 184fb09 registers it before any measurement). Offered to Provir to mirror
on his DJ-mix discs with the same binaries — same probes, same phases, same
bar rule, same predictions; the only variable is the population.

```
The era-paired idem battery — the generation axis on the wild 34, registered.

Why this exists (2026-08-22)
-----------------------------
Two findings left the wild idem question with one axis unspent. The phase
search (ml/idem_phase_probe.py) retired the instrument objection: at the best
of all 576 phases the 34 owner-attested wilds still read >= 1.89 dB from the
3.100 fixed point, 0/34 below the re-cut lawful bar. But that probe is
libmp3lame 3.100 through ffmpeg's Lavc route, and Provir's era bench says the
tell is VERSION-LOCKED (a 3.100-paired probe reaches its own generation and
the adjacent release only) and ROUTE-LOCKED (libmp3lame through ffmpeg is not
lame.exe of the same version). The 2004 discs were encoded by neither. We now
hold his period binaries (exhibit key lame3.92 = arm-1, verified), and he has
offered to mirror this registration on his DJ-mix discs with the same binaries.

The probes (his period builds, never rebuilds — "the version locks; the
compiler moves the read")
---------------------------------------------------------------------------
    lame3.90.3   2002-2003, the "recommended" build of its day
    lame3.92     2002, arm-1 exhibit key (sha cb2cdfde7b170d90)
    lame3.93.1   2003, period build (lame3.93.1r)
    lame3.96.1   2004-07, the year of the discs
    lame3.97     2006, period build (his genuine dip on the 3.100 V0 probe)
    lame3.98.4   2010
    lame3.100    2017, lame.exe — SAME generation as our shipped probe,
                 different route: this rung isolates the route axis.

Each probe read = two sequential roundtrips through that lame.exe at CBR 320
(files never pipes; output judged by size + decodability, never exit code —
his hurdle rule), R = 20 log10(d1/d2) with the shipped dist(), taken as the
MINIMUM over the canonical phases {0, 529, 47}. Under the 3.92 probe the 34
wilds additionally get the full 576-phase search. R is PROBE-RELATIVE (the
E-series lesson): every bar is cut on the probe's own lawful reads, and raw R
is never compared across probes.

Populations: 34 owner-attested wilds (CD1+CD2), 20 certified-genuine audit
sources (the per-probe lawful repricing), 8 direct lab mp3_320 arms
(libmp3lame 3.100 via ffmpeg — the route/generation lock control).

PREDICTIONS, registered before measurement — results appended below
--------------------------------------------------------------------
    EB1  BARS. Each probe's lawful bar = the minimum of its 20 genuine
         reads. No prediction on the values; they are measured (the draws
         rule). Reported per probe.
    EB2  LOCK CONTROL. The 8 Lavc-3.100 lab arms read ABOVE the lawful bar
         of every era probe 3.90.3-3.98.4 for >= 7/8 files each — the era
         probes do not see modern-route arms (version lock + route lock,
         mirrored). Under the lame.exe-3.100 probe the arms read BELOW its
         bar for >= 6/8 (same generation; if the route alone breaks the
         read, that is the finding).
    EB3  THE WILD QUESTION. Under the best-matching era probe at the best
         phase, at least 2 of the 34 wilds read below that probe's lawful
         bar. Below 2: era pairing recovers nothing either, and the wild
         sits off every fixed point we can build — the mastering layers
         stand entire. At or above 2: the generation axis was real, and
         the count is the recovered fraction.
    EB4  THE RUNG (graded only if EB3 holds). Among recovered wilds, the
         best-reading probe clusters on one rung or two adjacent rungs for
         >= 60 % of them — the disc's encoder generation, read off.
```
