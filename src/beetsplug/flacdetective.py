"""Beets plugin: flag fake-lossless files (MP3->FLAC transcodes) in your library.

Adds a ``beet flacdetective`` command that runs FLAC Detective's spectral analysis
over the lossless files in a beets library, prints a verdict per file, and (by
default) stores the result as the flexible attributes ``flacdetective_verdict`` and
``flacdetective_score`` so you can query them afterwards, e.g.::

    beet flacdetective artist:Radiohead
    beet ls flacdetective_verdict:FAKE_CERTAIN
    beet ls flacdetective_score:55..

Enable it like any beets plugin (after ``pip install "flac-detective[beets]"``)::

    plugins: flacdetective

Optional config (all shown with their defaults)::

    flacdetective:
        sample_duration: 30      # seconds of audio analysed per file
        deep: no                 # run the ML rule on every file (slower)
        write: yes               # store flacdetective_* attributes
        auto: no                 # also analyse files as they are imported
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, cast

from beets import ui
from beets.dbcore import types
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from beets.util import displayable_path

# Lossless containers FLAC Detective can decode and judge. A lossy file (e.g. an
# MP3 or an AAC .m4a) carries no "is this a transcode?" question, so we skip it.
ANALYSABLE_FORMATS = {"FLAC", "WAV", "ALAC", "APE"}

# Verdicts that mean "worth a human look".
FLAGGED_VERDICTS = ("WARNING", "SUSPICIOUS", "FAKE_CERTAIN")

# Verdict -> (beets colour name, one-word gloss) for console output.
_VERDICT_STYLE = {
    "AUTHENTIC": ("text_success", "real lossless"),
    "WARNING": ("text_warning", "borderline"),
    "SUSPICIOUS": ("text_warning", "likely transcode"),
    "FAKE_CERTAIN": ("text_error", "transcode"),
    "ERROR": ("text_error", "analysis error"),
}

# Order verdicts worst-last so the summary reads naturally.
_SUMMARY_ORDER = ("FAKE_CERTAIN", "SUSPICIOUS", "WARNING", "AUTHENTIC", "ERROR")


def is_analysable(fmt: Optional[str]) -> bool:
    """Return True if a beets ``format`` is a lossless container we can analyse."""
    return fmt is not None and fmt.upper() in ANALYSABLE_FORMATS


class FlacDetectivePlugin(BeetsPlugin):
    """Detect MP3-to-FLAC transcodes inside a beets library."""

    item_types = {
        "flacdetective_verdict": types.STRING,
        "flacdetective_score": types.INTEGER,
    }

    def __init__(self) -> None:
        """Register config defaults and, if enabled, the import-time hook."""
        super().__init__()
        self.config.add(
            {
                "sample_duration": 30.0,
                "deep": False,
                "write": True,
                "auto": False,
            }
        )
        if self.config["auto"].get(bool):
            self.import_stages = [self._import_stage]

    # ------------------------------------------------------------------ command
    def commands(self) -> List[Subcommand]:
        """Return the ``flacdetective`` subcommand."""
        cmd = Subcommand(
            "flacdetective",
            help="detect MP3-to-FLAC transcodes in your library",
            aliases=("flacdet",),
        )
        cmd.parser.add_option(
            "-d",
            "--sample-duration",
            type="float",
            dest="sample_duration",
            help="seconds of audio to analyse per file (default: 30)",
        )
        cmd.parser.add_option(
            "--deep",
            action="store_true",
            dest="deep",
            default=False,
            help="run the ML rule on every file (slower; catches high-bitrate AAC/Vorbis)",
        )
        cmd.parser.add_option(
            "-W",
            "--no-write",
            action="store_false",
            dest="write",
            default=None,
            help="do not store flacdetective_* attributes on items",
        )
        cmd.parser.add_option(
            "-p",
            "--pretend",
            action="store_true",
            dest="pretend",
            default=False,
            help="show verdicts but change nothing (implies --no-write)",
        )
        cmd.func = self._run
        return [cmd]

    def _run(self, lib: Any, opts: Any, args: List[str]) -> None:
        """Analyse every matching lossless item and report verdicts."""
        write = self.config["write"].get(bool)
        if opts.write is not None:
            write = opts.write
        if opts.pretend:
            write = False

        analyzer = self._make_analyzer(opts)
        counts: Dict[str, int] = {}
        analysed = 0

        for item in lib.items(ui.decargs(args)):
            if not is_analysable(item.format):
                continue
            result = self._analyse_item(analyzer, item)
            if result is None:
                continue
            analysed += 1
            verdict = result["verdict"]
            counts[verdict] = counts.get(verdict, 0) + 1
            self._print_item(item, result)
            if write:
                item["flacdetective_verdict"] = verdict
                item["flacdetective_score"] = int(result["score"])
                item.store()

        self._print_summary(analysed, counts)

    # -------------------------------------------------------------- import hook
    def _import_stage(self, session: Any, task: Any) -> None:
        """Analyse freshly imported items and tag any suspected transcodes."""
        analyzer = self._make_analyzer(None)
        for item in task.imported_items():
            if not is_analysable(item.format):
                continue
            result = self._analyse_item(analyzer, item)
            if result is None:
                continue
            item["flacdetective_verdict"] = result["verdict"]
            item["flacdetective_score"] = int(result["score"])
            if result["verdict"] in ("SUSPICIOUS", "FAKE_CERTAIN"):
                self._log.warning(
                    "possible transcode: {0} ({1}, score {2})",
                    displayable_path(item.path),
                    result["verdict"],
                    result["score"],
                )

    # ----------------------------------------------------------------- helpers
    def _make_analyzer(self, opts: Any) -> Any:
        """Build a FLACAnalyzer honouring config plus any command-line overrides."""
        from flac_detective import FLACAnalyzer

        sample = self.config["sample_duration"].get(float)
        deep = self.config["deep"].get(bool)
        if opts is not None:
            if getattr(opts, "sample_duration", None):
                sample = opts.sample_duration
            if getattr(opts, "deep", False):
                deep = True
        return FLACAnalyzer(sample_duration=sample, deep=deep)

    def _analyse_item(self, analyzer: Any, item: Any) -> Optional[Dict[str, Any]]:
        """Run analysis for one item, returning its result dict or None on failure."""
        path = self._item_path(item)
        if not os.path.exists(path):
            self._log.warning("missing file: {0}", path)
            return None
        try:
            result: Dict[str, Any] = analyzer.analyze_file(path)
            return result
        except Exception as exc:  # stay resilient across a whole library
            self._log.warning("analysis failed for {0}: {1}", path, exc)
            return None

    @staticmethod
    def _item_path(item: Any) -> str:
        """Decode a beets item path (bytes) to a filesystem string."""
        raw = item.path
        if isinstance(raw, bytes):
            return raw.decode("utf-8", "surrogateescape")
        return str(raw)

    def _print_item(self, item: Any, result: Dict[str, Any]) -> None:
        """Print a single colourised verdict line."""
        verdict = result["verdict"]
        color, _gloss = _VERDICT_STYLE.get(verdict, ("text_highlight_minor", ""))
        tag = ui.colorize(cast(Any, color), f"{verdict:<13}")
        line = f"{tag} {int(result['score']):>3}  {displayable_path(item.path)}"
        bitrate = result.get("estimated_mp3_bitrate")
        if verdict in FLAGGED_VERDICTS and bitrate:
            line += f"  (~{bitrate} kbps source)"
        ui.print_(line)

    def _print_summary(self, analysed: int, counts: Dict[str, int]) -> None:
        """Print the run summary line."""
        if not analysed:
            ui.print_("FLAC Detective: no analysable lossless files matched the query.")
            return
        parts = []
        for verdict in _SUMMARY_ORDER:
            if counts.get(verdict):
                color = _VERDICT_STYLE[verdict][0]
                parts.append(ui.colorize(cast(Any, color), f"{counts[verdict]} {verdict}"))
        ui.print_(f"FLAC Detective: analysed {analysed} file(s) — " + ", ".join(parts))
