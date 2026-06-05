# Repair Examples

This directory contains example scripts demonstrating FLAC file repair functionality.

## Example Scripts

### `test_repair_corrupted.py`
Interactive script to test repair on corrupted FLAC files.

**Usage:**
```bash
python examples/repair/test_repair_corrupted.py
```

**Features:**
- Two-phase testing (dry run + actual repair)
- User confirmation before replacing files
- Automatic backup creation (`.corrupted.bak`)
- Detailed progress logging
- Metadata preservation validation

**What it does:**
1. **Phase 1:** Tests repair without modifying source files
2. **Phase 2:** Asks for confirmation, then repairs and replaces source files
3. Creates backups of corrupted originals
4. Validates repaired files pass `flac --test`

### `check_metadata.py`
Validates metadata preservation after repair.

**Usage:**
```bash
python examples/repair/check_metadata.py
```

**Purpose:**
- Compares metadata between repaired and backup files
- Validates all tags are preserved (TITLE, ARTIST, ALBUM, etc.)
- Checks album art preservation
- Generates detailed comparison report

## Repair Process

The repair function (`repair_flac_file`) follows these steps:

1. **Extract metadata** - Saves all tags and album art
2. **Decode with error recovery** - `flac --decode --decode-through-errors`
3. **Re-encode to FLAC** - `flac --best`
4. **Restore metadata** - Writes back all tags and pictures
5. **Verify integrity** - `flac --test`
6. **Replace source** (optional) - Creates backup and replaces original

## Example Output

```
Attempting to repair Iceland (part 2).flac
  Step 0: Extracting metadata
  ✅ Extracted 10 tags, 1 picture(s)
  Step 1: Decoding with error recovery
  ✅ Decoded to WAV (97.5 MB)
  Step 2: Re-encoding to FLAC
  Step 3: Restoring metadata
  ✅ Metadata restored successfully
  Step 4: Verifying repaired FLAC
  ✅ Successfully repaired and verified (56.4 MB)
  💾 Creating backup: file.flac.corrupted.bak
  🔄 Replacing original file with repaired version
  ✅ Original file replaced successfully
```

## Safety Features

- **Automatic backups** - Original corrupted files saved as `.corrupted.bak`
- **Metadata preservation** - All tags and album art maintained
- **Integrity verification** - Repaired files validated with `flac --test`
- **User confirmation** - Interactive prompt before replacing files
- **Graceful degradation** - Partial repairs attempted when full repair fails
