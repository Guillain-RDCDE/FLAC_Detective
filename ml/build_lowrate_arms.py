#!/usr/bin/env python3
"""Build the low-rate arms the independence guard has to be priced against.

``INDEPENDENCE_GUARD_REGISTRATION_2026-09-01.md`` declares population P4 before
any constant is chosen, because the guard under test — collapse ``cnn`` and
``spectral`` into one witness when the cutoff is low — cannot tell a band-limited
authentic file from an honest low-bitrate transcode. Both live around 15-16 kHz.

``audit_corpus`` already carries ``aac_ff128`` and ``mp3_192``. It has no MP3
below 192 kbps, which is exactly the neighbourhood where the guard is most likely
to destroy a correct conviction, so the two missing arms are built here from the
same 80 sources, through the same ``transcode`` used for every existing arm, so
the price is charged on files built the same way as the ones that earn the credit.

Built once, before any candidate value is evaluated.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_audit_corpus import Codec, transcode  # noqa: E402

# The two arms audit_corpus lacks, at the rates where a real transcode's cutoff
# collides with a band-limited genuine's.
LOW_RATE_CODECS = (
    Codec("mp3_128", "libmp3lame", "mp3", ("-b:a", "128k")),
    Codec("mp3_V2", "libmp3lame", "mp3", ("-q:a", "2")),
)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=Path(r"C:\Users\loutr\audit_corpus"))
    args = ap.parse_args(argv)

    sources = sorted((args.corpus / "authentic").glob("*.flac"))
    if not sources:
        print(f"no sources under {args.corpus / 'authentic'}", file=sys.stderr)
        return 1

    for codec in LOW_RATE_CODECS:
        out = args.corpus / "fake" / codec.name
        built = failed = 0
        for src in sources:
            if transcode((src, out / src.name, codec)) is None:
                failed += 1
            else:
                built += 1
        print(f"{codec.name}: {built} built, {failed} failed", flush=True)
        if failed:
            print(f"  {codec.name} is incomplete — do not price on it", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
