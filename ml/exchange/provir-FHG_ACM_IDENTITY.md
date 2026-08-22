# Fraunhofer ACM codecs shipped by Windows — identity (recorded 2026-08-21 20:10)

| file | version (VersionInfo) | arch | sha256 (16) | bytes | role |
|---|---|---|---|---|---|
| `C:\Windows\System32\l3codecp.acm` | 3.4.0.0 "Fraunhofer IIS MPEG Audio Layer-3 ACM codec" | x64 | 587d64b9eedf3ea3 | 212,992 | **PROFESSIONAL — encoder**, the one we drive |
| `C:\Windows\SysWOW64\l3codecp.acm` | 3.4.0.0 | x86 | 7f0b3f35a85db853 | 196,096 | same codec, 32-bit image |
| `C:\Windows\System32\l3codeca.acm` | 1.9.0.0401 "MPEG Layer-3 Audio Codec for MSACM" | x64 | 5d7f5961411fe64b | 118,784 | "advanced": decode + ≤56 kbps; the ONLY one registered (`Drivers32\msacm.l3acm`) |

- Company string: Fraunhofer Institut Integrierte Schaltungen IIS. Shipped and serviced by Windows (file dates = Windows
  servicing: System32 2026-06-06, SysWOW64 2024-04-01). ⚠ PE timestamps are NOT dates for Microsoft-shipped binaries
  (deterministic builds: the x64 image reads 2028-04-25) — identity is sha256 + VersionInfo here, per the
  banner-is-not-a-build rule.
- Format table (enumerated via acmFormatEnum, 2026-08-21): MPEG-1 Layer III **CBR 32–320 kbps** at 32/44.1/48 kHz stereo
  and mono; MPEG-2 LSF 18–80 kbps at 16/22.05/24 kHz; MPEG-2.5 at 8/11.025/12 kHz. fdwFlags=2 (PADDING_OFF), nCodecDelay 0.
  **No VBR. No intensity-stereo switch exposed.** Output frames: MPEG-1 L3, no CRC, joint stereo (header byte 3 = 0x40),
  no Xing/Info tag (headerless CBR — the wild "FhG-consistent" class shape).
- Behaviour: honours the requested rate (127.7/191.8/319.9 measured on a 30-s encode); **drops the final ~64 ms**
  (no end-of-stream flush; 29.936 s out of 30.000 s at 128k) — a tail signature.
- Access path: `dev_hunt/_encoders/fhg_acm/fhg_acm_encode.py` — LoadLibrary + acmDriverAddW(ACM_DRIVERADDF_FUNCTION)
  + acmDriverOpen + acmStreamOpen against THAT driver handle. Process-local; nothing registered, nothing in the
  registry touched. Licence position: a codec shipped and serviced by Windows, used on that Windows, for R&D
  measurement; no redistribution (it is NOT in the encoder share folder — MANIFEST_RESTRICTED names it).
