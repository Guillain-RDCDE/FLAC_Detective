#!/usr/bin/env python3
"""Build set A of fd-exchange-v3 — the half FLAC Detective chooses, freezes and keys.

Protocol: ``ml/exchange/V3_PROTOCOL_2026-08-29.md`` (registered 2026-08-29,
accepted by Provir 2026-08-30 including the symmetric change and both additions).
This script implements the two conditions that are ours to enforce mechanically.

**Condition 6 — documentary admission.** This is the part v2 did not have, and
the reason v2's key was wrong in three of 59: the fetcher selected on licence and
collection and never read the taper's source line. So no file enters the genuine
stratum without provenance. Every candidate item's ``source``/``lineage``/
``notes`` metadata is read BEFORE the audio is downloaded, and each is classified:

    analog_chain        an analog capture with no codec anywhere in the chain
                        (vinyl, cassette, reel, FM/AM line-in, analog SBD)
    digital_documented  a documented lossless digital chain (DAT, CDR, WAV,
                        24-bit, "> flac" with nothing lossy upstream)
    lossy_documented    a codec name appears (MP3, MP2, ATRAC/MiniDisc, AAC,
                        Ogg, Opus, WMA, "lossy") — EXCLUDED, it is not genuine
    unstated            the lineage does not settle the question — EXCLUDED

Only the first two are admitted, and the key records which, per row, in a
``basis`` field. An excluded item is recorded too, with its reason, so the
selection itself is auditable rather than asserted.

**Condition 5 — the band-limited stratum.** At least a quarter of the sources
must be honestly lossless with nothing much above ~16 kHz: old masters, vinyl
transfers, AM/FM-era material. These are the hardest false positives in this
space and neither existing set covers them. The classification is measured on
the genuine excerpt itself (``analyze_spectrum``), never assumed from the
lineage text — but a file only reaches that measurement if its lineage already
admitted it, so a transcode cannot enter through the band-limited door.

No overlap with v1 or v2: v2's 59 archive.org identifiers are excluded by name,
and v1's sources were EAC rips of a private CD library, disjoint from ``etree``
by construction. A content-hash check against the frozen v2 audio runs anyway.

Arms, per the protocol — the v2 arms that carried information, plus the one v2's
adjudication exposed:

    genuine, mp3_320, mp3_V0, aac_ff256, aacmf_256, opus_256, vorbis_q8, mp2_256

``mp2_256`` is MPEG-1 **Layer II** (libtwolame): 32 subbands, no MDCT stage. v2's
0197 was a taper-documented MP2 chain that sat at the null for the MP3 families
in BOTH engines, because neither was looking for that filterbank. Carried as a
miss it misprices both; carried as an arm it becomes a measurement.

Usage — four phases, each resumable, nothing destructive::

    python ml/v3_build_set_a.py --discover --out C:/Users/loutr/fd-v3-setA
    python ml/v3_build_set_a.py --fetch    --out C:/Users/loutr/fd-v3-setA
    python ml/v3_build_set_a.py --arms     --out C:/Users/loutr/fd-v3-setA
    python ml/freeze_exchange_set.py --corpus C:/Users/loutr/fd-v3-setA/corpus \\
        --out C:/Users/loutr/fd-exchange-v3-setA --name fd-exchange-v3-setA

The audio and the key never enter the repository; only this script, the
provenance ledger and the manifest do.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from build_audit_corpus import Codec, make_excerpt, sha256, transcode  # noqa: E402

_UA = {"User-Agent": "flac-detective-research/1.1 (blind exchange v3, set A)"}

# The v3 arms. mp2_256 is the new one; see the module docstring.
ARMS: Tuple[Codec, ...] = (
    Codec("mp3_320", "libmp3lame", "mp3", ("-b:a", "320k")),
    Codec("mp3_V0", "libmp3lame", "mp3", ("-q:a", "0")),
    Codec("aac_ff256", "aac", "m4a", ("-b:a", "256k")),
    Codec("aacmf_256", "aac_mf", "m4a", ("-b:a", "256k")),
    Codec("opus_256", "libopus", "opus", ("-b:a", "256k")),
    Codec("vorbis_q8", "libvorbis", "ogg", ("-q:a", "8")),
    # MPEG-1 Layer II via libtwolame — a real Layer II encoder, not ffmpeg's
    # native one, for the same reason aacmf sits beside aac_ff: an arm should
    # test a codec, not one implementation of it.
    Codec("mp2_256", "libtwolame", "mp2", ("-b:a", "256k")),
)

DEFAULT_QUERY = "collection:etree AND format:(Flac)"

# Condition 5 needs material that is honestly lossless with nothing much above
# ~16 kHz, and the head of etree is modern 24-bit taper digital: the first crawl
# returned 3 analog chains out of 100 items. These queries go looking for the
# stratum instead of hoping for it — old shows, and shows whose own metadata
# names an analog carrier. The lineage classifier still has the last word, and
# the cutoff is still measured on the audio rather than believed from the text.
BAND_LIMITED_QUERIES = (
    "collection:etree AND format:(Flac) AND date:[1965-01-01 TO 1982-12-31]",
    "collection:etree AND format:(Flac) AND date:[1983-01-01 TO 1990-12-31]",
    'collection:etree AND format:(Flac) AND source:(cassette OR "master cassette")',
    "collection:etree AND format:(Flac) AND source:(reel OR reels)",
    "collection:etree AND format:(Flac) AND source:(FM OR broadcast OR " "pre-FM)",
    "collection:etree AND format:(Flac) AND source:(vinyl OR LP)",
    # The Great 78 Project. etree turned out not to hold the stratum: its analog
    # chains are modern 24/96 transfers of cassettes, and tape hiss reaches
    # Nyquist, so the measured content edge sat at 19-22 kHz on 49 of the first
    # 50 sources. A shellac 78 is band-limited by physics — content stops around
    # 8-10 kHz — it is documented analog end to end, and it is exactly the file
    # that makes a cutoff-led detector shout "transcode" at something honest.
    "collection:georgeblood AND format:(Flac)",
)

TARGET_SOURCES = 36
BAND_LIMITED_TARGET = 12  # a third, comfortably above the registered quarter
# The band-limited bar, on the CONTENT edge (see content_edge_hz). 17 kHz sits
# just above an FM broadcast's 15 kHz ceiling and a good cassette deck's ~16 kHz,
# and well below the 19-22 kHz every modern digital taper recording reaches.
BAND_LIMITED_HZ = 17_000.0

# The roll-off used to build the band-limited stratum, calibrated against the
# engine's OWN eyes rather than against a spectrum plot: six cascaded 2-pole
# sections at 14 kHz. Measured on a source that read 22,050 Hz unfiltered,
# ``detect_cutoff`` returns 19,000 at 4th order, 17,250 at 8th and 16,500 at
# 12th — a gentle analog-style roll-off is simply not visible to a detector, and
# a stratum the detector cannot see is not the stratum the condition asks for.
# ffmpeg's lowpass takes poles 1 or 2 only; asking for 4 fails with "Result too
# large", which looks like a path-length error and is not one.
BAND_LIMIT_FILTER = ",".join(["lowpass=f=14000:poles=2"] * 6)

# Codec names in a lineage line. Matched case-insensitively on word boundaries,
# because "MD" inside "MDCT" or a band called "AAC" would otherwise exclude a
# lawful item — and because v2 shipped an MP2 chain as genuine for want of
# exactly this list.
LOSSY_PATTERNS = (
    r"\bmp3\b",
    r"\bmp2\b",
    r"\bmpeg\s*layer\b",
    r"\blame\b",
    r"\bfraunhofer\b",
    r"\batrac\b",
    r"\bminidisc\b",
    r"\bmini-disc\b",
    r"\bmd\b",
    r"\bmz-[a-z0-9]+\b",
    r"\baac\b",
    r"\bm4a\b",
    r"\bogg\b",
    r"\bvorbis\b",
    r"\bopus\b",
    r"\bwma\b",
    r"\bmusepack\b",
    r"\bmpc\b",
    r"\bshorten-lossy\b",
    r"\blossy\b",
    r"\bhi-?md\b",
    r"\bportadisc\b",  # writes MP2
)

ANALOG_PATTERNS = (
    r"\bvinyl\b",
    r"\blp\b",
    r"\b45\s*rpm\b",
    r"\bturntable\b",
    r"\bcartridge\b",
    r"\bcassette\b",
    r"\btape\b",
    r"\breel\b",
    r"\bnakamichi\b",
    r"\bteac\b",
    r"\bfm\b",
    r"\bam\s*radio\b",
    r"\bline-?in\b",
    r"\banalog\b",
    r"\banalogue\b",
    r"\bpre-?fm\b",
    r"\bbroadcast\b",
    # The Great 78 Project's own vocabulary. "source: 78" is terse, and it is
    # also decisive: a shellac disc has no codec anywhere in its chain.
    r"\b78\s*rpm\b",
    r"\bshellac\b",
    r"\bgramophone\b",
    r"\bvictrola\b",
    r"\bacoustic recording\b",
    r"(?<![\d.])78(?![\d.])",
)

DIGITAL_PATTERNS = (
    r"\bdat\b",
    r"\bcdr?\b",
    r"\bcd-?r\b",
    r"\bwav\b",
    r"\bwave\b",
    r"\baiff\b",
    r"\b24\s*bit\b",
    r"\b16\s*bit\b",
    r"\bshn\b",
    r"\bshorten\b",
    r"\bflac\b",
    r"\bsbd\b",
    r"\bsoundboard\b",
    r"\bdsd\b",
    r"\bpcm\b",
)


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return bytes(r.read())


def _lineage_text(meta: dict) -> str:
    """Every field a taper might write the chain into, joined."""
    md = meta.get("metadata", {}) or {}
    parts: List[str] = []
    for key in ("source", "lineage", "taper", "transferer", "notes", "description", "title"):
        value = md.get(key)
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif value:
            parts.append(str(value))
    return " \n ".join(parts)


def classify_lineage(text: str) -> Tuple[str, str]:
    """(basis, why) for one item's lineage text. See the module docstring."""
    if not text.strip():
        return "unstated", "no source/lineage/notes field at all"
    low = text.lower()
    for pattern in LOSSY_PATTERNS:
        hit = re.search(pattern, low)
        if hit:
            return "lossy_documented", f"codec named in lineage: {hit.group(0)!r}"
    analog = [p for p in ANALOG_PATTERNS if re.search(p, low)]
    digital = [p for p in DIGITAL_PATTERNS if re.search(p, low)]
    if analog and not digital:
        return "analog_chain", f"analog chain, no codec: {analog[:3]}"
    if analog and digital:
        return (
            "analog_chain",
            f"analog capture into a documented digital chain: {analog[:2]} + {digital[:2]}",
        )
    if digital:
        return "digital_documented", f"documented lossless digital chain: {digital[:3]}"
    return "unstated", "lineage names neither an analog nor a documented digital chain"


def _performer_key(identifier: str) -> str:
    """A key that collapses the sides of one series into one source.

    Great 78 identifiers read ``78_<title>_<performer>_gbiaNNNNNNN``; etree ones
    read ``<band><date>.<gear>``. Both collapse on the field that names WHO is
    playing: the performer for a 78, the band-and-date prefix for a taper
    recording. Two sides of the same lesson series share a performer; two shows
    by the same band on different dates do not.
    """
    if identifier.startswith("78_"):
        parts = identifier.split("_")
        return parts[-2].lower() if len(parts) >= 3 else identifier.lower()
    return identifier.split(".")[0].lower()


def v2_identifiers(repo: Path) -> set:
    """The 59 archive.org items v2 used, so v3 cannot reuse one."""
    key = (
        repo / "Temp" / "fd-exchange-v2-return-flacdetective" / "fd-exchange-v2-2026-08-LABELS.json"
    )
    if not key.exists():
        return set()
    labels = json.loads(key.read_text(encoding="utf-8"))["labels"]
    out = set()
    for entry in labels.values():
        slug = entry.get("source_slug", "")
        # "001-TenD2005-07-16-flac16-TenD2005-07-16t01announcem" -> "tend2005-07-16"
        body = re.sub(r"^\d+-", "", slug)
        body = re.split(r"-flac16|-flac24|-shnf|-mk4|-neumann|-nak|-ck-|-bg4", body)[0]
        if body:
            out.add(body.lower())
    return out


def discover(
    out: Path,
    want: int,
    repo: Path,
    query: str = DEFAULT_QUERY,
    counts_toward: Tuple[str, ...] = ("analog_chain", "digital_documented"),
) -> int:
    """Phase 1: find items whose lineage settles the question, before downloading."""
    ledger_path = out / "provenance_ledger.json"
    ledger: Dict[str, dict] = {}
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    excluded_v2 = v2_identifiers(repo)
    print(f"{len(excluded_v2)} identifiants v2 exclus d'office", flush=True)

    # In band-limited mode only the analog chains count toward the target: the
    # digital stratum is already full, and a crawl that stops because of it
    # would never look for the stratum that is missing.
    admitted = [k for k, v in ledger.items() if v["basis"] in counts_toward]
    # Sort orders vary so the crawl does not keep re-reading the same head of the
    # distribution (the lesson from ml/fetch_wild_authentic.py).
    sorts = [
        "downloads desc",
        "downloads asc",
        "addeddate desc",
        "reviewdate desc",
        "titleSorter asc",
    ]
    page = 1
    while len(admitted) < want and page <= 40:
        sort = sorts[page % len(sorts)]
        params = [
            ("q", query),
            ("fl[]", "identifier"),
            ("rows", "50"),
            ("page", str(page)),
            ("sort[]", sort),
            ("output", "json"),
        ]
        url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params)
        try:
            docs = json.loads(_get(url))["response"]["docs"]
        except Exception as exc:
            print(f"  recherche page {page} echouee: {exc}", flush=True)
            page += 1
            continue
        for doc in docs:
            ident = doc["identifier"]
            if ident in ledger:
                continue
            if any(v2 in ident.lower() for v2 in excluded_v2 if len(v2) > 6):
                ledger[ident] = {"basis": "excluded_v2", "why": "source used in fd-exchange-v2"}
                continue
            try:
                meta = json.loads(_get(f"https://archive.org/metadata/{ident}"))
            except Exception as exc:
                ledger[ident] = {"basis": "unreadable", "why": str(exc)[:80]}
                continue
            text = _lineage_text(meta)
            basis, why = classify_lineage(text)
            flacs = [
                f for f in meta.get("files", []) if f.get("name", "").lower().endswith(".flac")
            ]
            ledger[ident] = {
                "basis": basis,
                "why": why,
                "lineage": text[:600],
                "n_flac": len(flacs),
                "licence": (meta.get("metadata", {}) or {}).get("licenseurl", ""),
            }
            if basis in counts_toward and flacs:
                admitted.append(ident)
                print(f"  [{len(admitted)}/{want}] {ident} — {basis}: {why}", flush=True)
            time.sleep(0.3)  # polite
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(ledger, indent=1), encoding="utf-8")
        page += 1

    counts: Dict[str, int] = {}
    for entry in ledger.values():
        counts[entry["basis"]] = counts.get(entry["basis"], 0) + 1
    print(f"\nledger: {len(ledger)} items examines -> {counts}")
    print(f"admis: {len(admitted)}")
    return 0


def _pick_track(meta_files: List[dict]) -> Optional[dict]:
    """One FLAC track per item: the first whose size is sane (10-120 MB)."""
    flacs = [f for f in meta_files if f.get("name", "").lower().endswith(".flac")]
    sized = []
    for f in flacs:
        try:
            size = int(f.get("size", 0))
        except (TypeError, ValueError):
            continue
        if 10_000_000 <= size <= 120_000_000:
            sized.append((size, f))
    if not sized:
        return None
    sized.sort(key=lambda x: x[0])
    return sized[len(sized) // 2][1]  # the median-sized track, not the shortest


def fetch(out: Path, want: int) -> int:  # noqa: C901
    """Phase 2: download one track per admitted item and cut the 60 s excerpt."""
    ledger = json.loads((out / "provenance_ledger.json").read_text(encoding="utf-8"))
    # Analog chains first: they are the scarce stratum (43 found against 76
    # digital), and condition 5 wants at least a quarter of the set band-limited.
    # Within a class the order is deterministic, so a resumed fetch continues the
    # same selection rather than a new one.
    admitted = sorted(
        (
            (k, v)
            for k, v in ledger.items()
            if v["basis"] in ("analog_chain", "digital_documented") and v.get("n_flac")
        ),
        key=lambda kv: (kv[1]["basis"] != "analog_chain", kv[0]),
    )
    # One item per PERFORMER, not merely one file per item. The first 78 rpm
    # fetch returned sixteen sources that were sixteen sides of the same Italian
    # language course, same series, same transfer, same room: one source wearing
    # sixteen identifiers. The v2 README promises "independent recordings", and a
    # set that quietly breaks its own promise is worse than a smaller set.
    seen_performer = set()
    diverse = []
    for ident, entry in admitted:
        performer = _performer_key(ident)
        if performer in seen_performer:
            continue
        seen_performer.add(performer)
        diverse.append((ident, entry))
    dropped = len(admitted) - len(diverse)
    if dropped:
        print(f"{dropped} items ecartes comme doublons d'interprete/serie", flush=True)
    admitted = diverse
    corpus = out / "corpus" / "authentic"
    corpus.mkdir(parents=True, exist_ok=True)
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    have = {p.stem.split("__")[0] for p in corpus.glob("*.flac")}

    done = len(have)
    for ident, entry in admitted:
        if done >= want:
            break
        if ident in have:
            continue
        try:
            meta = json.loads(_get(f"https://archive.org/metadata/{ident}"))
        except Exception as exc:
            print(f"  {ident}: metadata KO ({exc})", flush=True)
            continue
        track = _pick_track(meta.get("files", []))
        if track is None:
            entry["fetch"] = "no track in the 10-120 MB band"
            continue
        name = track["name"]
        url = f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}"
        local = raw / f"{ident}__{Path(name).name}"
        if not local.exists():
            try:
                data = _get(url, timeout=300)
                local.write_bytes(data)
            except Exception as exc:
                print(f"  {ident}: telechargement KO ({exc})", flush=True)
                continue
        dst = corpus / f"{ident}__{Path(name).stem}.flac"
        if make_excerpt(local, dst):
            entry["track"] = name
            entry["excerpt_sha256"] = sha256(dst)
            done += 1
            print(f"  [{done}/{want}] {ident} <- {name}", flush=True)
        else:
            entry["fetch"] = "excerpt failed"
        (out / "provenance_ledger.json").write_text(json.dumps(ledger, indent=1), encoding="utf-8")
    print(f"\n{done} extraits authentiques dans {corpus}")
    return 0


def content_edge_hz(path: Path, drop_db: float = 40.0) -> float:
    """Highest frequency whose level is still within ``drop_db`` of the midband.

    NOT ``detect_cutoff``. The first stratification used it and returned **0
    band-limited files out of 50**, because an analog transfer has tape hiss all
    the way to Nyquist: there is no cutoff to find, and the detector duly
    returned the top of its scan band (46-48 kHz on the 96 kHz transfers). The
    stratum the protocol asks for is about CONTENT — "nothing much above ~16
    kHz" — and hiss is not content. The 40 dB rule is the one ``analysis/hires``
    already uses for its content edge, kept identical so two parts of this
    project do not measure the same idea two ways.
    """
    import numpy as np
    import soundfile as sf
    from scipy.signal import welch

    audio, rate = sf.read(str(path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    freqs, power = welch(audio, rate, nperseg=16384)
    db = 10 * np.log10(power + 1e-20)
    reference = float(np.median(db[(freqs >= 1000) & (freqs <= 8000)]))
    above = np.where(db >= reference - drop_db)[0]
    return float(freqs[above[-1]]) if len(above) else float("nan")


def standardise(out: Path) -> int:
    """Phase 2b: every source to 44.1 kHz / 16-bit before anything is derived.

    The fetched excerpts arrived at 44.1, 48, 96 and even 192 kHz. Left alone,
    the container becomes a label twice over. First directly: v2 shipped its
    Opus arm at 48 kHz on 100 % of files while the genuine arm was 78 % at 44.1,
    so every Opus file was identifiable without decoding a sample. Second, and
    worse for THIS set: MP3 and Layer II cannot encode above 48 kHz, so a 96 kHz
    source would come back band-limited to 20 kHz in some arms and full-band in
    others — the hard question the band-limited stratum exists to ask would be
    answered by the sample rate instead of by the audio.

    So the sources are made uniform first and every arm inherits it. 44.1/16 is
    also how these recordings actually circulate when someone passes one off as
    lossless, which is the situation being modelled.
    """
    import subprocess

    import soundfile

    authentic = out / "corpus" / "authentic"
    converted = 0
    for f in sorted(authentic.glob("*.flac")):
        info = soundfile.info(str(f))
        if info.samplerate == 44100 and info.subtype == "PCM_16":
            continue
        tmp = f.with_suffix(".std.flac")
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(f),
                "-map",
                "0:a:0",
                "-map_metadata",
                "-1",
                "-ar",
                "44100",
                "-sample_fmt",
                "s16",
                "-c:a",
                "flac",
                str(tmp),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"  ECHEC {f.name}: {proc.stderr[-160:]}")
            return 1
        tmp.replace(f)
        converted += 1
    rates = {}
    for f in sorted(authentic.glob("*.flac")):
        info = soundfile.info(str(f))
        rates[(info.samplerate, info.subtype)] = rates.get((info.samplerate, info.subtype), 0) + 1
    print(f"{converted} fichiers convertis | distribution finale: {rates}")
    return 0 if list(rates) == [(44100, "PCM_16")] else 1


def stratify(out: Path) -> int:
    """Phase 3: measure which excerpts are band-limited, on the audio itself."""
    ledger = json.loads((out / "provenance_ledger.json").read_text(encoding="utf-8"))
    corpus = out / "corpus" / "authentic"
    by_file = {v.get("excerpt_file"): k for k, v in ledger.items() if v.get("excerpt_file")}
    band, full = [], []
    for f in sorted(corpus.glob("*.flac")):
        ident = by_file.get(f.name, f.stem.split("__")[0])
        edge = content_edge_hz(f)
        entry = ledger.get(ident, {})
        entry["content_edge_hz"] = round(edge, 1)
        entry["stratum"] = "band_limited" if edge < BAND_LIMITED_HZ else "full_band"
        ledger[ident] = entry
        (band if edge < BAND_LIMITED_HZ else full).append((ident, edge))
    (out / "provenance_ledger.json").write_text(json.dumps(ledger, indent=1), encoding="utf-8")
    print(
        f"band-limited (bord de contenu <{BAND_LIMITED_HZ:.0f} Hz): {len(band)} | full-band: {len(full)}"
    )
    for ident, edge in sorted(band, key=lambda x: x[1])[:20]:
        print(f"  {edge:8.0f} Hz  {ident}")
    if len(band) < BAND_LIMITED_TARGET:
        print(
            f"ATTENTION: {len(band)} band-limited pour une cible de {BAND_LIMITED_TARGET} "
            "(condition 5: au moins un quart). Relancer --discover --band-limited puis --fetch."
        )
    return 0


def bandlimit(out: Path, want: int = BAND_LIMITED_TARGET) -> int:
    """Phase 3c: the band-limited stratum, built and DISCLOSED rather than found.

    What was measured first, and why this phase exists at all. 68 sources were
    fetched under documentary admission, deliberately weighted toward analog
    lineages, and then two crawls went looking specifically for the stratum:
    etree's cassette/reel/FM/vinyl queries, then the Great 78 Project. **One of
    the 68 measured band-limited.** Not because the lineages were wrong — they
    are cassettes, audience reels and shellac 78s — but because every one of
    them was transferred at 24/96 with its own noise, and tape hiss and shellac
    surface noise reach Nyquist. Three instruments were tried and all three
    agreed: ``detect_cutoff`` (21-48 kHz), a -40 dB content edge (19-22 kHz on
    67 of 68), and a p90-minus-p50 dynamics edge (Nyquist on everything, because
    clicks are broadband transients). **By a detector's own eyes these files are
    not band-limited**, so they are not the population the condition is about.

    That is worth stating to Provir as a finding rather than hiding as a
    shortfall: the hardest false positives in this space are hard to *collect*,
    which is probably why nobody benchmarks them.

    So the stratum is built, from admitted genuine sources, with a documented
    analog-style roll-off — and it is labelled ``band_limited_synthetic`` in the
    key so that its rows can be scored apart from everything else. The file
    remains genuine and lossless; nothing lossy touches it. What it models is a
    master whose content stops around 15 kHz, which is exactly the question the
    condition asks: does the engine convict an honest file for ending early?
    """
    import subprocess

    ledger = json.loads((out / "provenance_ledger.json").read_text(encoding="utf-8"))
    authentic = out / "corpus" / "authentic"
    by_file = {v.get("excerpt_file"): k for k, v in ledger.items() if v.get("excerpt_file")}
    pool = [
        f
        for f in sorted(authentic.glob("*.flac"))
        if ledger.get(by_file.get(f.name, ""), {}).get("stratum") == "full_band"
    ]
    made = 0
    for src in pool:
        if made >= want:
            break
        ident = by_file.get(src.name, src.stem.split("__")[0])
        if ledger.get(ident, {}).get("stratum") == "band_limited_synthetic":
            continue
        # A short temporary name in the same directory, then a replace: the
        # source names are already near the Windows path limit (the Great 78
        # identifiers are 100+ characters) and appending to them fails with
        # "Result too large". The stratum lives in the ledger, not in a filename.
        dst = src.parent / "_bl_tmp.flac"
        # Two cascaded 2-pole sections at 15 kHz — a 4th-order roll-off, not a
        # brickwall, so the file reads like an analog-limited master rather than
        # like a codec cut. ffmpeg's lowpass takes poles 1 or 2 only; asking for
        # 4 fails with "Result too large", which is not a path-length problem
        # however much it looks like one.
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(src),
                "-map",
                "0:a:0",
                "-map_metadata",
                "-1",
                "-af",
                BAND_LIMIT_FILTER,
                "-ar",
                "44100",
                "-sample_fmt",
                "s16",
                "-c:a",
                "flac",
                str(dst),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"  ECHEC lowpass {src.name}: {proc.stderr[-160:]}")
            return 1
        dst.replace(src)
        dst = src
        entry = dict(ledger.get(ident, {}))
        entry["stratum"] = "band_limited_synthetic"
        entry["band_limit_filter"] = BAND_LIMIT_FILTER
        entry["content_edge_hz"] = round(content_edge_hz(dst), 1)
        ledger[ident] = entry
        made += 1
        print(f"  [{made}/{want}] {ident} -> bord {entry['content_edge_hz']:.0f} Hz", flush=True)
    (out / "provenance_ledger.json").write_text(json.dumps(ledger, indent=1), encoding="utf-8")
    print(f"{made} sources band-limited construites et declarees")
    return 0


def select(out: Path) -> int:
    """Phase 3b: keep exactly the registered composition, park the rest.

    The protocol asks for ~36 sources with at least a quarter band-limited. More
    are fetched than are needed, because the stratum is decided by the MEASURED
    cutoff and not by the lineage text, so which candidate lands where is not
    known until the audio exists. Selection is deterministic (sorted by
    identifier within each stratum) so a re-run reproduces the same set, and
    nothing is deleted — the unused excerpts move to ``corpus/_unused`` and stay
    auditable.
    """
    ledger = json.loads((out / "provenance_ledger.json").read_text(encoding="utf-8"))
    authentic = out / "corpus" / "authentic"
    unused = out / "corpus" / "_unused"
    unused.mkdir(parents=True, exist_ok=True)

    by_file = {v.get("excerpt_file"): k for k, v in ledger.items() if v.get("excerpt_file")}
    band, full = [], []
    for f in sorted(authentic.glob("*.flac")):
        entry = ledger.get(by_file.get(f.name, ""), {})
        stratum = entry.get("stratum")
        if stratum is None:
            print(f"  {f.name}: pas de stratum — lancer --stratify d'abord")
            return 1
        (band if stratum.startswith("band_limited") else full).append(f)

    n_band = min(len(band), BAND_LIMITED_TARGET)
    keep = set(band[:n_band]) | set(full[: TARGET_SOURCES - n_band])
    for f in sorted(authentic.glob("*.flac")):
        if f not in keep:
            f.rename(unused / f.name)

    kept_band = sum(1 for f in keep if f in set(band))
    print(
        f"retenu: {len(keep)} sources ({kept_band} band-limited, {len(keep) - kept_band} full-band)"
    )
    print(f"parque: {len(list(unused.glob('*.flac')))} sous {unused}")
    if len(keep) < TARGET_SOURCES:
        print(f"ATTENTION: {len(keep)} < {TARGET_SOURCES} — relancer --fetch")
    if kept_band * 4 < len(keep):
        print(f"ATTENTION: {kept_band}/{len(keep)} band-limited, sous le quart de la condition 5")
    return 0


def arms(out: Path) -> int:
    """Phase 4: the seven lossy arms, one directory each."""
    corpus = out / "corpus"
    sources = sorted((corpus / "authentic").glob("*.flac"))
    if not sources:
        print("aucun extrait authentique — lancer --fetch d'abord")
        return 1
    total = len(sources) * len(ARMS)
    done = 0
    for codec in ARMS:
        for src in sources:
            dst = corpus / "fake" / codec.name / src.name
            result = transcode((src, dst, codec))
            done += 1
            if result is None:
                print(f"  ECHEC {codec.name} sur {src.name}")
                return 1
            if done % 25 == 0:
                print(f"  {done}/{total}", flush=True)
    print(f"\n{done} fichiers de bras ecrits sous {corpus / 'fake'}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--want", type=int, default=TARGET_SOURCES)
    ap.add_argument("--discover", action="store_true")
    ap.add_argument(
        "--band-limited",
        action="store_true",
        help="discover with the targeted queries for the band-limited stratum",
    )
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--standardise", action="store_true")
    ap.add_argument("--stratify", action="store_true")
    ap.add_argument("--bandlimit", action="store_true")
    ap.add_argument("--select", action="store_true")
    ap.add_argument("--arms", action="store_true")
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parent.parent
    args.out.mkdir(parents=True, exist_ok=True)

    if args.discover:
        if args.band_limited:
            for query in BAND_LIMITED_QUERIES:
                print(f"=== {query}", flush=True)
                discover(args.out, BAND_LIMITED_TARGET, repo, query, ("analog_chain",))
            return 0
        return discover(args.out, args.want, repo)
    if args.fetch:
        return fetch(args.out, args.want)
    if args.standardise:
        return standardise(args.out)
    if args.stratify:
        return stratify(args.out)
    if args.bandlimit:
        return bandlimit(args.out)
    if args.select:
        return select(args.out)
    if args.arms:
        return arms(args.out)
    ap.error("choisir une phase: --discover / --fetch / --stratify / --select / --arms")
    return 2


if __name__ == "__main__":
    sys.exit(main())
