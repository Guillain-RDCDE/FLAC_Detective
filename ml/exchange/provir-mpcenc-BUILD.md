# mpcenc on Windows, built from canonical source — 2026-08-20

**Status: BUILT AND VERIFIED.** `MPC Encoder 1.30.1 --stable--`, PE32+ x86-64, native Windows, no
WSL, no downloaded binary.

## Why build rather than download

Windows binaries of mpcenc do exist (musepack.net's own download page; also
`github.com/Olsro/mpcenc-all-archs-windows-builds`). **We are not claiming a first.** We build from
source for a reason specific to this project:

⛔ **Encoder build is load-bearing for our claims.** We bracketed GMF to LAME 3.92–3.93.1
([[mp3-is-a-decoder-spec-version-matters]]) — i.e. we already assert that encoder *version* changes
the artifacts we detect. Generating forensic fixtures with a binary of unknown build provenance and
then making encoder-specific claims off them is self-undermining. A source build with a recorded
source hash, patch set and toolchain is the only defensible route for a provenance tool.

⚠ It also has to run on Windows natively, not under WSL. Provir ships on Windows; a fixture
generator a reviewer cannot run on the platform the tool targets is the freeze-harness defect
inverted ([[freeze-harness-could-not-fail-on-a-clone]]).

## Provenance

| item | value |
|---|---|
| source | `https://files.musepack.net/source/musepack_src_r475.tar.gz` |
| sha256 | `a4b1742f997f83e1056142d556a8c20845ba764b70365ff9ccf2e3f81c427b2b` |
| size | 188,737 bytes · revision 475 · released 2011-08-10 |
| licence | BSD-3-Clause AND LGPL-2.1-or-later (project also carries GPL-2.0-or-later and Zlib parts) |
| toolchain | MSVC 19.44.35207 (VS 2022 Community 17.14), CMake 4.4.2, x64 Release |
| configure | `cmake -G "Visual Studio 17 2022" -A x64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| binary sha256 | `39b58fa2aed5fd18e67a5f9fc551e8bf167c35bd5fff55b741587d4bd062137a` |
| binary | 189,952 bytes, `MPC Encoder 1.30.1 --stable--`, built 2026-08-20 09:49 |

⚠ **GPL is not linked.** `mpcenc` needs only `mpcpsy_static` + `mpcenc_static`. The GPL dependency
(`libcuefile`) is required only by `mpcchap` and `mpcgain`, and those two subdirectories are dropped
from the build. Relevant to [[open-core-calibration-split]].

## The patch set — `provir-msvc-r475.patch`, 8 files

The upstream CMake build **cannot configure under MSVC at all**, and has not been able to since 2011.
Four distinct upstream defects, in two species:

**Species 1 — the MSVC path was never once executed.**
1. `mpcdec` / `mpc2sv8` / `mpccut`: each calls `add_executable(...)` twice under MSVC — once inside
   `if(MSVC)` with the `win32/` POSIX shims, then again unconditionally. The second call is missing
   the `if(NOT MSVC)` guard every sibling branch has. ⇒ `add_executable cannot create target ...
   already exists`, configure aborts.
2. `mpcdec/CMakeLists.txt:10` references `${libmpc_SOURCE_DIR}/win32/attgetopt` — **no `.c`
   extension**. That is proof rather than inference: this line cannot ever have compiled.

**Species 2 — portability guards that rotted with TIME, not with platform.**
3. `libmpcpsy/psy_tab.c:190` supplies its own `asinh()` under `#ifdef _MSC_VER`. Correct in 2011;
   MSVC 2013 (`_MSC_VER 1800`) added the C99 math functions and declares `asinh` as
   `__declspec(dllimport)`, so the local definition became `error C2491`. Guard now bounded to
   `_MSC_VER < 1800`.
4. `libmpcenc/bitstream.c:96` defines a lookup table **named `log2`**, which collides with C99
   `log2()` once `<math.h>` declares it. Renamed to `log2_tab`. ⚠ The two follow-on errors
   ("subscript requires array or pointer type", "too few arguments") were CONSEQUENCES of this one
   collision, not separate bugs.
5. `__builtin_log2` (GCC builtin, no MSVC equivalent) in `common/huffman-bcl.c` and
   `libmpcenc/encode_sv7.c` — shimmed to C99 `log2` under `_MSC_VER`.

⭐ Both species are ones this project already has names for: a code path that cannot execute is
indistinguishable from one that works until you run it ([[corroboration-accepts-non-evidence]]), and
a guard keyed on the wrong variable (compiler, when the real axis is compiler *version*).

## Verification — positive-controlled

Synthetic signal only. **No corpus audio was used**, so this is reproducible by anyone.

Encoded white noise, pink noise and a 20 Hz→Nyquist sweep at all five profiles; decoded with
ffmpeg's `mpc8`; measured the band edge as the highest Welch bin within 40 dB of the 1–10 kHz
reference.

⭐ **Positive control passes**: the untouched source measures 22,050.0 Hz, i.e. the instrument
reports *no* cutoff where there is none. Without that the numbers below mean nothing.

### The encoder's own reported bandwidth cap

| profile | 44.1 kHz | 48 kHz |
|---|---|---|
| `--thumb` | 13.1 kHz | 13.5 kHz |
| `--radio` | 15.8 kHz | 16.5 kHz |
| `--standard` | 20.0 kHz | 20.2 kHz |
| `--extreme` | 22.1 kHz | 22.5 kHz |
| `--insane` | 22.1 kHz | 24.0 kHz |

Measured edge of the decoded audio agrees with the cap: all three probe types read 22,050.0 Hz at
`--insane`, 44.1 kHz.

## ⛔ CORRECTED 2026-08-20, SAME DAY, BY GUILLAIN — READ THIS BEFORE THE SECTION BELOW

The section that follows was written before his reply and **its central inference is withdrawn.**
Everything measured here stands; the step from measurement to explanation does not.

**Withdrawn:** that the 18,750 Hz *he observed* was our 48 kHz band boundary surfacing in his data.
It was not. He measured his own reporting path: `detect_cutoff` scans 250 Hz slices upward from
14,000 Hz and returns slice **boundaries**, so every slice-method cutoff lands on `14,000 + k×250`.
His 18,750 is cell `k=19`. Evidence: **154 of 154** slice-method cutoffs across 360 files sit exactly
on that grid, against **0 of 204** self-anchored edges. Same cause for the roundness of his
`21,000 / 21,000 / 20,250`, and for two files "agreeing to the Hz" on a 2.69 Hz bin — one 250 Hz cell.

⭐⭐ **And the agreement was guaranteed arithmetic, so it was never evidence.** His grid steps 250 Hz;
the mpcenc 48 kHz ladder below steps 750 Hz. They share **every third rung** — any 48 kHz band
boundary above 14 kHz would have "matched" his grid exactly. We read an exact coincidence as a cause
without first asking what the two number-lines were. **Two instruments agreeing on a round number is
evidence only if they could have disagreed;** the collision rate the two generators produce by
construction has to be computed first. Applies to us as much as to him: any figure that came off a
slice- or bin-boundary locator is a **cell label**, and its apparent precision is the cell width.

**Unaffected and still measured:** Musepack does not lowpass at 18,750 at `--insane` (three probe
types, 22,050.0 Hz, positive control passing); the `mpcenc.c:1282` arithmetic; the profile ladder.
His medians now carry a stamp saying they are cells rather than measurements, and his AUCs survive —
quantisation is monotone.

⇒ Read the section below as *"where the number 18,750 exists in mpcenc"*, which is true, and **not**
as *"why 18,750 appeared in his results"*, which is false.

## THE MEASUREMENT — 18,750 Hz is a 48 kHz number in mpcenc, and it is not the `--insane` cap

Guillain reported (2026-08-20) that "Musepack still lowpasses at 18,750 Hz even at its top preset".
**That does not reproduce here at either rate.** At `--insane` the cap is the full band — 22.1 kHz at
44.1 kHz, 24.0 kHz at 48 kHz — and three independent probe signals agree with it.

Where 18,750 comes from is exact. `mpcenc.c:1282` reports bandwidth as
`(Max_Band + 1) × (SampleFreq / 32 / 2000)` kHz — 32 subbands, so the step is sample-rate dependent:

```
44100 Hz -> 0.689063 kHz/band   Max_Band=26 -> 18,604.69 Hz   Max_Band=27 -> 19,293.75 Hz
48000 Hz -> 0.750000 kHz/band   Max_Band=24 -> 18,750.00 Hz   <-- EXACT, and unique to 48 kHz
```

**18,750.00 Hz is exactly Max_Band=24 at 48 kHz and matches no 44.1 kHz band boundary at all.**

⇒ The number silently encodes a sample-rate assumption. Applied to 44.1 kHz material — which is what
CD-sourced material is, and what our corpus overwhelmingly is — the corresponding boundary is
**18,604.69 Hz, 145 Hz away**. That gap is *inside* the disagreement between our own two edge-finders
on the Scott Brown exhibit (21,436.3 vs 21,562.8 = 126.5 Hz).

⚠ **What this does NOT establish.** All probes here are synthetic and broadband. Real music with
little HF energy can produce a lower *measured* edge without the codec imposing one — that is
content, not codec, and it is the [[dark-master-confound-and-frame-var]] hazard exactly. So the
honest statement is: **the 18,750 Hz cap does not exist at `--insane`; an effective edge measured on
music is not the codec's bandwidth cap.** His "cutoff separates at 0.90 AUC" is entirely consistent
with the profile ladder above, which is dramatic at `--thumb`/`--radio`.

⚠ **This paragraph originally read**: *"a second worked example of his own conclusion — that
absolute frequency constants are the problem — arriving from the opposite direction."* Overstated,
and withdrawn per the correction at the top: the 18,750 in his results is his grid cell, so this is
not a worked example of anything about his data. What it is: a note on where 18,750 exists inside
mpcenc, which turned out to be irrelevant to why he saw it. Kept visible rather than deleted, since
the mistake is the more useful half.

## Rebuild

```bash
curl -O https://files.musepack.net/source/musepack_src_r475.tar.gz   # verify sha256 above
tar xzf musepack_src_r475.tar.gz && cd musepack_src_r475
patch -p1 < ../provir-msvc-r475.patch
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build --config Release --target mpcenc
```

⚠ `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` is required: the tree declares
`CMAKE_MINIMUM_REQUIRED(VERSION 2.4)` and CMake 4.x refuses anything below 3.5.

## Owed next

- The patch set is upstream-reportable. Musepack r475 is from 2011 and the project is dormant, so
  the realistic destination is a note alongside the existing Windows-build repos rather than a PR.
- ⛔ **Do not quote a Musepack cutoff constant** until it is measured on real material with the
  profile and sample rate stated beside it. See the caveat above.
