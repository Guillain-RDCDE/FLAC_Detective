#!/usr/bin/env python3
"""
Check what mutagen.flac actually returns for duration
"""

from mutagen.flac import FLAC
from pathlib import Path
import soundfile as sf

FILES = [
    ("Banda lobourou", r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac"),
    ("Ma cherie", r"D:\FLAC\External\Clermont Music\CLE017 - Oumar Konaté - Live in America (2017)\03 - Oumar Konaté -  Ma cherie.flac"),
    ("Addoh (Reference)", r"D:\FLAC\External\Clermont Music\CLE009  - Oumar Konate - Addoh (2014)\01 - Oumar Konaté -  Addoh.flac"),
]

for name, filepath in FILES:
    print(f"\n{'='*80}")
    print(f"📋 {name}")
    print('='*80)
    
    p = Path(filepath)
    
    # Mutagen
    try:
        audio = FLAC(p)
        info = audio.info
        print(f"[MUTAGEN] info.length: {info.length} (type: {type(info.length).__name__})")
        print(f"[MUTAGEN] info.sample_rate: {info.sample_rate}")
        print(f"[MUTAGEN] info.samples: {info.samples}")
        print(f"[MUTAGEN] Calculated duration: {info.samples / info.sample_rate:.2f}s")
    except Exception as e:
        print(f"❌ Mutagen error: {e}")
    
    # SoundFile
    try:
        info_sf = sf.info(p)
        print(f"[SOUNDFILE] duration: {info_sf.duration:.2f}s")
        print(f"[SOUNDFILE] frames: {info_sf.frames}")
        print(f"[SOUNDFILE] samplerate: {info_sf.samplerate}")
    except Exception as e:
        print(f"❌ SoundFile error: {e}")
