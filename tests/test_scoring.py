"""Tests complets pour le module de scoring."""

import pytest
from flac_detective.analysis.scoring import calculate_score, THRESHOLDS


class TestScoring:
    """Tests de la logique de calcul de score."""

    @pytest.mark.parametrize(
        "cutoff,expected_score_range,expected_reason_part",
        [
            (22050, (100, 100), "Spectre complet"),
            (21000, (100, 100), "Spectre complet"),
            (20000, (100, 100), "authentique"),
            (19500, (85, 85), "légèrement suspect"),
            (19000, (65, 65), "MP3 256-320k"),
            (18000, (45, 45), "MP3 192k"),
            (16000, (25, 25), "MP3 128k"),
            (15000, (10, 10), "très suspect"),
        ],
    )
    def test_cutoff_frequencies(self, cutoff, expected_score_range, expected_reason_part):
        """Vérifie les scores pour différentes fréquences de coupure."""
        # Setup minimal
        energy = 0.1  # Énergie haute suffisante pour ne pas pénaliser
        metadata = {}
        duration = {"mismatch": False}

        score, reason = calculate_score(cutoff, energy, metadata, duration)

        assert expected_score_range[0] <= score <= expected_score_range[1]
        assert expected_reason_part in reason

    @pytest.mark.parametrize(
        "cutoff,energy,expected_penalty,expected_reason_part",
        [
            # Spectre complet (>= 21k)
            (22050, 0.000001, 5, "Contenu ultra-aigu minimal"),
            (22050, 0.1, 0, "Spectre complet"),
            # Spectre incomplet (< 21k)
            (20000, 0.00001, 25, "Absence d'énergie"),
            (20000, 0.0005, 15, "Très peu d'énergie"),
            (20000, 0.004, 5, "Énergie faible"),
            (20000, 0.1, 0, "Coupure à"),
        ],
    )
    def test_energy_ratio(self, cutoff, energy, expected_penalty, expected_reason_part):
        """Vérifie les pénalités liées au ratio d'énergie."""
        metadata = {}
        duration = {"mismatch": False}

        # Calculer le score de base pour ce cutoff
        base_score, _ = calculate_score(cutoff, 1.0, metadata, duration)
        
        # Calculer le score réel
        score, reason = calculate_score(cutoff, energy, metadata, duration)

        # Vérifier la pénalité
        assert score == max(0, base_score - expected_penalty)
        if expected_penalty > 0:
            assert expected_reason_part in reason

    @pytest.mark.parametrize(
        "diff_ms,expected_penalty",
        [
            (50, 0),    # Sous le seuil de 100ms
            (150, 10),  # > 100ms
            (1500, 20), # > 1000ms
        ],
    )
    def test_duration_mismatch(self, diff_ms, expected_penalty):
        """Vérifie les pénalités de durée."""
        cutoff = 22050
        energy = 0.1
        metadata = {}
        duration = {"mismatch": True, "diff_ms": diff_ms}

        score, reason = calculate_score(cutoff, energy, metadata, duration)
        
        # Score de base est 100
        assert score == 100 - expected_penalty
        if expected_penalty > 0:
            assert "durée" in reason.lower()

    @pytest.mark.parametrize(
        "metadata,expected_penalty,expected_reason_part",
        [
            ({"encoder": "LAME 3.99"}, 30, "Encodeur suspect"),
            ({"encoder": "Lavf mp3"}, 30, "Encodeur suspect"),
            ({"bit_depth": 14}, 20, "Bit depth suspect"),
            ({"bit_depth": 24}, 0, "Spectre complet"),  # Pas de pénalité
            ({"encoder": "reference libFLAC"}, 0, "Spectre complet"),
        ],
    )
    def test_suspicious_metadata(self, metadata, expected_penalty, expected_reason_part):
        """Vérifie les pénalités de métadonnées."""
        cutoff = 22050
        energy = 0.1
        duration = {"mismatch": False}

        score, reason = calculate_score(cutoff, energy, metadata, duration)
        
        assert score == max(0, 100 - expected_penalty)
        if expected_penalty > 0:
            assert expected_reason_part in reason

    def test_combined_penalties(self):
        """Vérifie que les pénalités s'accumulent correctement."""
        cutoff = 19000  # -35 (MP3 256)
        energy = 0.0005 # -15 (Très peu d'énergie)
        metadata = {"encoder": "LAME"} # -30
        duration = {"mismatch": True, "diff_ms": 1500} # -20

        # Total pénalités: 35 + 15 + 30 + 20 = 100
        # Score attendu: 0
        
        score, reason = calculate_score(cutoff, energy, metadata, duration)
        
        assert score == 0
        assert "MP3 256-320k" in reason
        assert "Très peu d'énergie" in reason
        assert "Encodeur suspect" in reason
        assert "Durée incohérente" in reason

    def test_score_clamping(self):
        """Vérifie que le score reste entre 0 et 100."""
        # Cas < 0
        score, _ = calculate_score(1000, 0, {"encoder": "LAME"}, {"mismatch": True, "diff_ms": 5000})
        assert score == 0

        # Cas > 100 (impossible avec la logique actuelle car max start est 100 et que des pénalités, mais bon)
        # Si on changeait la logique pour ajouter des bonus, ce test serait utile.
        # Ici on vérifie juste que le cas parfait reste à 100
        score, _ = calculate_score(24000, 1.0, {}, {})
        assert score == 100
