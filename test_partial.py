"""Test sf_blocks_partial directly"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flac_detective.analysis.new_scoring.audio_loader import sf_blocks_partial

file_path = r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac"

print("Calling sf_blocks_partial()...")
data, sr, is_complete = sf_blocks_partial(file_path)

if data is None:
    print("Result: None")
else:
    print(f"Data: {len(data)} frames at {sr} Hz")
    print(f"Is complete: {is_complete}")
    print(f"Shape: {data.shape}")
