"""Debug test - Check what's happening"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Disable unicode in output
os.environ['PYTHONIOENCODING'] = 'ascii'

from flac_detective.analysis.analyzer import FLACAnalyzer

file_path = Path(r"D:\FLAC\External\Clermont Music\CLE018 - Hama Sankare - Ballebe (2018)\02 - Hama Sankare -  Banda lobourou.flac")

analyzer = FLACAnalyzer()
result = analyzer.analyze_file(file_path)

# Print only safe ASCII
print("Verdict:", result['verdict'])
print("Score:", result['score'])
print("Cutoff:", result['cutoff_freq'], "Hz")
print("Sample rate:", result['sample_rate'])
print("Is corrupted:", result['is_corrupted'])
print("Partial analysis:", result.get('is_partial_analysis', False))

# Success check
if result['verdict'] in ['FAKE_CERTAIN', 'SUSPICIOUS']:
    print("\nSUCCESS: File detected as FAKE/SUSPICIOUS")
elif result['verdict'] == 'AUTHENTIC':
    print("\nPROBLEM: File detected as AUTHENTIC (should be FAKE)")
    print("Cutoff should be around 16kHz for MP3 128k")
else:
    print("\nERROR: File marked as", result['verdict'])
