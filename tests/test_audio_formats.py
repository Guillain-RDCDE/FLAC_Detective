"""Tests for audio_formats: codec probing, lossless classification, ffmpeg decode.

The structural foundation for ALAC/APE support. Fixtures are generated with
ffmpeg; the whole module is skipped if ffmpeg/ffprobe aren't available.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from flac_detective.analysis import audio_formats as af

sf = pytest.importorskip("soundfile")

if not af.ffmpeg_available():
    pytest.skip("ffmpeg/ffprobe not on PATH", allow_module_level=True)


@pytest.fixture(scope="module")
def sources(tmp_path_factory):
    """A short WAV, plus ALAC, AAC and FLAC re-encodes of it."""
    d = tmp_path_factory.mktemp("fmt")
    wav = d / "src.wav"
    sr = 44100
    x = (np.random.default_rng(0).standard_normal(sr * 2) * 0.2).astype(np.float32)
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
        "alac": enc("a.m4a", ["-c:a", "alac"]),
        "aac": enc("b.m4a", ["-c:a", "aac", "-b:a", "192k"]),
        "flac": enc("c.flac", ["-c:a", "flac"]),
    }


def test_probe_codec(sources):
    assert af.probe_codec(sources["alac"]) == "alac"
    assert af.probe_codec(sources["aac"]) == "aac"
    assert af.probe_codec(sources["flac"]) == "flac"


def test_probe_codec_strips_trailing_comma_and_cr(monkeypatch):
    r"""Regression: ffprobe can emit 'alac,\r' on real ALAC files with cover art.

    Field validation on a real library found ~10 ALAC tracks whose csv codec_name
    came back as 'alac,' (trailing empty field + Windows CR), which made
    is_analysable_lossless reject them as if lossy. probe_codec must normalise it.
    """

    class _R:
        stdout = "alac,\r\n"

    monkeypatch.setattr(af.subprocess, "run", lambda *a, **k: _R())
    codec = af.probe_codec(Path("whatever.m4a"))
    assert codec == "alac"
    # And the file must therefore route to analysis, not the reject list.
    monkeypatch.setattr(af, "probe_codec", lambda _p: "alac")
    assert af.is_analysable_lossless(Path("whatever.m4a")) is True


def test_lossless_classification(sources):
    assert af.is_analysable_lossless(sources["flac"]) is True
    assert af.is_analysable_lossless(sources["wav"]) is True
    assert af.is_analysable_lossless(sources["alac"]) is True
    # An AAC .m4a is lossy — must NOT be treated as analysable lossless.
    assert af.is_analysable_lossless(sources["aac"]) is False


def test_needs_ffmpeg_decode(sources):
    assert af.needs_ffmpeg_decode(sources["flac"]) is False
    assert af.needs_ffmpeg_decode(sources["wav"]) is False
    assert af.needs_ffmpeg_decode(sources["alac"]) is True


def test_decode_alac_to_wav(sources):
    wav = af.decode_to_wav(sources["alac"])
    try:
        assert wav is not None and wav.exists()
        info = sf.info(str(wav))  # readable by libsndfile
        assert info.samplerate == 44100
        assert info.duration == pytest.approx(2.0, abs=0.1)
    finally:
        if wav:
            wav.unlink(missing_ok=True)


# --- archival video containers (v1.13.16) ------------------------------------
# LPCM in MXF / QuickTime, PCM or FLAC in Matroska (FFV1 preservation masters),
# TrueHD and DTS-HD MA next to a remux: once demuxed, the detector reads them
# like any other file. The lossy streams the same containers carry (AC-3, a
# DTS core) go to the reject list.


@pytest.fixture(scope="module")
def containers(tmp_path_factory, sources):
    """Archival containers around the same 2 s source: lossless and lossy ones."""
    d = tmp_path_factory.mktemp("containers")
    wav = sources["wav"]

    def enc(name, args, src=wav, extra_in=()):
        out = d / name
        r = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", *extra_in, "-i", str(src), *args, str(out)],
            capture_output=True,
        )
        return out if r.returncode == 0 and out.exists() and out.stat().st_size > 0 else None

    made = {
        "mka_flac": enc("a.mka", ["-c:a", "flac"]),
        "mkv_pcm": enc("p.mkv", ["-c:a", "pcm_s16le"]),
        "mov_pcm_be": enc("p.mov", ["-c:a", "pcm_s16be"]),
        "mka_truehd": enc("t.mka", ["-strict", "-2", "-c:a", "truehd"]),
        "mkv_ac3": enc("l.mkv", ["-c:a", "ac3"]),
        "mkv_dts_core": enc("d.mkv", ["-strict", "-2", "-c:a", "dca"]),
    }
    # MXF: the muxer wants 48 kHz audio and a video track (OP1a). Best effort;
    # the tests that need it skip when this build of ffmpeg cannot write one.
    src48 = d / "src48.wav"
    sr = 48000
    x = (np.random.default_rng(1).standard_normal(sr * 2) * 0.2).astype(np.float32)
    sf.write(str(src48), x, sr, subtype="PCM_16")
    made["mxf_pcm"] = enc(
        "v.mxf",
        ["-c:v", "mpeg2video", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-shortest"],
        src=src48,
        extra_in=["-f", "lavfi", "-i", "color=c=black:s=64x64:r=25:d=2"],
    )
    return made


def _need(containers, key):
    path = containers.get(key)
    if path is None:
        pytest.skip(f"this ffmpeg build could not write the {key} fixture")
    return path


def test_lossless_audio_in_video_containers_is_analysable(containers):
    for key in ("mka_flac", "mkv_pcm", "mov_pcm_be", "mka_truehd"):
        path = _need(containers, key)
        assert af.is_analysable_lossless(path) is True, key
        assert af.needs_ffmpeg_decode(path) is True, key


def test_mxf_lpcm_is_analysable(containers):
    path = _need(containers, "mxf_pcm")
    assert af.probe_codec(path) == "pcm_s16le"
    assert af.is_analysable_lossless(path) is True


def test_lossy_audio_in_the_same_containers_is_rejected(containers):
    for key in ("mkv_ac3", "mkv_dts_core"):
        path = _need(containers, key)
        assert af.is_analysable_lossless(path) is False, key


def test_dts_is_lossless_only_as_master_audio(monkeypatch):
    """No ffmpeg build encodes DTS-HD MA, so the profile branch is pinned on the probe."""
    monkeypatch.setattr(af, "probe_codec", lambda _p: "dts")
    monkeypatch.setattr(
        af, "probe_stream", lambda _p: {"codec_name": "dts", "profile": "DTS-HD MA"}
    )
    assert af.is_analysable_lossless(Path("remux.mkv")) is True
    monkeypatch.setattr(
        af, "probe_stream", lambda _p: {"codec_name": "dts", "profile": "DTS-HD HRA"}
    )
    assert af.is_analysable_lossless(Path("remux.mkv")) is False
    monkeypatch.setattr(af, "probe_stream", lambda _p: None)
    assert af.is_analysable_lossless(Path("remux.mkv")) is False


def test_probe_stream_reads_profile_and_depth(containers):
    info = af.probe_stream(_need(containers, "mka_truehd"))
    assert info is not None
    assert info["codec_name"] == "truehd"
    assert info.get("bits_per_raw_sample") == "24"


def test_decode_takes_the_first_audio_stream_and_drops_video(containers):
    path = _need(containers, "mov_pcm_be")
    wav = af.decode_to_wav(path)
    try:
        assert wav is not None and wav.exists()
        info = sf.info(str(wav))
        assert info.samplerate == 44100
        assert info.subtype == "PCM_16"
        assert info.duration == pytest.approx(2.0, abs=0.1)
    finally:
        if wav:
            wav.unlink(missing_ok=True)


def test_decode_keeps_a_24_bit_stream_at_24_bits(containers):
    """The WAV muxer's 16-bit default used to truncate a 24-bit source before analysis."""
    path = _need(containers, "mka_truehd")
    wav = af.decode_to_wav(path)
    try:
        assert wav is not None and wav.exists()
        assert sf.info(str(wav)).subtype == "PCM_24"
    finally:
        if wav:
            wav.unlink(missing_ok=True)


def test_pcm_codec_choice():
    assert af._pcm_codec_for(None) == "pcm_s16le"
    assert af._pcm_codec_for({"bits_per_raw_sample": "16", "sample_fmt": "s16"}) == "pcm_s16le"
    assert af._pcm_codec_for({"bits_per_raw_sample": "24", "sample_fmt": "s32p"}) == "pcm_s24le"
    assert af._pcm_codec_for({"bits_per_raw_sample": "N/A", "sample_fmt": "s32"}) == "pcm_s24le"
    assert af._pcm_codec_for({"bits_per_sample": "16", "sample_fmt": "s16"}) == "pcm_s16le"


def test_discover_audio_files_walks_once_and_sorts(tmp_path, containers, sources):
    """An .aiff in a folder is analysed (it was not before 1.13.16); lossy goes to rejects."""
    import shutil

    aiff = tmp_path / "beatport.aiff"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(sources["wav"]), str(aiff)],
        check=True,
        capture_output=True,
    )
    shutil.copy(sources["flac"], tmp_path / "c.flac")
    shutil.copy(sources["aac"], tmp_path / "b.m4a")
    shutil.copy(sources["alac"], tmp_path / "a.m4a")
    (tmp_path / "sub").mkdir()
    shutil.copy(_need(containers, "mkv_pcm"), tmp_path / "sub" / "master.mkv")
    shutil.copy(_need(containers, "mkv_ac3"), tmp_path / "sub" / "dvd.mkv")
    (tmp_path / "notes.txt").write_text("not audio")
    (tmp_path / "song.mp3").write_bytes(b"\x00")

    analysable, rejects = af.discover_audio_files(tmp_path)
    assert {p.name for p in analysable} == {"beatport.aiff", "c.flac", "a.m4a", "master.mkv"}
    assert {p.name for p in rejects} == {"b.m4a", "dvd.mkv", "song.mp3"}
