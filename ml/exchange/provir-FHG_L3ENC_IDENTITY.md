# Fraunhofer l3enc — the FIRST MP3 encoder (1994–1997), identities (banked 2026-08-21 22:57 from the owner's rarewares drop, via Encoders/FhG on the Drive)

| package | file | sha256 (16) | bytes |
|---|---|---|---|
| l3enc_0.99a_1994 | l3dec.exe | 64f4854a6a63b369 | 82308 |
| l3enc_0.99a_1994 | l3enc.exe | ec5b21109bbf0465 | 94242 |
| l3enc_0.99a_1994 | l3enc_fp.exe | 2cf4018c5c871dac | 83896 |
| l3enc_0.99c | l3dec.exe | 3e239e34abeeaca0 | 80067 |
| l3enc_0.99c | l3enc.exe | d28943e9e19a29c2 | 94240 |
| l3enc_0.99c | l3enc_fp.exe | c2d8d46d037dc65a | 83894 |
| l3enc_1.00 | l3enc.exe | 9eb617d5f2a7f618 | 143364 |
| l3enc_1.50_1995 | l3dec.exe | 85024fa423df9360 | 174421 |
| l3enc_1.50_1995 | l3enc.exe | 9eb617d5f2a7f618 | 143364 |
| l3enc_2.00 | L3DEC.EXE | 7f3cf3f724ebeab9 | 192917 |
| l3enc_2.00 | L3ENC.EXE | 7461b3af4cc93bf8 | 316343 |
| l3enc_2.60_1996 | l3dec.exe | dcdcb51c54a94111 | 199425 |
| l3enc_2.60_1996 | l3enc.exe | d52a352a2b8e370d | 327245 |
| l3enc_2.61 | l3dec.exe | 1795a976657368c1 | 199425 |
| l3enc_2.61 | l3enc.exe | 3d569ea92790d3c2 | 327269 |
| l3enc_2.70_1997 | l3dec.exe | 65029466ce352a42 | 197359 |
| l3enc_2.70_1997 | l3enc.exe | 763680f0299eceb6 | 344568 |
| l3enc_2.71 | l3dec.exe | 0fefecdc76dfe2a6 | 197359 |
| l3enc_2.71 | l3enc.exe | 4f40c45aac43ae22 | 344568 |
| l3enc_2.72 | L3DEC.EXE | 7ba80ff8c8e06e56 | 197409 |
| l3enc_2.72 | L3ENC.EXE | 62476feeb1cdc7b3 | 344772 |

- ALL l3enc.exe are **DOS** binaries (DJGPP/GO32, EMX/RSX DOS extenders; the 0.99x 8088/80486 builds) — they cannot run on 64-bit Windows; they need DOSBox (or DOSBox-X) to be driven. l3dec.exe = Fraunhofer's own decoder of the same era.
- Versions held: 0.99a (Mar 1994), 0.99c (Jun 1994), 1.00 (Jul 1994, WAV input), 1.50 (Feb 1995), 2.00 (Sep 1995), 2.60 (1996), 2.61, 2.70 (1997), 2.71, 2.72 (+ a third-party Win32 frontend in 2.72/Frontend: L3ENC_FE.exe / Wrap.exe / l3codec.exe — launchers, not encoders).
- Licence (README.TXT 2.72): shareware; 'You may give copies of the unregistered shareware version of this software to other people as long as no file is changed and no file is omitted' -> the COMPLETE packages are redistributable and ship in the share folder as whole directories; unregistered use is a 30-day evaluation; bitstreams from the unregistered version may not be marketed or broadcast — R&D measurement only.
- NOT YET MEASURED (DOSBox needed). When driven: `l3enc in.wav out.mp3 -br 128000` (bit/s; see each MANUAL.TXT; 0.99x takes raw 16-bit input, WAV from 1.00).

**2.70 DOES NOT RUN under DOSBox 0.74-3 (2026-08-22 01:36):** `l3enc_2.70_1997/l3enc.exe` (sha 763680f0299eceb6, 344,568 B, ships
with `go32.exe` — a DJGPP/DPMI-extended build) starts, writes nothing to LOG.TXT and produces no OUT.MP3; it sat 8 minutes at
01:28 where every other l3enc build returns in ≤60 s, and it had failed once before in the evening. Killed; excluded from the sweep
(`SWEEP_SKIP_EXTRA=l3enc_2.70` for the closing pass). Ladder unaffected: 2.61 and 2.71 bracket it at 15,057–15,100 Hz @112k.
Route if ever needed: CWSDPMI/real DOS VM rather than DOSBox's built-in DPMI. The other nine packages: 27/27 cells OK.
