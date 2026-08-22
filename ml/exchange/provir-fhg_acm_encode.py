r"""fhg_acm_encode.py — drive Windows' Fraunhofer PROFESSIONAL MP3 codec (l3codecp.acm v3.4) as an encoder,
loaded IN-PROCESS. No registry change, no system setting touched.

WHY THIS EXISTS (2026-08-21, owner: "I want full FhG coverage"). Windows ships TWO Fraunhofer ACM codecs:
`l3codeca.acm` (1.9 — decode + 56 kbps "advanced", the only one REGISTERED in Drivers32) and
`l3codecp.acm` (3.4.0.0 — the PROFESSIONAL encoder, Fraunhofer-signed, present in System32 (x64) and
SysWOW64 (x86) but NOT registered). The 08-07 bridge (`dev_hunt/fhg_acm.cs`) opened a stream against
"any registered driver" and got ACMERR_NOTPOSSIBLE at every format — because the professional codec was
never in the driver list. The fix is `acmDriverAdd(..., ACM_DRIVERADDF_FUNCTION)`: LoadLibrary the .acm,
hand its DriverProc to MSACM for THIS PROCESS ONLY, then open the stream against that driver handle.
This is the WMP-9/10-on-XP / Sound Forge / Cool Edit era Fraunhofer encoder — the largest casual FhG
share of 1999–2005 — and it has been on this machine the whole time.

  python fhg_acm_encode.py --list                      # enumerate every MP3 format the codec offers
  python fhg_acm_encode.py in.wav out.mp3 --kbps 128   # CBR encode (16-bit PCM WAV in, raw MP3 frames out)
  python fhg_acm_encode.py in.wav out.mp3 --kbps 320 --flags 2   # fdwFlags: 0 ISO padding, 1 on, 2 off

Exit code 0 + a non-trivial output file is the ONLY success signal; the mp3 is also re-decoded by the caller
([[silent-failure-species-census]] 7th species: exit codes are rumours).
"""
import argparse
import ctypes as C
import ctypes.wintypes as W
import os
import sys
import wave

ACM_PATH = r"C:\Windows\System32\l3codecp.acm" if sys.maxsize > 2**32 else r"C:\Windows\SysWOW64\l3codecp.acm"
WAVE_FORMAT_PCM = 1
WAVE_FORMAT_MPEGLAYER3 = 0x0055
MPEGLAYER3_ID_MPEG = 1
ACM_DRIVERADDF_FUNCTION = 0x00000003
ACM_STREAMOPENF_NONREALTIME = 0x00000004
ACM_STREAMCONVERTF_BLOCKALIGN = 0x00000004
ACM_STREAMCONVERTF_START = 0x00000010
ACM_STREAMCONVERTF_END = 0x00000020
ACM_STREAMSIZEF_SOURCE = 0x00000000
ACM_FORMATENUMF_WFORMATTAG = 0x00010000
ACM_FORMATDETAILSF_INDEX = 0
ACMFORMATDETAILS_FORMAT_CHARS = 128


class WAVEFORMATEX(C.Structure):
    _pack_ = 1
    _fields_ = [("wFormatTag", W.WORD), ("nChannels", W.WORD), ("nSamplesPerSec", W.DWORD),
                ("nAvgBytesPerSec", W.DWORD), ("nBlockAlign", W.WORD), ("wBitsPerSample", W.WORD),
                ("cbSize", W.WORD)]


class MPEGLAYER3WAVEFORMAT(C.Structure):
    _pack_ = 1
    _fields_ = [("wfx", WAVEFORMATEX), ("wID", W.WORD), ("fdwFlags", W.DWORD), ("nBlockSize", W.WORD),
                ("nFramesPerBlock", W.WORD), ("nCodecDelay", W.WORD)]


class ACMSTREAMHEADER(C.Structure):
    _fields_ = [("cbStruct", W.DWORD), ("fdwStatus", W.DWORD), ("dwUser", C.c_void_p),
                ("pbSrc", C.c_void_p), ("cbSrcLength", W.DWORD), ("cbSrcLengthUsed", W.DWORD),
                ("dwSrcUser", C.c_void_p), ("pbDst", C.c_void_p), ("cbDstLength", W.DWORD),
                ("cbDstLengthUsed", W.DWORD), ("dwDstUser", C.c_void_p),
                ("dwReservedDriver", C.c_void_p * 15)]


class ACMFORMATDETAILSW(C.Structure):
    _fields_ = [("cbStruct", W.DWORD), ("dwFormatIndex", W.DWORD), ("dwFormatTag", W.DWORD),
                ("fdwSupport", W.DWORD), ("pwfx", C.c_void_p), ("cbwfx", W.DWORD),
                ("szFormat", W.WCHAR * ACMFORMATDETAILS_FORMAT_CHARS)]


msacm = C.WinDLL("msacm32.dll")
k32 = C.WinDLL("kernel32.dll", use_last_error=True)
k32.LoadLibraryW.restype = W.HMODULE
k32.LoadLibraryW.argtypes = [W.LPCWSTR]
k32.GetProcAddress.restype = C.c_void_p
k32.GetProcAddress.argtypes = [W.HMODULE, C.c_char_p]

msacm.acmDriverAddW.argtypes = [C.POINTER(C.c_void_p), W.HMODULE, C.c_ssize_t, W.DWORD, W.DWORD]
msacm.acmDriverOpen.argtypes = [C.POINTER(C.c_void_p), C.c_void_p, W.DWORD]
msacm.acmDriverClose.argtypes = [C.c_void_p, W.DWORD]
msacm.acmStreamOpen.argtypes = [C.POINTER(C.c_void_p), C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p,
                                C.c_void_p, C.c_void_p, W.DWORD]
msacm.acmStreamSize.argtypes = [C.c_void_p, W.DWORD, C.POINTER(W.DWORD), W.DWORD]
msacm.acmStreamPrepareHeader.argtypes = [C.c_void_p, C.POINTER(ACMSTREAMHEADER), W.DWORD]
msacm.acmStreamConvert.argtypes = [C.c_void_p, C.POINTER(ACMSTREAMHEADER), W.DWORD]
msacm.acmStreamUnprepareHeader.argtypes = [C.c_void_p, C.POINTER(ACMSTREAMHEADER), W.DWORD]
msacm.acmStreamClose.argtypes = [C.c_void_p, W.DWORD]
msacm.acmFormatEnumW.argtypes = [C.c_void_p, C.POINTER(ACMFORMATDETAILSW), C.c_void_p, C.c_ssize_t, W.DWORD]
msacm.acmMetrics.argtypes = [C.c_void_p, W.UINT, C.c_void_p]
ACM_METRIC_MAX_SIZE_FORMAT = 50
ACMFORMATENUMCB = C.WINFUNCTYPE(W.BOOL, C.c_void_p, C.POINTER(ACMFORMATDETAILSW), C.c_ssize_t, W.DWORD)


def add_driver():
    hmod = k32.LoadLibraryW(ACM_PATH)
    if not hmod:
        raise OSError("LoadLibrary failed for %s (err %d)" % (ACM_PATH, C.get_last_error()))
    proc = k32.GetProcAddress(hmod, b"DriverProc")
    if not proc:
        raise OSError("DriverProc not exported by %s" % ACM_PATH)
    hadid = C.c_void_p()
    rc = msacm.acmDriverAddW(C.byref(hadid), hmod, proc, 0, ACM_DRIVERADDF_FUNCTION)
    if rc:
        raise OSError("acmDriverAdd rc=%d" % rc)
    had = C.c_void_p()
    rc = msacm.acmDriverOpen(C.byref(had), hadid, 0)
    if rc:
        raise OSError("acmDriverOpen rc=%d" % rc)
    return had


def list_formats(had):
    maxsz = W.DWORD(0)
    msacm.acmMetrics(had, ACM_METRIC_MAX_SIZE_FORMAT, C.byref(maxsz))
    buf = C.create_string_buffer(max(int(maxsz.value), 64))
    wfx = C.cast(buf, C.POINTER(WAVEFORMATEX))
    wfx.contents.wFormatTag = WAVE_FORMAT_MPEGLAYER3
    afd = ACMFORMATDETAILSW()
    afd.cbStruct = C.sizeof(ACMFORMATDETAILSW)
    afd.dwFormatTag = WAVE_FORMAT_MPEGLAYER3
    afd.pwfx = C.cast(buf, C.c_void_p)
    afd.cbwfx = len(buf)
    rows = []

    @ACMFORMATENUMCB
    def cb(hadid, pafd, inst, fdw):
        f = C.cast(pafd.contents.pwfx, C.POINTER(MPEGLAYER3WAVEFORMAT)).contents
        rows.append((pafd.contents.szFormat, f.wfx.nSamplesPerSec, f.wfx.nChannels,
                     f.wfx.nAvgBytesPerSec * 8 // 1000, f.fdwFlags, f.nBlockSize, f.nFramesPerBlock, f.nCodecDelay))
        return True

    rc = msacm.acmFormatEnumW(had, C.byref(afd), cb, 0, ACM_FORMATENUMF_WFORMATTAG)
    if rc:
        raise OSError("acmFormatEnum rc=%d" % rc)
    return rows


def encode(had, pcm, rate, ch, kbps, flags):
    src = WAVEFORMATEX(WAVE_FORMAT_PCM, ch, rate, rate * ch * 2, ch * 2, 16, 0)
    dst = MPEGLAYER3WAVEFORMAT()
    dst.wfx = WAVEFORMATEX(WAVE_FORMAT_MPEGLAYER3, ch, rate, kbps * 1000 // 8, 1, 0, 12)
    dst.wID = MPEGLAYER3_ID_MPEG
    dst.fdwFlags = flags
    dst.nBlockSize = 144 * kbps * 1000 // rate + (1 if flags == 1 else 0)
    dst.nFramesPerBlock = 1
    dst.nCodecDelay = 1393
    has = C.c_void_p()
    rc = msacm.acmStreamOpen(C.byref(has), had, C.byref(src), C.byref(dst), None, None, None,
                             ACM_STREAMOPENF_NONREALTIME)
    if rc:
        raise OSError("acmStreamOpen rc=%d (512 = NOTPOSSIBLE: format not offered)" % rc)
    out = bytearray()
    chunk = 1152 * ch * 2 * 64            # 64 frames of PCM per call
    srcbuf = (C.c_char * chunk)()
    dstlen = W.DWORD(0)
    msacm.acmStreamSize(has, chunk, C.byref(dstlen), ACM_STREAMSIZEF_SOURCE)
    dstbuf = (C.c_char * max(int(dstlen.value), 65536))()
    off = 0
    first = True
    while off < len(pcm):
        n = min(chunk, len(pcm) - off)
        C.memmove(srcbuf, pcm[off:off + n], n)
        hdr = ACMSTREAMHEADER()
        hdr.cbStruct = C.sizeof(ACMSTREAMHEADER)
        hdr.pbSrc = C.cast(srcbuf, C.c_void_p)
        hdr.cbSrcLength = n
        hdr.pbDst = C.cast(dstbuf, C.c_void_p)
        hdr.cbDstLength = len(dstbuf)
        rc = msacm.acmStreamPrepareHeader(has, C.byref(hdr), 0)
        if rc:
            raise OSError("acmStreamPrepareHeader rc=%d" % rc)
        last = off + n >= len(pcm)
        fl = (ACM_STREAMCONVERTF_START if first else 0) | (ACM_STREAMCONVERTF_END if last else ACM_STREAMCONVERTF_BLOCKALIGN)
        rc = msacm.acmStreamConvert(has, C.byref(hdr), fl)
        if rc:
            msacm.acmStreamUnprepareHeader(has, C.byref(hdr), 0)
            raise OSError("acmStreamConvert rc=%d at offset %d" % (rc, off))
        used = int(hdr.cbSrcLengthUsed)
        out += bytes(dstbuf[:int(hdr.cbDstLengthUsed)])
        msacm.acmStreamUnprepareHeader(has, C.byref(hdr), 0)
        if used == 0:
            raise OSError("codec consumed 0 bytes at offset %d — would loop forever" % off)
        off += used
        first = False
    msacm.acmStreamClose(has, 0)
    return bytes(out)


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2, "16-bit PCM only"
        return w.readframes(w.getnframes()), w.getframerate(), w.getnchannels()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--kbps", type=int, default=128)
    ap.add_argument("--flags", type=int, default=2, help="MPEGLAYER3 fdwFlags: 0 ISO padding, 1 on, 2 off (2 = what the codec itself enumerates; default)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    had = add_driver()
    if a.list:
        for r in list_formats(had):
            print("%-40s %6d Hz %dch %4d kbps flags=%d block=%d fpb=%d delay=%d" % r)
        return
    if not (a.src and a.dst):
        ap.error("src and dst required unless --list")
    pcm, rate, ch = read_wav(a.src)
    mp3 = encode(had, pcm, rate, ch, a.kbps, a.flags)
    with open(a.dst, "wb") as f:
        f.write(mp3)
    print("wrote %d bytes (%.1f kbps over %.1f s)" % (len(mp3), len(mp3) * 8 / 1000.0 / (len(pcm) / (rate * ch * 2.0)),
                                                      len(pcm) / (rate * ch * 2.0)))
    if len(mp3) < 4096:
        sys.exit(3)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
