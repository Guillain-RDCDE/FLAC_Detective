#!/usr/bin/env python3
"""
Test script to analyze A SINGLE FLAC file in detail
Displays all detection steps for debugging
"""

import sys
import subprocess
from pathlib import Path

# Install dependencies
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
matplotlib.use('Agg')  # Non-interactive backend

def analyze_file_verbose(filepath: Path):
    """Detailed analysis of a file with display of all steps"""
    
    print("=" * 80)
    print(f"🎵 DETAILED ANALYSIS : {filepath.name}")
    print("=" * 80)
    print()
    
    # 1. Metadata
    print("📋 METADATA")
    print("-" * 80)
    try:
        audio = FLAC(filepath)
        info = audio.info
        metadata_duration = info.length
        print(f"  Sample Rate    : {info.sample_rate} Hz")
        print(f"  Bit Depth      : {info.bits_per_sample} bits")
        print(f"  Channels       : {info.channels}")
        print(f"  Duration       : {metadata_duration:.1f} secondes")
        print(f"  Encoder        : {audio.get('encoder', ['Unknown'])[0] if audio.get('encoder') else 'Unknown'}")
        
        # Duration consistency check
        print()
        print("⏱️  DURATION CHECK (FTF Criterion)")
        print("-" * 80)
        file_info = sf.info(filepath)
        real_duration = file_info.duration
        sample_rate = info.sample_rate
        
        metadata_samples = int(metadata_duration * sample_rate)
        real_samples = int(real_duration * sample_rate)
        diff_samples = abs(metadata_samples - real_samples)
        diff_ms = (diff_samples / sample_rate) * 1000
        
        print(f"  Metadata duration : {metadata_duration:.3f}s ({metadata_samples:,} samples)")
        print(f"  Real duration     : {real_duration:.3f}s ({real_samples:,} samples)")
        print(f"  Difference        : {diff_samples:,} samples ({diff_ms:.1f}ms)")
        
        if diff_samples <= 588:
            print(f"  Status            : ✅ OK (normal tolerance)")
        elif diff_samples <= 44100:
            print(f"  Status            : ⚠️  Slight mismatch (monitor)")
        else:
            print(f"  Status            : 🔴 SIGNIFICANT MISMATCH (suspicious)")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()
    
    # 2. Spectral analysis
    print("🔬 SPECTRAL ANALYSIS (3 samples)")
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
            print(f"\n  📍 Sample {i+1}/{num_samples}")
            
            # Position
            start_time = (total_duration / (num_samples + 1)) * (i + 1) - sample_duration / 2
            start_time = max(0, start_time)
            start_frame = int(start_time * samplerate)
            
            print(f"     Position: {start_time:.1f}s - {start_time + sample_duration:.1f}s")
            
            # Read
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
            
            # Cutoff detection
            cutoff_freq = detect_cutoff_verbose(fft_freq, magnitude_db)
            cutoff_freqs.append(cutoff_freq)
            
            # Energy ratio
            energy_ratio = calculate_energy_ratio(fft_freq, magnitude)
            energy_ratios.append(energy_ratio)
            
            print(f"     Detected cutoff: {cutoff_freq:.0f} Hz")
            print(f"     Energy >16kHz: {energy_ratio:.6f}")
            
            # Plot
            ax = axes[i]
            ax.plot(fft_freq / 1000, magnitude_db, linewidth=0.5, alpha=0.7)
            ax.axvline(cutoff_freq / 1000, color='red', linestyle='--', 
                      label=f'Cutoff: {cutoff_freq:.0f} Hz')
            ax.axvline(16, color='orange', linestyle=':', alpha=0.5, label='16 kHz')
            ax.axvline(20, color='green', linestyle=':', alpha=0.5, label='20 kHz')
            ax.set_xlim(10, 24)
            ax.set_ylim(-120, 0)
            ax.set_xlabel('Frequency (kHz)')
            ax.set_ylabel('Magnitude (dB)')
            ax.set_title(f'Sample {i+1} - Position {start_time:.1f}s')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        output_plot = filepath.parent / f"{filepath.stem}_analysis.png"
        plt.savefig(output_plot, dpi=150, bbox_inches='tight')
        print(f"\n  💾 Spectrogram saved: {output_plot.name}")
        
        # Final result
        final_cutoff = max(cutoff_freqs)
        final_energy = max(energy_ratios)
        
        print()
        print("📊 FINAL RESULT")
        print("-" * 80)
        print(f"  Cutoff frequency (max): {final_cutoff:.0f} Hz")
        print(f"  Energy ratio >16kHz (max): {final_energy:.6f}")
        
        # Score
        score, reason = calculate_score(final_cutoff, final_energy)
        
        print()
        print("🎯 VERDICT")
        print("-" * 80)
        print(f"  Score: {score}% {'🟢' if score >= 90 else '🟡' if score >= 70 else '🟠' if score >= 50 else '🔴'}")
        print(f"  Reason: {reason}")
        print()
        
        if score >= 90:
            print("  ✅ AUTHENTIC FLAC - Very likely original lossless")
        elif score >= 70:
            print("  🟡 PROBABLY AUTHENTIC - Some suspicious characteristics")
        elif score >= 50:
            print("  🟠 SUSPICIOUS - Possibly transcoded from MP3")
        else:
            print("  🔴 VERY SUSPICIOUS - Probably transcoded from MP3")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def detect_cutoff_verbose(frequencies: np.ndarray, magnitude_db: np.ndarray) -> float:
    """Cutoff detection with logs"""
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
    
    # Reference
    ref_mask = (freq_high >= 15000) & (freq_high <= 17000)
    if np.any(ref_mask):
        reference_energy = np.percentile(mag_smooth[ref_mask], 50)
    else:
        reference_energy = np.max(mag_smooth)
    
    cutoff_threshold = reference_energy - 40
    
    # Slice analysis
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
    """Energy ratio calculation >16kHz"""
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
    """Score calculation with smart logic"""
    score = 100
    reasons = []
    
    # Determine if spectrum is full
    cutoff_is_full_spectrum = cutoff_freq >= 21000
    
    # Cutoff analysis
    if cutoff_freq >= 21000:
        reasons.append(f"Full spectrum up to {cutoff_freq:.0f} Hz (excellent)")
    elif cutoff_freq >= 20000:
        reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (authentic)")
    elif cutoff_freq >= 19500:
        score -= 15
        reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (slightly suspicious)")
    elif cutoff_freq >= 19000:
        score -= 35
        reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (typical MP3 256-320k)")
    elif cutoff_freq >= 18000:
        score -= 55
        reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (typical MP3 192k)")
    elif cutoff_freq >= 16000:
        score -= 75
        reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (typical MP3 128k)")
    else:
        score -= 90
        reasons.append(f"Cutoff at {cutoff_freq:.0f} Hz (very suspicious)")
    
    # Energy analysis with SMART LOGIC
    if cutoff_is_full_spectrum:
        # Full spectrum: low energy = mastering/style, not transcoding
        if energy_ratio < 0.00001:
            reasons.append("Minimal ultra-high content (mastering or musical style)")
            score -= 5  # Very slight penalty
    else:
        # Incomplete spectrum: low energy = SUSPICIOUS
        if energy_ratio < 0.0001:
            score -= 25
            reasons.append("No energy >16kHz (reinforces suspicion)")
        elif energy_ratio < 0.001:
            score -= 15
            reasons.append("Very low energy >16kHz")
        elif energy_ratio < 0.005:
            score -= 5
            reasons.append("Low energy >16kHz")
    
    final_score = max(0, min(100, score))
    reason = " | ".join(reasons) if reasons else "Normal analysis"
    
    return final_score, reason

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 test_single_file.py <path_to_flac_file>")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)
    
    if filepath.suffix.lower() != '.flac':
        print(f"❌ File must be a .flac")
        sys.exit(1)
    
    analyze_file_verbose(filepath)
