"""Plain-language presentation layer — the "easy mode" voice of FLAC Detective.

The analysis pipeline speaks in plumbing: rule codes (R1, R9, R12), point
contributions (``+30pts``), cutoff frequencies in Hz, residual floors in dB,
softmax probabilities. That's exactly what an *advanced* user wants and what the
default reports have always shown. But a newcomer just wants the traffic light and
a sentence: *is this real, and what do I do?*

This module is the single source of truth for that friendly voice — a verdict's
icon, human label and recommended action, plus a one-line plain explanation
derived from the result's key signals (the spectral cliff, the implied MP3
bitrate, the fake-hi-res axis). The CLI, the text report and the GUI all read from
here so "easy mode" says the same thing everywhere. Pure stdlib; no heavy imports.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

# verdict -> (icon, human label, recommended action). The traffic light from the
# README, in one place. Icons are plain unicode so they render in a terminal too.
_VERDICT_PLAIN: Dict[str, Tuple[str, str, str]] = {
    "AUTHENTIC": ("✅", "Authentic", "Keep it."),
    "WARNING": ("❓", "Worth a check", "Probably fine — give it a listen."),
    "SUSPICIOUS": ("⚠️", "Likely fake", "Likely a transcode — give it a listen."),
    "FAKE_CERTAIN": ("❌", "Fake", "Replace it with a real lossless copy."),
    "NON_FLAC": ("🚫", "Not lossless", "Replace it with a real lossless file."),
    "ERROR": ("⁉️", "Couldn't read", "This file couldn't be analysed."),
}


def verdict_plain(verdict: str) -> Tuple[str, str, str]:
    """Return ``(icon, human_label, action)`` for a verdict, with a safe default."""
    return _VERDICT_PLAIN.get(verdict, ("•", verdict or "Unknown", ""))


def _hires_note(result: Dict[str, Any]) -> str:
    """A plain sentence for the fake-hi-res axis, or '' if it doesn't apply."""
    hv = result.get("hires_verdict", "")
    rate = result.get("suspected_original_rate") or 0
    from_rate = (
        f" from about {rate / 1000:.1f} kHz" if isinstance(rate, (int, float)) and rate else ""
    )
    if hv == "UPSAMPLED":
        return (
            f"It's sold as hi-res but was upsampled{from_rate}: the extra range is empty, "
            "so it holds no more detail than a CD."
        )
    if hv == "PADDED_DEPTH":
        return "It's labelled high bit-depth but only carries 16-bit audio — the extra bits are silent."
    if hv == "UPSAMPLED_AND_PADDED":
        return "It's fake hi-res on both counts: upsampled, and padded to a higher bit-depth it doesn't use."
    if hv == "GENUINE_HIRES":
        return "Genuine high-resolution: there's real detail above the CD range."
    return ""


def plain_explanation(result: Dict[str, Any]) -> str:
    """A friendly, jargon-free one-to-two sentence explanation of the verdict.

    Uses the verdict plus the most telling signals (the spectral cliff, the implied
    MP3 bitrate, the fake-hi-res axis) — never rule codes, points, Hz or dB. Meant
    for "easy mode" in the CLI and GUI.
    """
    verdict = result.get("verdict", "")
    cutoff = result.get("cutoff_freq") or 0
    bitrate = result.get("estimated_mp3_bitrate") or 0

    # The cliff/bitrate clause, when we have it — the single most intuitive evidence.
    cliff = ""
    if isinstance(cutoff, (int, float)) and 0 < cutoff < 21000:
        khz = cutoff / 1000.0
        if isinstance(bitrate, (int, float)) and bitrate > 0:
            cliff = (
                f" The sound stops dead at about {khz:.0f} kHz — the tell-tale wall of a "
                f"~{int(bitrate)} kbps MP3 re-saved as FLAC."
            )
        else:
            cliff = f" The high frequencies cut off sharply at about {khz:.0f} kHz."

    if verdict == "AUTHENTIC":
        base = "No signs of transcoding — this looks like genuine lossless audio."
    elif verdict == "WARNING":
        base = "A couple of mild oddities, but nothing conclusive. Most likely genuine."
    elif verdict == "SUSPICIOUS":
        base = "This shows the marks of a lossy original (an MP3 or AAC) saved into a FLAC." + cliff
    elif verdict == "FAKE_CERTAIN":
        base = (
            "Almost certainly a fake — lossless on the outside, but the audio already lost detail."
            + cliff
        )
    elif verdict == "NON_FLAC":
        base = "This isn't a lossless file at all; it only looks like one by its name."
    elif verdict == "ERROR":
        base = "This file couldn't be read for analysis."
    else:
        base = ""

    note = _hires_note(result)
    if note:
        base = f"{base}  {note}" if base else note
    return base.strip()
