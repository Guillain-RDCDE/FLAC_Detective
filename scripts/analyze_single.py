#!/usr/bin/env python3
"""
Script de test pour analyser UN SEUL fichier FLAC en détail
Affiche toutes les étapes de détection pour débuggage
"""

import sys
import subprocess
from pathlib import Path

# Installation des dépendances
def install_dependencies():
    required = ['numpy', 'scipy', 'mutagen', 'soundfile', 'matplotlib']
    missing = []
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"📦 Installation: {', '.join(missing)}")
        for pkg in missing:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 
                                 pkg, '--break-system-packages', '-q'])

install_dependencies()

import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq
import soundfile as sf
from mutagen.flac import FLAC
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif

def analyze_file_verbose(filepath: Path):
    """Analyse détaillée d'un fichier avec affichage de toutes les étapes"""
    
    print("=" * 80)
    print(f"🎵 ANALYSE DÉTAILLÉE : {filepath.name}")
    print("=" * 80)
    print()
    
    # 1. Métadonnées
    print("📋 MÉTADONNÉES")
    print("-" * 80)
    try:
        audio = FLAC(filepath)
        info = audio.info
        metadata_duration = info.length
        print(f"  Sample Rate    : {info.sample_rate} Hz")
        print(f"  Bit Depth      : {info.bits_per_sample} bits")
        print(f"  Channels       : {info.channels}")
        print(f"  Duration       : {metadata_duration:.1f} secondes")
        print(f"  Encodeur       : {audio.get('encoder', ['Unknown'])[0] if audio.get('encoder') else 'Unknown'}")
        
        # Vérification cohérence durée
        print()
        print("⏱️  VÉRIFICATION DURÉE (Critère FTF)")
        print("-" * 80)
        file_info = sf.info(filepath)
        real_duration = file_info.duration
        sample_rate = info.sample_rate
        
        metadata_samples = int(metadata_duration * sample_rate)
        real_samples = int(real_duration * sample_rate)
        diff_samples = abs(metadata_samples - real_samples)
        diff_ms = (diff_samples / sample_rate) * 1000
        
        print(f"  Durée métadonnées : {metadata_duration:.3f}s ({metadata_samples:,} samples)")
        print(f"  Durée réelle      : {real_duration:.3f}s ({real_samples:,} samples)")
        print(f"  Différence        : {diff_samples:,} samples ({diff_ms:.1f}ms)")
        
        if diff_samples <= 588:
            print(f"  Statut            : ✅ OK (tolérance normale)")
        elif diff_samples <= 44100:
            print(f"  Statut            : ⚠️  Léger décalage (à surveiller)")
        else:
            print(f"  Statut            : 🔴 DÉCALAGE IMPORTANT (suspect)")
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
    print()
    
    # 2. Analyse spectrale
    print("🔬 ANALYSE SPECTRALE (3 échantillons)")
    print("-" * 80)
    
    try:
        info = sf.info(filepath)
        total_duration = info.duration
        samplerate = info.samplerate
        
        num_samples = 3 if total_duration > 90 else 1
        sample_duration = min(30.0, total_duration / num_samples)
        
        fig, axes = plt.subplots(num_samples, 1, figsize=(12, 4*num_samples))
        if num_samples == 1:
            axes = [axes]
        
        cutoff_freqs = []
        energy_ratios = []
        
        for i in range(num_samples):
            print(f"\n  📍 Échantillon {i+1}/{num_samples}")
            
            # Position
            start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
            start_time = max(0, start_time)
            start_frame = int(start_time * samplerate)
            
            print(f"     Position: {start_time:.1f}s - {start_time + sample_duration:.1f}s")
            
            # Lecture
            data, _ = sf.read(filepath, 
                            start=start_frame,
                            frames=int(sample_duration * samplerate),
                            always_2d=True)
            
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            else:
                data = data[:, 0]
            
            # FFT
            window = signal.windows.hann(len(data))
            data_windowed = data * window
            fft_vals = rfft(data_windowed)
            fft_freq = rfftfreq(len(data_windowed), 1/samplerate)
            magnitude = np.abs(fft_vals)
            magnitude_db = 20 * np.log10(magnitude + 1e-10)
            
            # Détection de coupure
            cutoff_freq = detect_cutoff_verbose(fft_freq, magnitude_db)
            cutoff_freqs.append(cutoff_freq)
            
            # Ratio d'énergie
            energy_ratio = calculate_energy_ratio(fft_freq, magnitude)
            energy_ratios.append(energy_ratio)
            
            print(f"     Coupure détectée: {cutoff_freq:.0f} Hz")
            print(f"     Énergie >16kHz: {energy_ratio:.6f}")
            
            # Plot
            ax = axes[i]
            ax.plot(fft_freq / 1000, magnitude_db, linewidth=0.5, alpha=0.7)
            ax.axvline(cutoff_freq / 1000, color='red', linestyle='--', 
                      label=f'Coupure: {cutoff_freq:.0f} Hz')
            ax.axvline(16, color='orange', linestyle=':', alpha=0.5, label='16 kHz')
            ax.axvline(20, color='green', linestyle=':', alpha=0.5, label='20 kHz')
            ax.set_xlim(10, 24)
            ax.set_ylim(-120, 0)
            ax.set_xlabel('Fréquence (kHz)')
            ax.set_ylabel('Magnitude (dB)')
            ax.set_title(f'Échantillon {i+1} - Position {start_time:.1f}s')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_plot = filepath.parent / f"{filepath.stem}_analysis.png"
        plt.savefig(output_plot, dpi=150, bbox_inches='tight')
        print(f"\n  💾 Spectrogramme sauvegardé: {output_plot.name}")
        
        # Résultat final
        final_cutoff = max(cutoff_freqs)
        final_energy = max(energy_ratios)
        
        print()
        print("📊 RÉSULTAT FINAL")
        print("-" * 80)
        print(f"  Fréquence de coupure (max): {final_cutoff:.0f} Hz")
        print(f"  Ratio énergie >16kHz (max): {final_energy:.6f}")
        
        # Score
        score, reason = calculate_score(final_cutoff, final_energy)
        
        print()
        print("🎯 VERDICT")
        print("-" * 80)
        print(f"  Score: {score}% {'🟢' if score >= 90 else '🟡' if score >= 70 else '🟠' if score >= 50 else '🔴'}")
        print(f"  Raison: {reason}")
        print()
        
        if score >= 90:
            print("  ✅ FLAC AUTHENTIQUE - Très probablement lossless d'origine")
        elif score >= 70:
            print("  🟡 PROBABLEMENT AUTHENTIQUE - Quelques caractéristiques suspectes")
        elif score >= 50:
            print("  🟠 SUSPECT - Possiblement transcodé depuis MP3")
        else:
            print("  🔴 TRÈS SUSPECT - Probablement transcodé depuis MP3")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def detect_cutoff_verbose(frequencies: np.ndarray, magnitude_db: np.ndarray) -> float:
    """Détection de coupure avec logs"""
    high_freq_mask = frequencies > 15000
    if not np.any(high_freq_mask):
        return frequencies[-1]
    
    freq_high = frequencies[high_freq_mask]
    mag_high = magnitude_db[high_freq_mask]
    
    if len(mag_high) > 100:
        from scipy.ndimage import uniform_filter1d
        mag_smooth = uniform_filter1d(mag_high, size=100)
    else:
        mag_smooth = mag_high
    
    # Référence
    ref_mask = (freq_high >= 15000) & (freq_high <= 17000)
    if np.any(ref_mask):
        reference_energy = np.percentile(mag_smooth[ref_mask], 50)
    else:
        reference_energy = np.max(mag_smooth)
    
    cutoff_threshold = reference_energy - 40
    
    # Analyse par tranches
    tranche_size_hz = 500
    current_freq = 17000
    consecutive_low = 0
    
    while current_freq < freq_high[-1]:
        tranche_mask = (freq_high >= current_freq) & (freq_high < current_freq + tranche_size_hz)
        
        if np.any(tranche_mask):
            tranche_energy = np.percentile(mag_smooth[tranche_mask], 75)
            
            if tranche_energy < cutoff_threshold:
                consecutive_low += 1
                if consecutive_low >= 3:
                    return current_freq - tranche_size_hz
            else:
                consecutive_low = 0
        
        current_freq += tranche_size_hz
    
    return freq_high[-1]

def calculate_energy_ratio(frequencies: np.ndarray, magnitude: np.ndarray) -> float:
    """Calcul du ratio d'énergie >16kHz"""
    high_freq_idx = frequencies > 16000
    if not np.any(high_freq_idx):
        return 0
    
    tranche_energies = []
    for f_start in range(16000, int(frequencies[-1]), 1000):
        f_mask = (frequencies >= f_start) & (frequencies < f_start + 1000)
        if np.any(f_mask):
            tranche_energy = np.sum(magnitude[f_mask]**2)
            total_energy = np.sum(magnitude**2)
            tranche_energies.append(tranche_energy / total_energy if total_energy > 0 else 0)
    
    return np.mean(tranche_energies) if tranche_energies else 0

def calculate_score(cutoff_freq: float, energy_ratio: float) -> tuple:
    """Calcul du score avec logique intelligente"""
    score = 100
    reasons = []
    
    # Déterminer si le spectre est complet
    cutoff_is_full_spectrum = cutoff_freq >= 21000
    
    # Analyse de la coupure
    if cutoff_freq >= 21000:
        reasons.append(f"Spectre complet jusqu'à {cutoff_freq:.0f} Hz (excellent)")
    elif cutoff_freq >= 20000:
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (authentique)")
    elif cutoff_freq >= 19500:
        score -= 15
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (légèrement suspect)")
    elif cutoff_freq >= 19000:
        score -= 35
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (typique MP3 256-320k)")
    elif cutoff_freq >= 18000:
        score -= 55
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (typique MP3 192k)")
    elif cutoff_freq >= 16000:
        score -= 75
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (typique MP3 128k)")
    else:
        score -= 90
        reasons.append(f"Coupure à {cutoff_freq:.0f} Hz (très suspect)")
    
    # Analyse de l'énergie avec LOGIQUE INTELLIGENTE
    if cutoff_is_full_spectrum:
        # Spectre complet : énergie faible = mastering/style, pas transcodage
        if energy_ratio < 0.00001:
            reasons.append("Contenu ultra-aigu minimal (mastering ou style musical)")
            score -= 5  # Pénalité très légère
    else:
        # Spectre incomplet : énergie faible = SUSPECT
        if energy_ratio < 0.0001:
            score -= 25
            reasons.append("Absence d'énergie >16kHz (renforce suspicion)")
        elif energy_ratio < 0.001:
            score -= 15
            reasons.append("Très peu d'énergie >16kHz")
        elif energy_ratio < 0.005:
            score -= 5
            reasons.append("Énergie faible >16kHz")
    
    final_score = max(0, min(100, score))
    reason = " | ".join(reasons) if reasons else "Analyse normale"
    
    return final_score, reason

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 test_single_file.py <chemin_vers_fichier.flac>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"❌ Fichier introuvable: {filepath}")
        sys.exit(1)
    
    if filepath.suffix.lower() != '.flac':
        print(f"❌ Le fichier doit être un .flac")
        sys.exit(1)
    
    analyze_file_verbose(filepath)
