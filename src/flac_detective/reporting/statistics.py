"""Calculs statistiques pour les rapports."""

from typing import Dict, List


def calculate_statistics(results: List[Dict]) -> Dict:
    """Calcule les statistiques globales des résultats.

    Args:
        results: Liste des résultats d'analyse.

    Returns:
        Dict avec les statistiques calculées.
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

    authentic = len([r for r in results if r["score"] >= 90])
    probably_auth = len([r for r in results if 70 <= r["score"] < 90])
    suspect = len([r for r in results if 50 <= r["score"] < 70])
    fake = len([r for r in results if r["score"] < 50])

    # Statistiques sur les problèmes de durée
    duration_issues = len([r for r in results if r.get("duration_mismatch")])
    duration_issues_critical = len(
        [r for r in results if r.get("duration_mismatch") and r.get("duration_diff", 0) > 44100]
    )

    # Statistiques sur les problèmes de qualité (Phase 1)
    clipping_issues = len([r for r in results if r.get("has_clipping", False)])
    dc_offset_issues = len([r for r in results if r.get("has_dc_offset", False)])
    corrupted_files = len([r for r in results if r.get("is_corrupted", False)])

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
        # Nouvelles statistiques de qualité
        "clipping_issues": clipping_issues,
        "clipping_issues_pct": f"{clipping_issues/total*100:.1f}%" if total > 0 else "0%",
        "dc_offset_issues": dc_offset_issues,
        "dc_offset_issues_pct": f"{dc_offset_issues/total*100:.1f}%" if total > 0 else "0%",
        "corrupted_files": corrupted_files,
        "corrupted_files_pct": f"{corrupted_files/total*100:.1f}%" if total > 0 else "0%",
    }


def filter_suspicious(results: List[Dict], threshold: int = 90) -> List[Dict]:
    """Filtre les fichiers suspects selon un seuil de score.

    Args:
        results: Liste des résultats d'analyse.
        threshold: Seuil de score (par défaut 90).

    Returns:
        Liste des résultats suspects (score < threshold).
    """
    return [r for r in results if r["score"] < threshold]
