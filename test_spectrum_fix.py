#!/usr/bin/env python3
"""
Test the fix on all three files
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

import logging
logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

from flac_detective.analysis.spectrum import analyze_spectrum

FILES = [
    ("Banda lobourou", r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac"),
    ("Ma cherie", r"D:\FLAC\External\Clermont Music\CLE017 - Oumar Konaté - Live in America (2017)\03 - Oumar Konaté -  Ma cherie.flac"),
    ("Addoh (Reference)", r"D:\FLAC\External\Clermont Music\CLE009  - Oumar Konate - Addoh (2014)\01 - Oumar Konaté -  Addoh.flac"),
]

print("="*100)
print("TESTING SPECTRUM FIX ON ALL THREE FILES")
print("="*100)

for name, filepath in FILES:
    print(f"\n{name}:")
    try:
        p = Path(filepath)
        cutoff, energy, std = analyze_spectrum(p, sample_duration=30.0)
        print(f"  ✅ Cutoff: {cutoff:.1f} Hz ({cutoff/1000:.1f}k Hz) | Energy >16k: {energy:.6f} | Std: {std:.1f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*100)
