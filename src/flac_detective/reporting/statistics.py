"""Statistical calculations for reports."""

from typing import Dict, List


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calculates global statistics from results.

    Args:
        results: List of analysis results.

    Returns:
        Dict with calculated statistics.
    """
    total = len(results)

    if total == 0:
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

    # NEW SCORING SYSTEM: higher score = more fake
    # Score < 30: AUTHENTIQUE
    # Score 30-49: DOUTEUX (probably authentic)
    # Score 50-79: FAKE_PROBABLE (suspect)
    # Score >= 80: FAKE_CERTAIN (fake)

    authentic = len([r for r in results if r.get("score", 0) < 30])
    probably_auth = len([r for r in results if 30 <= r.get("score", 0) < 50])
    suspect = len([r for r in results if 50 <= r.get("score", 0) < 80])
    fake = len([r for r in results if r.get("score", 0) >= 80])

    # Statistics on duration issues
    duration_issues = len([r for r in results if r.get("duration_mismatch")])
    duration_issues_critical = len(
        [r for r in results if r.get("duration_mismatch") and r.get("duration_diff", 0) > 44100]
    )

    # Statistics on quality issues (Phase 1)
    clipping_issues = len([r for r in results if r.get("has_clipping", False)])
    dc_offset_issues = len([r for r in results if r.get("has_dc_offset", False)])
    corrupted_files = len([r for r in results if r.get("is_corrupted", False)])

    # Phase 2
    silence_issues = len([r for r in results if r.get("has_silence_issue", False)])
    fake_high_res = len([r for r in results if r.get("is_fake_high_res", False)])
    upsampled_files = len([r for r in results if r.get("is_upsampled", False)])

    # Non-FLAC files (identified by verdict="NON_FLAC" or score=100 with NON-FLAC in reason)
    non_flac_files = len([r for r in results if r.get("verdict") == "NON_FLAC" or (r.get("score", 0) == 100 and "NON-FLAC FILE" in r.get("reason", ""))])

    return {
        "total": total,
        "authentic": authentic,
        "authentic_pct": f"{authentic/total*100:.1f}%" if total > 0 else "0%",
        "probably_authentic": probably_auth,
        "probably_authentic_pct": f"{probably_auth/total*100:.1f}%" if total > 0 else "0%",
        "suspect": suspect,
        "suspect_pct": f"{suspect/total*100:.1f}%" if total > 0 else "0%",
        "fake": fake,
        "fake_pct": f"{fake/total*100:.1f}%" if total > 0 else "0%",
        "duration_issues": duration_issues,
        "duration_issues_pct": f"{duration_issues/total*100:.1f}%" if total > 0 else "0%",
        "duration_issues_critical": duration_issues_critical,
        "duration_issues_critical_pct": (
            f"{duration_issues_critical/total*100:.1f}%" if total > 0 else "0%"
        ),
        # New quality statistics
        "clipping_issues": clipping_issues,
        "clipping_issues_pct": f"{clipping_issues/total*100:.1f}%" if total > 0 else "0%",
        "dc_offset_issues": dc_offset_issues,
        "dc_offset_issues_pct": f"{dc_offset_issues/total*100:.1f}%" if total > 0 else "0%",
        "corrupted_files": corrupted_files,
        "corrupted_files_pct": f"{corrupted_files/total*100:.1f}%" if total > 0 else "0%",
        # Phase 2
        "silence_issues": silence_issues,
        "silence_issues_pct": f"{silence_issues/total*100:.1f}%" if total > 0 else "0%",
        "fake_high_res": fake_high_res,
        "fake_high_res_pct": f"{fake_high_res/total*100:.1f}%" if total > 0 else "0%",
        "upsampled_files": upsampled_files,
        "upsampled_files_pct": f"{upsampled_files/total*100:.1f}%" if total > 0 else "0%",
        # Non-FLAC files
        "non_flac_files": non_flac_files,
        "non_flac_files_pct": f"{non_flac_files/total*100:.1f}%" if total > 0 else "0%",
    }


def filter_suspicious(results: List[Dict], threshold: int = 90) -> List[Dict]:
    """Filters suspicious files according to a score threshold.

    Args:
        results: List of analysis results.
        threshold: Score threshold (default 90).

    Returns:
        List of suspicious results (score < threshold).
    """
    return [r for r in results if r["score"] < threshold]
