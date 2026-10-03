"""Statistical calculations for reports."""

from typing import Dict, List

from .common import verdict_of

# (statistic name, result key) for every boolean per-file flag that is counted.
_FLAG_COUNTS = (
    ("duration_issues", "duration_mismatch"),
    ("clipping_issues", "has_clipping"),
    ("dc_offset_issues", "has_dc_offset"),
    ("corrupted_files", "is_corrupted"),
    ("silence_issues", "has_silence_issue"),
    ("fake_high_res", "is_fake_high_res"),
    ("upsampled_files", "is_upsampled"),
)

# Order of the counters in the returned dict (each followed by its "_pct" twin).
_COUNTER_ORDER = (
    "authentic",
    "probably_authentic",
    "suspect",
    "fake",
    "duration_issues",
    "duration_issues_critical",
    "clipping_issues",
    "dc_offset_issues",
    "corrupted_files",
    "silence_issues",
    "fake_high_res",
    "upsampled_files",
    "non_flac_files",
)


def _empty_statistics() -> Dict:
    return {
        "total": 0,
        "authentic": 0,
        "probably_authentic": 0,
        "suspect": 0,
        "fake": 0,
        "duration_issues": 0,
        "duration_issues_critical": 0,
        "clipping_issues": 0,
        "dc_offset_issues": 0,
        "corrupted_files": 0,
    }


def _verdict_counts(results: List[Dict]) -> Dict[str, int]:
    """Count files by their authoritative verdict.

    ``determine_verdict`` (new_scoring/constants.py) is the single source of
    truth; this module used to re-derive its own score cut points, which drifted
    from the verdict constants and could disagree with the JSON/console output.
    """
    verdicts = [verdict_of(r) for r in results]
    return {
        "authentic": verdicts.count("AUTHENTIC"),
        "probably_authentic": verdicts.count("WARNING"),
        "suspect": verdicts.count("SUSPICIOUS"),
        "fake": verdicts.count("FAKE_CERTAIN") + verdicts.count("NON_FLAC"),
    }


def _is_non_flac(r: Dict) -> bool:
    """A non-FLAC row: by verdict, or by the legacy score-100 + reason marker."""
    return r.get("verdict") == "NON_FLAC" or (
        r.get("score", 0) == 100 and "NON-FLAC FILE" in r.get("reason", "")
    )


def _pct(count: int, total: int) -> str:
    return f"{count/total*100:.1f}%"


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculates global statistics from results.

    Args:
        results: List of analysis results.

    Returns:
        Dict with calculated statistics: ``total``, then one counter per
        statistic and its ``<name>_pct`` string twin.
    """
    total = len(results)
    if total == 0:
        return _empty_statistics()

    counts: Dict[str, int] = dict(_verdict_counts(results))
    for name, key in _FLAG_COUNTS:
        counts[name] = sum(1 for r in results if r.get(key, False))
    counts["duration_issues_critical"] = sum(
        1 for r in results if r.get("duration_mismatch") and r.get("duration_diff", 0) > 44100
    )
    counts["non_flac_files"] = sum(1 for r in results if _is_non_flac(r))

    stats: Dict = {"total": total}
    for name in _COUNTER_ORDER:
        stats[name] = counts[name]
        stats[f"{name}_pct"] = _pct(counts[name], total)
    return stats
