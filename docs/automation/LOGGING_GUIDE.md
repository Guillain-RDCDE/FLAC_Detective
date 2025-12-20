# Logging Configuration Guide

## Overview

FLAC Detective uses a centralized logging configuration system that provides:
- Configurable log levels with clear documentation
- Rich console output (when Rich library is available)
- File-based persistent logging
- Structured log formatting
- Easy integration across all modules

## Quick Start

### Basic Usage

```python
from flac_detective.logging_config import setup_logging, get_logger, LogLevel

# Setup logging (typically done once at application start)
log_file = setup_logging(
    output_dir=Path("./logs"),
    log_level=LogLevel.INFO
)

# Get a logger for your module
logger = get_logger(__name__)

# Use the logger
logger.info("Processing file...")
logger.warning("Unusual metadata detected")
logger.error("Failed to read file")
```

## Log Levels

FLAC Detective defines five log levels with clear use cases:

| Level | Value | Use Case | Examples |
|-------|-------|----------|----------|
| **DEBUG** | 10 | Detailed diagnostic information for developers | Cache operations, internal state, algorithm details |
| **INFO** | 20 | General informational messages about program flow | File processing, analysis results, progress updates |
| **WARNING** | 30 | Warnings about potential issues (non-blocking) | Missing metadata, unusual formats, quality degradation |
| **ERROR** | 40 | Serious problems that affect functionality | File access errors, corrupted files, analysis failures |
| **CRITICAL** | 50 | Critical errors that may cause termination | Unrecoverable errors, system-level failures |

## Configuration Options

### `setup_logging()`

The main configuration function with flexible options:

```python
setup_logging(
    output_dir: Optional[Path] = None,      # Where to save log files (default: current directory)
    log_level: int = LogLevel.INFO,         # Minimum level to capture
    enable_file_logging: bool = True,       # Create persistent log files
    enable_console_logging: bool = True,    # Output to terminal
    log_format: str = "...",                # Custom format string
    date_format: str = "%Y-%m-%d %H:%M:%S"  # Custom date format
)
```

### Examples

#### Debug Mode for Troubleshooting

```python
# Enable verbose logging for debugging
log_file = setup_logging(
    output_dir=Path("./debug_logs"),
    log_level=LogLevel.DEBUG
)
```

#### Console Only (No File Logging)

```python
# Quick testing without creating log files
setup_logging(enable_file_logging=False)
```

#### Custom Format

```python
# Minimal format for production
setup_logging(
    log_format="%(levelname)s - %(message)s",
    log_level=LogLevel.WARNING
)
```

## Dynamic Log Level Changes

You can change the log level at runtime:

```python
from flac_detective.logging_config import set_log_level, LogLevel

# Enable debug logging dynamically
set_log_level(LogLevel.DEBUG)

# Process some files...

# Return to normal logging
set_log_level(LogLevel.INFO)
```

## Module-Specific Loggers

Each module should get its own logger instance:

```python
# In your_module.py
from flac_detective.logging_config import get_logger

logger = get_logger(__name__)

def process_file(path):
    logger.info(f"Processing {path}")
    try:
        # ... processing logic ...
        logger.debug(f"Successfully processed {path}")
    except Exception as e:
        logger.error(f"Failed to process {path}: {e}", exc_info=True)
```

## Rich Console Output

When the Rich library is installed, FLAC Detective automatically uses enhanced console output with:
- Color-coded log levels
- Beautiful formatting
- Rich tracebacks with syntax highlighting
- Source code context in errors

To disable Rich and use standard output:

```python
# The system automatically falls back to standard logging
# if Rich is not installed. No configuration needed.
```

## Best Practices

### 1. Use Appropriate Log Levels

```python
# ✅ Good
logger.debug("Cache hit for file XYZ")           # Development info
logger.info("Analyzing 50 FLAC files")           # User-facing progress
logger.warning("Missing artist metadata")        # Non-critical issues
logger.error("Cannot read file: permission denied")  # Problems
logger.critical("Database connection lost")      # Fatal errors

# ❌ Bad
logger.info("x = 42, y = 13")                    # Too verbose for INFO
logger.error("File processing started")          # Not an error
```

### 2. Include Context

```python
# ✅ Good
logger.error(f"Failed to process {file_path}: {error}", exc_info=True)

# ❌ Bad
logger.error("Error occurred")
```

### 3. Use exc_info for Exceptions

```python
try:
    analyze_file(path)
except Exception as e:
    # Include full traceback
    logger.error(f"Analysis failed: {e}", exc_info=True)
```

### 4. Avoid Logging in Tight Loops

```python
# ❌ Bad - logs millions of times
for sample in audio_samples:
    logger.debug(f"Processing sample {sample}")

# ✅ Good - log summary
logger.debug(f"Processing {len(audio_samples)} samples")
```

## Integration with Existing Code

The centralized logging config is backward compatible. Existing code using `logging.getLogger()` directly will still work, but migrating to the centralized config provides:

1. Consistent log formatting across all modules
2. Centralized level management
3. Better documentation of log levels
4. Rich console output support

### Migration Example

Before:
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

After:
```python
from flac_detective.logging_config import get_logger

logger = get_logger(__name__)
# Level is managed centrally via setup_logging()
```

## Troubleshooting

### Logs Not Appearing

Check that logging is initialized:
```python
# This must be called before any logging occurs
setup_logging()
```

### Too Much/Too Little Output

Adjust the log level:
```python
# More output
set_log_level(LogLevel.DEBUG)

# Less output
set_log_level(LogLevel.WARNING)
```

### Duplicate Log Messages

Ensure `setup_logging()` is called only once:
```python
# ✅ Good - in main entry point
if __name__ == "__main__":
    setup_logging()
    # ... rest of code

# ❌ Bad - in every module
```

## File Naming Convention

Log files are automatically named with timestamps:
```
flac_detective_20250219_143052.log
flac_detective_20250219_150323.log
```

This prevents overwriting and makes it easy to track when issues occurred.
