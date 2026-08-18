#!/usr/bin/env python3
"""Regenerate the GitHub social preview from a real spectrogram.

Why this is a script and not a hand-made file
---------------------------------------------
The previous social preview was made by hand in June and said "Catch
MP3-to-lossless transcodes — 11-rule spectral analysis + CNN". By August all three
claims were wrong: Rule 3 had been deleted, Rule 13 is not spectral, and the blind
exchange with Provir put both ffmpeg-AAC arms above 128 kbps at 100 % flagged with
Vorbis at AUC 0.955. Nobody noticed, because an image is not something anyone
greps. Jamie Dodd pointed at it.

So the image is generated from constants that sit next to the claims, and
regenerating it is one command.

The background is a real spectrogram of a real AAC transcode from the audit corpus
— not a stock texture. The dark band across the top is the artefact itself: the
frequencies the encoder threw away and the container is pretending to still have.
An AAC source on purpose, since "we only catch MP3" is the claim being retired.

Usage::

    python ml/make_social_preview.py --out docs/social-preview.jpg
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

# GitHub renders social previews at 1280x640.
SIZE = (1280, 640)

TITLE_PLAIN = "FLAC "
TITLE_ACCENT = "Detective"

# The claim, kept beside the code that has to stay true to it.
SUBTITLE = [
    "Lossy transcodes hiding inside lossless files.",
    "MP3 · AAC · Vorbis · Opus — three independent kinds of evidence.",
]
FOOTER = "github.com/Guillain-RDCDE/FLAC_Detective"

ACCENT = (255, 92, 141)
WHITE = (255, 255, 255)
SUBTLE = (214, 214, 222)

FFT_SIZE = 1024

_FONT_CANDIDATES = (
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)
_FONT_REGULAR = (
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """First available system font at ``size``, or PIL's default."""
    for candidate in (_FONT_CANDIDATES if bold else _FONT_REGULAR):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def spectrogram(path: Path, seconds: float = 20.0) -> np.ndarray:
    """Log-magnitude spectrogram, normalised to 0..1, low frequencies at the bottom."""
    info = sf.info(str(path))
    data, rate = sf.read(str(path), dtype="float32", frames=int(seconds * info.samplerate))
    mono = data if data.ndim == 1 else np.mean(data, axis=1)
    window = np.hanning(FFT_SIZE).astype(np.float32)
    hop = FFT_SIZE // 4

    columns = []
    for start in range(0, len(mono) - FFT_SIZE, hop):
        block = mono[start : start + FFT_SIZE] * window
        columns.append(np.abs(np.fft.rfft(block)))
    spec = np.asarray(columns).T
    with np.errstate(divide="ignore"):
        db = 20 * np.log10(np.maximum(spec, 1e-10))
    db = np.clip(db, db.max() - 90.0, db.max())
    db -= db.min()
    return np.flipud(db / (db.max() + 1e-9))


def colourise(norm: np.ndarray) -> Image.Image:
    """Map 0..1 to the deep-violet / magenta / amber ramp of the original preview.

    Hand-built rather than pulled from matplotlib: this is the only thing the whole
    repository would need matplotlib for, and a four-stop ramp is not worth the
    dependency.
    """
    stops = [
        (0.00, (10, 4, 28)),
        (0.35, (86, 24, 92)),
        (0.62, (186, 54, 118)),
        (0.82, (240, 130, 62)),
        (1.00, (255, 214, 140)),
    ]
    positions = np.array([s[0] for s in stops])
    colours = np.array([s[1] for s in stops], dtype=np.float64)
    flat = norm.ravel()
    out = np.empty((flat.size, 3))
    for channel in range(3):
        out[:, channel] = np.interp(flat, positions, colours[:, channel])
    return Image.fromarray(out.reshape(*norm.shape, 3).astype(np.uint8))


def build(source: Path, out: Path) -> int:
    """Render the preview and write it."""
    norm = spectrogram(source)
    image = colourise(norm).resize(SIZE, Image.LANCZOS)

    # Darken from the LEFT, where the type sits, rather than from the top.
    #
    # The first version graded top-down and washed out the one feature that makes
    # this image mean anything: the horizontal cliff where the encoder stopped
    # storing frequencies. That edge is the artefact. Losing it to a gradient
    # leaves a pretty texture that could be any audio at all.
    overlay = Image.new("RGB", SIZE, (0, 0, 0))
    mask = Image.linear_gradient("L").rotate(-90).resize(SIZE)
    image = Image.composite(Image.blend(image, overlay, 0.62), image, mask)

    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 14, SIZE[1]], fill=ACCENT)

    title_font = _font(96, bold=True)
    x, y = 70, 210
    draw.text((x, y), TITLE_PLAIN, font=title_font, fill=WHITE)
    x += int(draw.textlength(TITLE_PLAIN, font=title_font))
    draw.text((x, y), TITLE_ACCENT, font=title_font, fill=ACCENT)

    body = _font(31)
    for index, line in enumerate(SUBTITLE):
        draw.text((70, 356 + index * 44), line, font=body, fill=SUBTLE)

    draw.text((70, 566), FOOTER, font=_font(27), fill=SUBTLE)

    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=92, subsampling=0)
    print(f"{out}  {image.size[0]}x{image.size[1]}  {out.stat().st_size // 1024} KB")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Pick a source with a visible artefact and render."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(r"C:/Users/loutr/audit_corpus/fake/aac_ff128"),
        help="a transcoded file, or a directory to take the first file from",
    )
    parser.add_argument("--out", type=Path, default=Path("docs/social-preview.jpg"))
    args = parser.parse_args(argv)

    source = args.source
    if source.is_dir():
        candidates = sorted(source.glob("*.flac"))
        if not candidates:
            raise SystemExit(f"no .flac under {source}")
        source = candidates[0]
    if not source.exists():
        raise SystemExit(f"{source} not found")
    return build(source, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
