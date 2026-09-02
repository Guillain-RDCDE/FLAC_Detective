"""Free-format MP3: ffmpeg cannot read it, so LAME's own decoder has to.

MEASURED HERE on 2 September 2026, not taken on trust. Provir raised it for set
C's MP3 ladder, which climbs past the standard's 320 kbps ceiling into free
format at 512, 600 and 640. The check:

* 10 s of 44.1 kHz stereo, encoded with LAME 3.100 ``--freeformat -b 512``
  (643,656 bytes, ~515 kbps).
* ``ffmpeg -i free512.mp3 out.wav`` fails: ``[mp3float] Header missing``,
  repeated 199 times, no audio produced.
* ``lame --decode free512.mp3 out.wav`` succeeds, 1,764,044 bytes.

His statement is exact.

**Scope, because it is narrower than it first looks.** He ships FLAC, so our
engine never meets a free-format MP3 — the constraint is on whoever BUILDS the
arm. It becomes ours only if we build one, and our builder currently encodes
through ffmpeg's libmp3lame (``ml/build_lowrate_arms.py``), which cannot produce
or read free format either.

What this module is really for is reception: he will ship the decoder build and
its hash alongside the files, and a third-party binary gets its hash checked
before it is executed — the rule already applied to his encoder collection.
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Optional


class DecoderRefused(Exception):
    """The decoder would not, or must not, run. Raised rather than returning empty audio."""


def verify_decoder(lame_exe: Path, expected_sha256: Optional[str] = None) -> str:
    """Hash a decoder binary before running it, and return the digest.

    A binary someone else built is checked against the digest they published,
    every time, before execution. Passing ``expected_sha256=None`` computes the
    digest and returns it without asserting — for the first look at a new build,
    never for a run that matters.

    Raises:
        DecoderRefused: if the file is missing or the digest does not match.
    """
    if not lame_exe.exists():
        raise DecoderRefused(f"no decoder at {lame_exe}")
    digest = hashlib.sha256(lame_exe.read_bytes()).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise DecoderRefused(
            f"{lame_exe.name}: digest {digest} does not match the published "
            f"{expected_sha256.lower()} — not executing it"
        )
    return digest


def decode_free_format(
    mp3: Path, wav_out: Path, lame_exe: Path, expected_sha256: Optional[str] = None
) -> Path:
    """Decode a free-format MP3 with LAME's own decoder.

    ffmpeg is not attempted and not offered as a fallback: it does not fail
    loudly on this input, it emits a header error per frame and produces nothing,
    which is the kind of failure that reaches a manifest as silence.

    Raises:
        DecoderRefused: if the binary fails its hash check or the decode fails.
    """
    verify_decoder(lame_exe, expected_sha256)
    result = subprocess.run(
        [str(lame_exe), "--decode", "--quiet", str(mp3), str(wav_out)],
        capture_output=True,
        timeout=300,
    )
    if result.returncode != 0 or not wav_out.exists() or wav_out.stat().st_size == 0:
        raise DecoderRefused(
            f"lame --decode failed on {mp3.name} (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:200]}"
        )
    return wav_out
