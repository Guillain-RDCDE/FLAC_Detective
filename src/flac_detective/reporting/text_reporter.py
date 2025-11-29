"""Génération de rapports texte avec formatage ASCII."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .statistics import calculate_statistics, filter_suspicious

logger = logging.getLogger(__name__)


class TextReporter:
    """Générateur de rapports texte avec formatage ASCII."""

    def __init__(self):
        """Initialise le générateur de rapports."""
        self.width = 100  # Largeur du rapport

    def _header(self, title: str) -> str:
        """Génère un en-tête formaté.

        Args:
            title: Titre de la section.

        Returns:
            En-tête formaté.
        """
        border = "═" * self.width
        padding = (self.width - len(title) - 2) // 2
        return f"\n{border}\n{' ' * padding} {title}\n{border}\n"

    def _section(self, title: str) -> str:
        """Génère un titre de section.

        Args:
            title: Titre de la section.

        Returns:
            Titre formaté.
        """
        return f"\n{'─' * self.width}\n  {title}\n{'─' * self.width}\n"

    def _table_row(self, *columns: str, widths: list[int] | None = None) -> str:
        """Génère une ligne de tableau.

        Args:
            *columns: Colonnes à afficher.
            widths: Largeurs des colonnes (optionnel).

        Returns:
            Ligne formatée.
        """
        if widths is None:
            widths = [20, 10, 10, 15, 45]

        formatted_cols = []
        for col, width in zip(columns, widths):
            col_str = str(col)
            if len(col_str) > width:
                col_str = col_str[: width - 3] + "..."
            formatted_cols.append(col_str.ljust(width))

        return "  " + " │ ".join(formatted_cols)

    def _score_icon(self, score: int) -> str:
        """Retourne une icône basée sur le score.

        Args:
            score: Score de 0 à 100.

        Returns:
            Icône ASCII.
        """
        if score >= 90:
            return "✓✓✓"  # Authentique
        elif score >= 70:
            return "✓✓ "  # Probablement authentique
        elif score >= 50:
            return "✓  "  # Suspect
        else:
            return "✗✗✗"  # Fake

    def _score_label(self, score: int) -> str:
        """Retourne un label basé sur le score.

        Args:
            score: Score de 0 à 100.

        Returns:
            Label textuel.
        """
        if score >= 90:
            return "AUTHENTIC"
        elif score >= 70:
            return "PROB. AUTH."
        elif score >= 50:
            return "SUSPICIOUS"
        else:
            return "FAKE"

    def generate_report(self, results: list[dict[str, Any]], output_file: Path) -> None:
        """Génère un rapport texte complet.

        Args:
            results: Liste des résultats d'analyse.
            output_file: Chemin du fichier de sortie.
        """
        logger.info(f"Génération du rapport texte : {output_file}")

        # Calcul des statistiques
        stats = calculate_statistics(results)
        suspicious = filter_suspicious(results, threshold=90)

        # Construction du rapport
        report_lines = []

        # En-tête principal
        report_lines.append(self._header("🔍 FLAC DETECTIVE - ANALYSIS REPORT"))
        report_lines.append(f"\n  Date : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        report_lines.append(f"  Files analyzed : {stats['total']}\n")

        # Statistiques globales
        report_lines.append(self._section("📊 GLOBAL STATISTICS"))
        report_lines.append(f"\n  ✓✓✓ Authentic (≥90%)          : {stats['authentic']:>4} files")
        report_lines.append(
            f"  ✓✓  Probable auth. (≥70%)     : {stats['probably_authentic']:>4} files"
        )
        report_lines.append(f"  ✓   Suspicious (≥50%)         : {stats['suspect']:>4} files")
        report_lines.append(f"  ✗✗✗ Fakes (<50%)              : {stats['fake']:>4} files")
        report_lines.append(f"\n  ⚠️  Duration issues           : {stats['duration_issues']:>4} files")
        report_lines.append(
            f"      (critical >1s)            : {stats['duration_issues_critical']:>4} files"
        )
        report_lines.append(f"\n  🔊 Clipping issues            : {stats['clipping_issues']:>4} files")
        report_lines.append(f"  📊 DC offset issues           : {stats['dc_offset_issues']:>4} files")
        report_lines.append(f"  🔇 Abnormal silence (>2s)     : {stats['silence_issues']:>4} files")
        report_lines.append(f"  📉 Fake High-Res (padding)    : {stats['fake_high_res']:>4} files")
        report_lines.append(f"  📈 Upsampling detected        : {stats['upsampled_files']:>4} files")
        report_lines.append(f"  💥 Corrupted files            : {stats['corrupted_files']:>4} files\n"
        )

        # Taux de qualité
        if stats["total"] > 0:
            quality_rate = (stats["authentic"] / stats["total"]) * 100
            report_lines.append(f"  📈 Quality rate : {quality_rate:.1f}%\n")

        # Fichiers suspects (score < 90%)
        if suspicious:
            report_lines.append(self._section(f"⚠️  SUSPICIOUS FILES ({len(suspicious)} files)"))
            report_lines.append("")

            # En-tête du tableau
            widths = [5, 10, 10, 15, 60]
            report_lines.append(
                self._table_row("Icon", "Score", "Cutoff", "Duration", "File", widths=widths)
            )
            report_lines.append("  " + "─" * (sum(widths) + 3 * (len(widths) - 1)))

            # Trier par score croissant (les pires en premier)
            sorted_suspicious = sorted(suspicious, key=lambda x: x["score"])

            for result in sorted_suspicious:
                icon = self._score_icon(result["score"])
                score = f"{result['score']}%"
                cutoff = f"{result['cutoff_freq'] / 1000:.1f} kHz"

                # Indicateur de durée
                if result.get("duration_mismatch", False):
                    duration = f"⚠️ {result.get('duration_diff', 0):.0f}ms"
                else:
                    duration = "OK"

                filename = result["filename"]

                report_lines.append(
                    self._table_row(icon, score, cutoff, duration, filename, widths=widths)
                )

            report_lines.append("")

        # Détails des fichiers authentiques (optionnel, commenté par défaut)
        # authentics = [r for r in results if r["score"] >= 90]
        # if authentics:
        #     report_lines.append(self._section(f"✅ AUTHENTIC FILES ({len(authentics)} files)"))
        #     report_lines.append("\n  (List available on request)\n")

        # Recommandations
        report_lines.append(self._section("💡 RECOMMENDATIONS"))
        report_lines.append("")

        if stats["fake"] > 0:
            report_lines.append(
                f"  ⚠️  {stats['fake']} file(s) identified as FAKE (score < 50%)"
            )
            report_lines.append("      → Check source and consider deleting\n")

        if stats["suspect"] > 0:
            report_lines.append(
                f"  ⚠️  {stats['suspect']} file(s) suspicious (score 50-69%)"
            )
            report_lines.append("      → Critical listening recommended\n")

        if stats["duration_issues_critical"] > 0:
            report_lines.append(
                f"  ⚠️  {stats['duration_issues_critical']} file(s) with critical duration issues"
            )
            report_lines.append(
                "      → Use repair module: python -m flac_detective.repair\n"
            )

        if stats["authentic"] == stats["total"]:
            report_lines.append("  ✅ All files are authentic! High quality collection.\n")

        # Pied de page
        report_lines.append("\n" + "═" * self.width)
        report_lines.append("  Generated by FLAC Detective v0.1")
        report_lines.append("  https://github.com/your-repo/flac-detective")

        report_lines.append("═" * self.width + "\n")

        # Écriture du fichier
        report_text = "\n".join(report_lines)
        output_file.write_text(report_text, encoding="utf-8")

        logger.info(f"✅ Rapport généré : {output_file}")
        logger.info(f"   Taille : {len(report_text)} caractères")
