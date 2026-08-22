# Encoder hurdles and how we got past them — a working list for anyone re-running this register (Guillain first)

Written 2026-08-22 00:20 after one evening that banked ~40 encoder builds from 1994–2008. Every item is something that silently
produced nothing, the wrong thing, or a refusal — and the one move that fixed it. Ordered roughly by how often it will bite.

## Inputs
1. **Old encoders and ffmpeg's default WAV header.** ffmpeg writes a `LIST`/`INFO` chunk before `data`. The 1999 LAME builds
   (3.20, 3.24b, 3.30b) and AudioCatalyst reject it — and 3.20/3.24b fail SILENTLY (exit 0, a 419-byte stub). Always write encoder
   input with `-map_metadata -1 -fflags +bitexact` (plain RIFF: fmt, data). Judge every encoder by its OUTPUT — size and
   decodability — never by its exit code. A cached stub from a failed pass will be re-served by any resumable sweep: treat an
   encode under 4 kB as absent.
2. **Old encoders and paths.** MP3enc 3.0 (1998) could not open a 120-character path; it worked from `C:\tmp_fhg\`. DOS encoders
   need 8.3 names. Keep a short, spaceless scratch root.
3. **Per-channel bitrates.** Helix `-B`, Xing tompg `-B` and several 1990s CLIs take kbps PER CHANNEL: total = 2×. The rate-honoured
   check (bytes·8/seconds vs. the label, 12 % tolerance, status RATE_OFF) is what catches it — and it also caught MediaFoundation AC-3
   ignoring `-b:a` (always 256 k) and ffmpeg `wmav2` overshooting 1.1–1.7×.

## Running the binaries at all
4. **16-bit installers on 64-bit Windows** (InstallShield 3 stubs, SoundVQ, the Thomson mp3PRO player, XingMPEG 1.5's stub is
   Wise 32-bit and fine): Windows refuses the stub, not the payload. Carve the embedded archive: 7-Zip opens IExpress/NSIS/Wise
   wrappers and plain zips; InstallShield 5 cabs (`ISc(`) need our `is5cab_extract.py` (pure Python, in _records); InstallShield 3
   `Data.z`/`.cab` (`13 5D 65 8C`) need `i3comp`/STIX (not yet written in Python).
5. **16-bit DOS encoders** (Fraunhofer l3enc 0.99a–2.72, LAME 3.29b/3.35b, the DOS 3.97): DOSBox 0.74-3, headless — a generated
   `dosbox.conf` whose `[autoexec]` mounts a short-path work dir, runs the encoder with 8.3 names, `exit`; launch with `-noconsole
   -exit` (`l3enc_dosbox.py`). Budget minutes per cell for the 1994 builds; the sweep's per-cell timeout had to go from 300 s to 1800 s.
   The unregistered l3enc shareware caps the format (2.72: 112 kbit/s stereo @ 44.1) — label the cell by the cap, do not fake a ladder.
   l3enc 2.70 (the go32/DPMI build) hangs silently under DOSBox 0.74-3 — no log, no output, where its siblings return in under a
   minute; nine of the ten packages run, 2.70 needs a real DPMI host (CWSDPMI / a DOS VM). Cap the cell and move on.
6. **Windows Media Encoder 9's wrapper demands "DirectX Media 8.1"** — a 2001 runtime that cannot exist on a modern Windows. The check
   is ONLY in the IExpress wrapper; the MSI inside has no such condition. Extract (7-Zip) and `msiexec /i WMEncoder64.msi` elevated.
   Then `WMCmd.vbs -audioonly -a_codec WMA9STD -a_mode 0 -a_setting 128_44_2` drives it headlessly. WME 7/7.1 install into the SAME
   folder and may replace WME 9's files.
7. **Windows' own Fraunhofer professional codec is present but unregistered** (`l3codecp.acm` 3.4; only the decode-only `l3codeca`
   is in Drivers32), so `acmStreamOpen` against the driver list fails at every format. Load the .acm in-process:
   `LoadLibrary` → `acmDriverAddW(&hadid, hmod, DriverProc, 0, ACM_DRIVERADDF_FUNCTION)` → `acmDriverOpen` → `acmStreamOpen`
   against THAT handle. No registration, no system change (`fhg_acm_encode.py`). Use the codec's own enumerated format
   (fdwFlags=2, PADDING_OFF). It drops the last ~64 ms (no end-of-stream flush).
8. **Encoders with no CLI**: AudioCatalyst 2.1 / XingMP3 1.5 engines are COM DLLs with unregistered, undocumented interfaces —
   but XingMP3 1.5 ships `x3enc.exe`, a real CLI (`-b<bit/s>`, `-l` = High Frequency off, `-q`; `-p` waits for a key — never call it
   headless without a timeout). iTunes' Fraunhofer MP3 has no CLI but a COM object (`iTunes.Application`, `ConvertFile2`); bitrate/mode
   live only in its GUI Import Settings (set, OK out, REOPEN to read back, relaunch iTunes; it also keeps a sample-rate field that was
   left at 48 kHz once — check every output). RealProducer Basic 8 (cook) and the Thomson mp3PRO player (`/ENCODE` opens the GUI)
   are GUI-only: owner-encoded files enter our ledger through a manual-emitter folder (`<source>_<rate>.<ext>`), by the same checks.
9. **Plug-in encoders** (Winamp `enc_aacplus.dll` = Coding Technologies aacPlus, `enc_lame.dll`): Winamp's AudioCoder API
   (`CreateAudio3` → C++ object with virtual `Encode`); needs a small host. `lame_enc.dll` is the BladeEnc API and runs through a
   BladeEnc bridge (BE_CONFIG is `#pragma pack(1)`; the LHV1 struct segfaults on old DLLs — use the legacy Blade struct).
10. **Source tarballs on a 2026 toolchain**: LAME 3.94b/3.95 need `id3tag.c`'s `#define snprintf _snprintf` guarded `#if _MSC_VER < 1900`;
    LAME 3.99.x `Makefile.MSVC` passes `/opt:NOWIN98` which modern `link` rejects (LNK1117) — drop the switch; LAME 4.0's tarball has no
    mpglib sources. Vorbis 1.0.1 + libogg 1.0 compile clean with `cl /O2 /MT` straight from the sources (no project files needed).
    Record build date ≠ source date in the identity line — and measure the build: a 2023 rebuild of LAME 3.93.1 reads 2/72 on the V0
    bench where the period build reads 0/72; Helix x64 r11 ships HF mode ON where the x86 build does not. Build ≠ version.

15. **GOGO-no-coda 2.x (WinGOGO 2.24d / 2.39c packs) and `-silent`**: the option parser lives in the engine DLL; the 2.x DLLs
    do not know `-silent`, print usage and WAIT FOR A KEYPRESS — a headless call hangs for ever (ours sat two minutes before
    the kill). Call 2.x as `GOGO_8HZ.EXE in.wav out.mp3 -b <kbps>` with no `-silent`; 3.x takes it. Always run an unknown
    encoder with a timeout the first time. The WinGOGO `wing*.exe` installers are plain LZX cabs — 7-Zip extracts the CLI
    frontend + GOGO.DLL without installing; `.ex_` files inside are MS-compressed (`expand.exe`, the Windows one — the shell's
    `expand` is the GNU tab tool).
16. **LAME 3.94 beta rejects `-k`** ("fatal error during initialization") and `--lowpass -1` too; 3.93 and 3.95+ accept `-k`.
    For a no-lowpass probe across the ladder, run 3.94b at plain `-b 320` (its own 20.1 kHz lowpass) and FLAG the cell — its
    distance is an upper bound, not a like-for-like read.

18. **Winamp encoder plug-ins (`enc_aacplus.dll` = Coding Technologies aacPlus v1.28; also enc_lame/enc_wma/enc_flac)** need
    (a) `NSCRT.dll` (the Nullsoft CRT) and, for MP4 types, `libmp4v2.dll` — both inside the Winamp installer (an NSIS exe; 7-Zip
    extracts single files) — placed BESIDE the plug-in, and the host must load with `LoadLibraryEx(..., LOAD_WITH_ALTERED_SEARCH_PATH)`
    after `SetDllDirectory(plugin folder)` — error 126 otherwise; (b) the AudioCoder API: `CreateAudio3(nch, srate, bps, 'PCM ',
    &outt, inipath)` returns a C++ object whose **vtable slot 0 is Encode** (slot 1 is the deleting destructor — calling it returns
    `this` and kills the coder; slot 3 delay-loads libmp4v2) — `__thiscall` = `__fastcall` with a dummy EDX, x86 host only;
    (c) the INI section names are in the DLL's strings (`audio_aacplus` / `audio_aacplushigh` / `audio_aac`, key `bitrate` in bps)
    and each type accepts a bitrate window (aacPlus 64–128, High 96–256, LC 64–320) — outside it CreateAudio3 returns NULL, which
    is your "unsupported", not an error. Host + build script in _records.

## Archives, packaging, transport
11. **Archive zips lie about their contents**: the LAME archive's "3.93.1" zip holds the 3.90.1 exe; "3.81b" holds 3.80b; the same
    binary appears under several names. Identity is sha256 + PE date + banner, never the zip name. Microsoft-shipped binaries have
    reproducible-build timestamps that are not dates (`l3codecp.acm` reads 2028).
12. **Google Drive for Desktop**: renames extensionless files (README → README.txt) in transit; holds per-folder `desktop.ini` and
    sync locks, so delete-then-copy of a folder dies half-way — mirror by SYNC (copy over, prune strays inside folders you own, never
    touch folders you did not ship) and verify every hash ON THE DRIVE SIDE; the first pass after a large addition can race the
    uploader and report files missing that a second pass finds intact.
13. **Licence routes**: l3enc shareware may be copied ONLY as complete unchanged packages (so it ships whole); Fraunhofer demo builds
    and Nero/Apple/Microsoft binaries are not redistributable — the manifest names the public source and the sha256 so the same
    bytes can be fetched; scene "FULL" packs and leaked libraries (Fastencc, mp3enc 3.1.1 lib) stay out of every public table.

## The instrument
14. **The idem fixed point is grid-locked** (period 576 samples, zero tolerance): a file read one sample off its original MDCT
    grid reads lawful. Fixture rows are phase 0 by construction; wild files are not. Any idem read of a wild file needs a phase
    search ({0, 529, 47} cheaply; all 576 on a 4-s excerpt by d1, then full R at the best) — `idem_phase_search.py`. LAME 3.99.1's
    tag says `L3.99`, which ffmpeg does not recognise, so its output decodes untrimmed (phase 529): that is how this was found.
17. **Naming the encoder VERSION with the grid lock (2026-08-22)**: use each candidate binary as the probe at the file's route
    config, search all 576 phases on a 4-s excerpt by first-pass distance d1, and compare d1 at the best phase — NOT the idem
    ratio R, which is dominated by each encoder's own convergence rate (LAME 3.93 reads R ≈ +16 on lossless input too). Run a
    positive control per candidate version on an OWNED lossless source and a lossless negative (no phase preference) before
    believing the exhibit. Two traps: ffmpeg `-ss` on an MP3 INPUT lands on a frame boundary (1152 = 2 granules), so an MP3
    probed through `-ss` always reports phase 0 — probe MP3s from sample 0 or decode to PCM first; and two builds of one version
    can read differently (lame3.93.1w32, a 2023 rebuild, sits 18 % above the period 3.93.1 on every file).
