"""Test what load_audio_with_retry returns"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flac_detective.analysis.new_scoring.audio_loader import load_audio_with_retry

file_path = r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac"

print("Calling load_audio_with_retry(always_2d=True)...")
data, sr = load_audio_with_retry(file_path, always_2d=True)

if data is None:
    print("Result: None (load failed)")
else:
    print(f"Result: {len(data)} frames at {sr} Hz")
    print(f"Shape: {data.shape}")
