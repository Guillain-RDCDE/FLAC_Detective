# ENCODER COVERAGE 1995–2026 — the comprehensive list, and what is still missing
Written 2026-08-21 (owner: "we need a comprehensive list of all the encoders used from 1995-2026 and
we need to figure out which ones are still missing"). Companion to `ENCODER_REGISTER.md` (what we
have measured, the source ladder, build identity) and `_convict/idem/ENCODER_PROBE_MAP_v0.md` (the
probe-response matrix). ⚠ Compiled WITHOUT web access (standing order); years marked "~" are from
memory and to be verified against release notes before anything is quoted. Wild prevalence =
[[wild-mp3-encoder-census]] (E:\ calibration, n=2,852, LAST-HOP only).

**Status vocabulary** (ENCODER_REGISTER): measured · owned/unmeasured · gap · excluded (warez) ·
observation-only (wild files, no encoder). **Coverage is counted by probe-able encoder, not by family
name** — the idem tell is generation- AND family-locked, so every cell needs its own probe rung.

---

## 1. MP3 — the family that matters most (83% of the wild's last hop is LAME)

| encoder / lineage | years (~) | where it lived in the wild | status | route |
|---|---|---|---|---|
| **Fraunhofer l3enc / MP3enc (FhG IIS)** — lineage l3enc → MP3enc 3.0/3.1 → FastEnc / the ACM codec | 1994–~2000 | the first encoders; early scene rips, pro tools, ISDN broadcast; output carries NO Xing/Info tag = the wild "FhG-consistent" class | **OWNED — MEASURING (2026-08-21 evening): the OFFICIAL DEMO builds of MP3enc 3.0 (PE 1998-04-03) and 3.1 (PE 1998-09-23), 30-s encode limit, banked in `era_encoders/fhg_mp3enc3{0,1}_demo/` with `FHG_DEMO_BUILD_IDENTITY.md`.** The scene "(full)" 3.1 stays EXCLUDED (licence-key-gated at launch anyway) | Demo builds cover 3.0/3.1 at 30 s; a FULL-length licensed FhG encoder (period product: Audition/CoolEdit, Sound Forge, WMP Pro `l3codecp.acm`, Audioactive) remains the route for >30-s material and for the FastEnc/ACM generation. |
| **Fraunhofer in products** (WMP 10/11 via l3codecp, Nero "FhG mp3", Audition, Sound Forge, Cakewalk, MusicMatch FhG mode) | ~1999–2010 | casual ripping on Windows; pro exports | **measured 2026-08-21** — `l3codecp.acm` 3.4.0.0 (the Windows-shipped PROFESSIONAL codec) driven in-process: 15.8 kHz wall at 128k, no wall at 192/320; the Audition/Sound Forge/WaveLab modern library still open | one licensed FhG encoder covers the lineage at first; build identity per product later |
| **Xing MP3 (AudioCatalyst, XingMPEG, MP3 Grabber; RealJukebox 1999–2001)** | 1998–~2003 | THE late-90s ripper; the hard ~16 kHz lowpass at every rate; 2 genuine specimens on disk | **GAP — highest-value single landmark** | RealJukebox (free download, believed Xing-based, to verify) or boxed AudioCatalyst 2.x on eBay; OEM burner bundles. Never abandonware sites. |
| **ISO dist10 lineage: BladeEnc 0.91/0.92.7/0.94/0.94.2** | 1998–2001 | Linux/Amiga/early PC ripping | **measured** (4 builds; invisible on both spectral axes; lattice sees it off-grid) | — |
| **8hz-mp3, SoloH, Plugger, mpegEnc** (dist10 siblings) | 1997–2000 | niche | GAP (cheap lineage breadth) | GPL/open archives |
| **Shine** (fixed-point, later libshine in ffmpeg) | 2001–; ffmpeg `-c:a libshine` | embedded devices, some Android apps | GAP, **free** (ffmpeg build with libshine) | build ffmpeg w/ libshine |
| **Gogo-no-coda** (LAME-derived, Japan) | 1999–2003 | Japanese ripping scene | GAP | open source archives |
| **LAME 3.0–3.8x** (pre-3.90) | 1998–2000 | Napster era first wave | **measured 2026-08-21** (archive set: 3.20, 3.24b, 3.30b, 3.34b, 3.50, 3.55b–3.63b, 3.65b–3.70, 3.80b, 3.82b, 3.85b, 3.87a–3.89b = 24 runnable rungs; 3.29b/3.35b 16-bit, 3.83b/3.86b invalid images — cannot run) | — |
| **LAME 3.90.x (r3mix/--alt-preset era)** | 2001–2002 | Napster/Audiogalaxy/Kazaa golden age | **measured** (3.90, 3.90.1, 3.90.3 ×2 builds, 3.91 + 2002 daily) | — |
| **LAME 3.92 / 3.93.1** | 2002–2003 | Kazaa/Limewire/Soulseek; GMF bracketed here | **measured** (3.92, 3.93, 3.93.1r, 3.93.1w32 — ⚠ w32 built 2023 from 2002 source) | — |
| **LAME 3.94/3.95** | 2003–2004 | short-lived | **measured** (3.94b + 3.95 built here from source 2026-08-21; byte-identical cells; V0 era-bench KNEE) | — |
| **LAME 3.96.1** | 2004–2005 | Limewire peak, EAC/CDex/dBpoweramp defaults | **measured** | — |
| **LAME 3.97** | 2006–2007 | rip scene; Audacity bundles | **measured** (wb_lame3.97 = libmp3lame-win-3.97; 3.97 exe not held) | exe build optional |
| **LAME 3.98.x** | 2008–2010 | scene, Google Play Music? , Bandcamp early | **measured** (3.98.4) | — |
| **LAME 3.99.x** | 2011–2016 | **69% of the wild's last hop** — streaming-era transcodes, Bandcamp, SoundCloud, most re-rips | **measured** (3.99.5) | — |
| **LAME 3.100** | 2017–2026 | ffmpeg/libmp3lame everywhere (Lavc tag = ffmpeg wrapper, 9.6% wild), Audacity, dBpoweramp, every modern store MP3 | **measured** (3.100.1; also the probe itself) | — |
| **ffmpeg libmp3lame wrapper (Lavc/Lavf tags)** | 2008–2026 | YouTube-DL era, SoundCloud, web services | **measured** (system path, ffmpeg) | — |
| **Apple iTunes MP3 encoder** (Apple's own, SoundJam lineage) | 2001–~2019 | casual Mac/Windows ripping, iTunes users | **measured 2026-08-21 via COM** (3×3 CBR ladder + 256-VBR cell = 12 cells, all OK; `_encoders/itunes/`; iTunes 12.13.10.3 on this machine) — no lowpass at ANY rate, 128 included; observation via produced files only | keep; add VBR/CBR ladder |
| **Helix MP3 (Real, open-sourced Xing descendant)** | 2004–2010 | Helix Producer, some Linux | **measured** (hmp3) | — (also a candidate PROBE for the Xing lineage? unproven) |
| **Windows Media Foundation MP3 encoder** | Win8+ 2012– | WMP/Groove exports | **measured** (MediaFoundation system path) | — |
| **MusicMatch Jukebox** | 1998–2005 | huge casual-ripper share 1999–2003 (FhG or Xing engine by version) | GAP (engine = FhG/Xing above) | covered when FhG+Xing are |
| **Audiograbber / CDex / EAC front-ends** | 1998– | enthusiast rips — they bundle LAME (and earlier Blade/Xing/FhG plugins) | covered via engines (CDex 1.51 confirmed an installer, not an encoder) | — |
| **mp3PRO (Thomson/Coding Technologies, SBR)** | 2001–2005 | brief; RCA Lyra, MusicMatch | GAP (minor; decodes as mp3 at half rate) | licensed period product |
| **Android/phone MP3 (LAME in apps), Sony SonicStage MP3, Samsung** | 2005– | phone rips | covered (LAME) / GAP (Sony = FhG?) | — |

## 2. AAC — the streaming/store family

| encoder | years (~) | wild channel | status | route |
|---|---|---|---|---|
| **Apple CoreAudio AAC (iTunes/qaac; TVBR/CVBR)** | 2003–2026 | iTunes Store/Apple Music 256 (2007 "iTunes Plus" → now), iPhone rips | **measured** (qaac, 10 cells; bench arms qaac_tvbr91/127, cvbr256(v)) | — |
| **Fraunhofer FDK-AAC** | 2012–2026 | **every Android**, much streaming/podcast, Bandcamp AAC? | **GAP, free** (open source; ffmpeg `libfdk_aac` nonfree build) | build ffmpeg with libfdk_aac or use fdkaac CLI |
| **Nero AAC (neroAacEnc 1.0.0.2 → 1.5.4)** | 2006–2010 | enthusiast AAC, HE-AAC | **measured** (7 builds; NAACEnc Nero6 plugin = real blocker) | — |
| **FAAC** | 2001–2010s | Linux ripping, early ffmpeg | **measured** | — |
| **ffmpeg native aac (libavcodec)** | 2008–, usable 2015– | YouTube-DL transcodes, web services, our own arms (aacff_*) | **measured** | — |
| **libvo-aacenc (VisualOn, Android 2.3–4.x)** | 2010–2013 | early Android recordings/exports | GAP, free | old ffmpeg builds / vo-aacenc source |
| **Coding Technologies aacPlus (HE-AAC v1/v2)** | 2003–2007 | Winamp, Nero "Nero Digital", Sonic, XM/Sirius, early streaming | GAP (partially via Nero HE) | Winamp-era licensed copies |
| **Dolby Pulse / Dolby HE-AAC** | 2008– | broadcast (DAB+, DVB) | GAP (broadcast, low priority for music files) | — |
| **Microsoft Media Foundation AAC** | Win7+ 2009– | WMP/Movie Maker exports | **measured** (MediaFoundation) | — |
| **MainConcept AAC** (Adobe Premiere/Audition, Vegas, Flash Media Encoder) | 2005– | video-export rips, YouTube uploads | GAP | licensed Adobe/Vegas |
| **exhale (xHE-AAC / USAC)** | 2020– | niche, future streaming | **measured** (128/192; 320 does not exist) | — |
| **YouTube/Google AAC** (unknown encoder behind `mp4a` 128) | 2006– | YouTube rips — a huge wild source | observation-only (rips identify the channel, not the encoder) | characterise from wild; encoder unknowable |
| **Spotify web AAC 128/256, Amazon/Tidal AAC 320** | 2015– | stream rips | observation-only | same |

## 3. Ogg Vorbis / Opus / Musepack

| encoder | years (~) | wild channel | status |
|---|---|---|---|
| libvorbis 1.0–1.0.1 (oggenc 1.0) | 2002–2004 | early Linux | GAP (minor) |
| libvorbis 1.1.x / 1.2.x / 1.3.x (oggenc 1.1.1, 1.2.0, 1.3.3/1.3.4 downloaded) | 2004–2026 | Bandcamp Ogg, Wikipedia, game audio, **Spotify (Ogg q)** | **measured** (vorb_112, vorb_120, oggenc_official, vorb_oggenc111; dl_v_133/134 owned — unmeasured?) |
| aoTuV b5/b6, Lancer, GT3b1 | 2005–2011 | enthusiast Vorbis | **measured** (aotuv_b5, gt3b1); b6/Lancer GAP (minor) |
| **Spotify's Vorbis (q5 ~160 / q9 ~320)** | 2008–2026 | stream rips — a major wild source | observation-only (encoder = libvorbis, settings unknown) |
| libopus 0.9/1.0 (2012) → 1.1 (2013) → 1.2 (2017) → 1.3 (2018) → 1.4 (2023) → 1.5 (2024) → 1.6 | 2012–2026 | YouTube 160 kbps Opus, Discord, WhatsApp, SoundCloud 64k Opus | **measured** (8 builds 0.1.2 → 1.6.1; hard-CBR + VBR cells) |
| Musepack (mpcenc 1.15/1.16/1.30) | 1999–2009 | enthusiast archive scene | **measured** (r475 build; Guillain holds r495 — banner collision case) |

## 4. Proprietary / platform / legacy families (lossy, music-relevant)

| codec / encoder | years (~) | wild channel | status | route |
|---|---|---|---|---|
| **Windows Media Audio (WMA 7/8/9 Std, WMA Pro)** | 1999–2010 | Napster 2.0 / Zune / PlaysForSure stores, WMP ripping default 1999–2005 — **enormous casual share**; memory: 32/32 unarmed = total blind spot | **GAP, free** (Windows Media Format SDK / WMP still encodes WMA) | use WMP / MF WMA encoder on this machine |
| **RealAudio `cook` (RealNetworks G2/8/10)** | 1998–2005 | 90s–2000s stream rips | **GAP — decode-only; observation-only** | RealProducer Basic (was free) for an encoder; ffmpeg decodes |
| **Sony ATRAC1 / ATRAC3 / ATRAC3plus** | 1992/1999/2002–2009 | MiniDisc, Walkman, SonicStage | **measured** (bench arms atrac1_sp, atrac3_lp2, atrac3plus — [[atrac-encoder-acquired]]) | — |
| **MP2 (MUSICAM/Layer II)** | 1995– | DAB/DVB broadcast, TV rips | **measured** (mp2_256 arm) | — |
| **Dolby AC-3** | 1995– | DVD/concert/TV rips | owned/unmeasured (ffmpeg encodes natively — register correction says measure it) | run it |
| **DTS** | 1995– | DVD rips | GAP (ffmpeg dca encoder experimental) | low priority |
| **QDesign Music Codec (QuickTime)** | 1998–2002 | early QuickTime streams | GAP (no encoder) | low |
| **TwinVQ / VQF (NTT/Yamaha)** | 1997–1999 | SoundVQ era | GAP (no encoder; ffmpeg decodes) | low |
| **Bluetooth captures (SBC / aptX / AAC-BT / LDAC)** | 2005– | "recorded over Bluetooth" provenance | GAP (niche) | low |
| **MQA** | 2014–2024 | Tidal Masters — lossy-folded inside FLAC | GAP / observation-only | relevant to provenance claims; low for now |
| **Neural codecs: EnCodec (2022), SoundStream (2021), DAC (2023), Suno/Udio internal (2023–26)** | 2021–2026 | AI-generated music exports | partly measured (EnCodec 48k idem move; Suno 55/55 via learned scars) — the [[ai-generated-detection-fork]] | — |

---

## 5. THE GAP LIST — ranked by (wild prevalence × our blindness × cost)

1. ~~Fraunhofer MP3 encoder~~ **→ PARTLY CLOSED 2026-08-21 evening**: the OFFICIAL MP3enc 3.0 and
   3.1 DEMO builds (30-s encode limit; no key) are banked and measuring — first cells already show
   the late-90s FhG lowpass (3.0: ~12.2 kHz at 128k, ~14.7 kHz at 192k). The wild FhG check read
   FhG-consistent files LAWFUL-like under the LAME-3.100 probe (median 3.78, 1/40 below q01) —
   family-locked, as predicted. **The ACM (WMP-era) generation CLOSED 20:15: Windows' own `l3codecp.acm` 3.4 (professional) driven
   in-process — 15.8 kHz wall at 128k only, bandwidth kept above (the start of the keep-bandwidth philosophy
   iTunes-FhG ends in). Still open: l3enc 1.x–2.x (1994–97 shareware), FastEnc, a full-length licensed
   mp3enc, the modern library in Audition/WaveLab/Sound Forge. The scene "(full)" copy stays excluded.
2. **Xing (AudioCatalyst / RealJukebox)** — the extreme 16 kHz case, huge 1999–2001; 2 specimens on
   disk. Route: boxed AudioCatalyst on eBay / RealJukebox; NLnet M4 budget line.
3. **WMA Std/Pro** — total blind spot (32/32 unarmed) and the largest casual-ripping share of
   1999–2005 outside MP3. **PARTLY CLOSED 2026-08-21 evening: ffmpeg `wmav2` (WMA Standard v2) measured
   (18 cells, rate overshoots → RATE_OFF-marked).** Still open: **Microsoft's OWN encoder** (Media Foundation
   WMA Std v9 / WMA Pro — the WMP-ripping lineage) via a small MF tool, and WMA Pro; free on this machine.
4. **FDK-AAC** — every Android device; free. Build ffmpeg with libfdk_aac or use the CLI.
5. ~~**LAME pre-3.90 (3.5x–3.8x) and 3.94/3.95** — fill the generation ladder's gaps; source archives.~~ ✔ DONE 2026-08-21 evening (archive set + two source builds; register has the lowpass ladder 3.20→4.0).
6. **Shine / 8hz / Gogo / SoloH** — dist10 siblings, free, cheap breadth (the family BladeEnc proved
   invisible on two axes).
7. **libvo-aacenc, MainConcept AAC, CT aacPlus** — secondary AAC lineages; licensed where needed.
8. **RealAudio cook** — decode-only; RealProducer Basic if findable; otherwise observation-only rows
   from wild files, labelled so.
9. ~~**AC-3** — owned via ffmpeg, never measured: run it.~~ ✔ DONE 2026-08-21 evening (ffmpeg `ac3` + MediaFoundation
   `ac3_mf`; ac3_mf fixes 256 kbps → RATE_OFF; AC-3 INVERTS the idem sign under its own probe — map carries direction).
10. Observation-only channels (YouTube AAC/Opus, Spotify Vorbis/AAC, Tidal/Amazon AAC): the encoder
    is unknowable but the CHANNEL fingerprint is measurable from wild files — a separate axis.

**Already complete enough to map today (v0):** LAME 3.20→4.0 (49 builds incl. the 08-21 archive set), BladeEnc ×4, Helix,
FAAC, Nero ×7, qaac/CoreAudio, ffmpeg (mp3/aac/opus/vorbis/mp2/ac3), MediaFoundation (mp3/aac),
Opus ×8, Vorbis ×5+, exhale, Musepack, ATRAC ×3, iTunes-mp3 (COM ladder + VBR). ⚠ Per ENCODER_REGISTER the
binding constraint stays **n per cell with the 3-source ladder**, and every new binary gets its
build identity (sha256 / PE date / banner) recorded before a cell is quotable.

**Sharing (owner 17:53):** encoders + the probe-response matrix go to Guillain's Drive as the set
fills in — mechanism, not calibration; fitted thresholds stay.
