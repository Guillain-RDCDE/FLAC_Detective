# NOT in this folder — fetch yourself (licence), with the bytes we hold identified

- **fhg_mp3enc30_demo** — Fraunhofer MP3enc 3.0 DEMO (1998-04-03). Banner: reproduction/distribution prohibited. Fetch: the MP3 encoders archive page 'mp3encdemo_win32.zip' (209 kB). sha256 of mp3encdemo.exe: 54f960064ad0f31d...
- **fhg_mp3enc31_demo** — Fraunhofer MP3enc 3.1 DEMO (1998-09-23). Same page, 'mp3encdemo_3_1_win32.zip' (219 kB). sha256 of mp3encdemo31.exe: 1ce704fafdbe2a05...
- **nero_*** — Nero AAC 1.0.0.2 / 1.0.7.0 / 1.1.34.2 / 1.3.3 / 1.5.1 / 1.5.4 — Nero EULA (free download, no redistribution). Fetch the NeroAACCodec-x.x.x.x.zip archives; our sha256s are in ERA_BUILD_IDENTITY files.
- **qaac/CoreAudio** — Apple AAC via qaac needs Apple's CoreAudio DLLs — Apple's licence; install iTunes/Apple Application Support locally.
- **itunes/fhg_mp3** — Apple's Fraunhofer MP3 encoder inside iTunes 12.13.10.3 — Apple's binary, not redistributable. Drive it headlessly with our _records/itunes_mp3_convert.ps1 (+ itunes_mp3_cell.py checks); bitrate/mode are set in iTunes' Import Settings GUI.
- **ffmpeg / MediaFoundation** — system codecs (ac3, ac3_mf, wmav2, aac_mf, mp3_mf) — use your own ffmpeg build; our cells name the build: ffmpeg 2026-06-15 git-44d082edc8 gyan essentials.
- **mp3enc31full** — EXCLUDED on principle (scene release, licence-key-gated). Not in our register; never will be.
- **fhg_acm/l3codecp34** — Fraunhofer PROFESSIONAL ACM codec l3codecp.acm 3.4.0.0 — shipped by Windows (System32 x64 sha256 587d64b9eedf3ea3…, SysWOW64 x86 7f0b3f35a85db853…). Not redistributable; every Windows 10/11 has it. Driven in-process by dev_hunt/_encoders/fhg_acm/fhg_acm_encode.py (acmDriverAdd FUNCTION — no registration). The tool itself is ours and ships in _records/.

Skipped era_encoders dirs: cdex2006, fhg_mp3enc30_demo, fhg_mp3enc31_demo, lame4.0_src, mp3enc31full, nero_1_0_0_2, nero_1_0_7_0, nero_1_1_34_2, nero_1_3_3, nero_1_5_1, nero_1_5_4, nero_aac
