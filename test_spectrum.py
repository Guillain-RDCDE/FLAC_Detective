"""Test spectrum analysis on partial data"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
os.environ['PYTHONIOENCODING'] = 'ascii'

from flac_detective.analysis.audio_cache import AudioCache
from flac_detective.analysis.spectrum import analyze_spectrum

file_path = Path(r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac")

print("Creating AudioCache...")
cache = AudioCache(file_path)

# Force load audio FIRST
audio, sr = cache.get_full_audio()
print("Audio loaded:", len(audio), "frames at", sr, "Hz")

# Then check if partial
print("Cache is_partial:", cache.is_partial())
print("Audio shape:", audio.shape)
print("Audio dtype:", audio.dtype)

print("\nAnalyzing spectrum...")
cutoff, energy_ratio, cutoff_std = analyze_spectrum(file_path, sample_duration=30.0, cache=cache)

print("Cutoff detected:", cutoff, "Hz")
print("Energy ratio:", energy_ratio)
print("Cutoff std:", cutoff_std)

if cutoff < 17000:
    print("\nSUCCESS: Cutoff correctly detected as MP3 (~16kHz)")
else:
    print("\nPROBLEM: Cutoff should be around 16kHz, got", cutoff)
