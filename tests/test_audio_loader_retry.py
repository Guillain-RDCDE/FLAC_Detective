"""Test script for audio loading retry mechanism."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flac_detective.analysis.new_scoring.audio_loader import load_audio_with_retry, is_temporary_decoder_error

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_is_temporary_decoder_error():
    """Test the temporary error detection function."""
    print("\n" + "="*60)
    print("Testing is_temporary_decoder_error()")
    print("="*60)
    
    test_cases = [
        ("flac decoder lost sync", True),
        ("decoder error occurred", True),
        ("sync error detected", True),
        ("invalid frame header", True),
        ("unexpected end of file", True),
        ("file not found", False),
        ("permission denied", False),
        ("out of memory", False),
        ("FLAC DECODER LOST SYNC", True),  # Case insensitive
    ]
    
    for error_msg, expected in test_cases:
        result = is_temporary_decoder_error(error_msg)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: '{error_msg}' -> {result} (expected {expected})")


def test_load_audio_with_retry():
    """Test the audio loading with retry."""
    print("\n" + "="*60)
    print("Testing load_audio_with_retry()")
    print("="*60)
    
    # Test with a non-existent file (should fail quickly)
    print("\n1. Testing with non-existent file:")
    audio, sr = load_audio_with_retry("non_existent_file.flac", max_attempts=2)
    if audio is None and sr is None:
        print("✅ PASS: Correctly returned None for non-existent file")
    else:
        print("❌ FAIL: Should have returned None")
    
    # If you have a test FLAC file, you can test it here
    # test_file = Path("path/to/test.flac")
    # if test_file.exists():
    #     print(f"\n2. Testing with real file: {test_file}")
    #     audio, sr = load_audio_with_retry(str(test_file))
    #     if audio is not None:
    #         print(f"✅ PASS: Loaded audio with shape {audio.shape} at {sr} Hz")
    #     else:
    #         print("❌ FAIL: Could not load valid file")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FLAC Detective - Audio Loader Retry Tests")
    print("="*60)
    
    test_is_temporary_decoder_error()
    test_load_audio_with_retry()
    
    print("\n" + "="*60)
    print("Tests completed!")
    print("="*60)
