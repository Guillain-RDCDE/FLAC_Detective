"""End-to-end ALAC support: routing, full analysis, and the bitrate subtlety.

ALAC is lossless-COMPRESSED inside an .m4a container. Detection is codec-agnostic
(it runs on decoded PCM), so the analyser decodes ALAC -> WAV via ffmpeg and treats
it like any lossless source. The one trap is the *real bitrate*: it must be sized
from the original compressed .m4a, not the decoded WAV — otherwise the file looks
uncompressed and Rules 1 & 3 wrongly switch off. These tests pin all of that.

Fixtures are generated with ffmpeg; the module is skipped if ffmpeg is absent.
"""

from __future__ import annotations

import subprocess

import numpy as np
import pytest

from flac_detective.analysis import audio_formats as af

sf = pytest.importorskip("soundfile")

if not af.ffmpeg_available():
    pytest.skip("ffmpeg/ffprobe not on PATH", allow_module_level=True)


@pytest.fixture(scope="module")
def alac_and_aac(tmp_path_factory):
    """A clean full-spectrum signal encoded as ALAC (.m4a) and AAC (.m4a)."""
    d = tmp_path_factory.mktemp("alac")
    sr = 44100
    n = sr * 12
    # A rich harmonic series (fundamental 100 Hz, partials up to ~20 kHz): energy all
    # the way to Nyquist (no MP3 cliff -> reads authentic) yet low-entropy so ALAC
    # genuinely compresses (unlike white noise, which is ~incompressible). This makes
    # the real/apparent ratio realistic for the bitrate-gate assertion below.
    t = np.arange(n) / sr
    mono = np.zeros(n, dtype=np.float64)
    for f in range(100, 20001, 100):
        mono += np.sin(2 * np.pi * f * t)
    mono /= np.max(np.abs(mono))
    x = np.column_stack([mono, mono]).astype(np.float32) * 0.5
    wav = d / "clean.wav"
    sf.write(str(wav), x, sr, subtype="PCM_16")

    def enc(name, args):
        out = d / name
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-vn", *args, str(out)],
            check=True,
            capture_output=True,
        )
        return out

    return {
        "wav": wav,
        "alac": enc("clean_alac.m4a", ["-c:a", "alac"]),
        "aac": enc("clean_aac.m4a", ["-c:a", "aac", "-b:a", "192k"]),
    }


def test_scan_routes_alac_to_analysis_aac_to_reject(alac_and_aac, tmp_path):
    """A folder with an ALAC .m4a and an AAC .m4a: ALAC analysed, AAC rejected."""
    import shutil

    from flac_detective.main import scan_files

    folder = tmp_path / "lib"
    folder.mkdir()
    shutil.copy(alac_and_aac["alac"], folder / "a.m4a")
    shutil.copy(alac_and_aac["aac"], folder / "b.m4a")

    analyse, reject = scan_files([folder])
    assert {p.name for p in analyse} == {"a.m4a"}  # ALAC -> analysed on its merits
    assert {p.name for p in reject} == {"b.m4a"}  # AAC -> "replace with a real FLAC"


def test_analyze_alac_runs_and_reports_codec(alac_and_aac):
    """Full analysis of a clean ALAC file: decodes, scores, reports the source codec."""
    from flac_detective.analysis.analyzer import FLACAnalyzer

    result = FLACAnalyzer(sample_duration=10.0).analyze_file(alac_and_aac["alac"])

    assert result["verdict"] != "ERROR", result.get("reason")
    assert result["sample_rate"] == 44100
    assert result["encoder"] == "ALAC"  # real source codec, not the temp WAV's "WAV"
    # A clean full-spectrum signal must not be called a fake transcode.
    assert result["verdict"] in {"AUTHENTIC", "WARNING"}


def test_real_bitrate_uses_compressed_source_not_decoded_wav(alac_and_aac):
    """The bitrate subtlety: real bitrate is sized from the .m4a, not the decoded WAV.

    If it were sized from the (uncompressed) decoded WAV, real/apparent would be ~1.0
    and trip the 'uncompressed' gate that disables Rules 1 & 3.
    """
    from flac_detective.analysis.metadata import read_metadata
    from flac_detective.analysis.new_scoring.calculator import _calculate_bitrate_metrics
    from flac_detective.analysis.new_scoring.metadata import parse_metadata

    alac = alac_and_aac["alac"]
    decoded = af.decode_to_wav(alac)
    try:
        meta = parse_metadata(read_metadata(decoded))

        # Sizing the decoded WAV: looks ~uncompressed (gate would fire).
        bm_wrong = _calculate_bitrate_metrics(decoded, meta)
        ratio_wrong = bm_wrong.real_bitrate / bm_wrong.apparent_bitrate
        assert ratio_wrong > 0.92  # decoded WAV ~= uncompressed

        # Sizing the original .m4a (what the analyser actually passes): clearly compressed.
        bm_right = _calculate_bitrate_metrics(decoded, meta, source_path=alac)
        ratio_right = bm_right.real_bitrate / bm_right.apparent_bitrate
        assert ratio_right < 0.92  # compressed -> Rules 1 & 3 stay ON
    finally:
        if decoded:
            decoded.unlink(missing_ok=True)
