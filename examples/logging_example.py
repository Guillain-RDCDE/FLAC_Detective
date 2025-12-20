#!/usr/bin/env python3
"""Example demonstrating the centralized logging configuration.

This example shows how to use the logging_config module in your code.
"""

from pathlib import Path
from flac_detective.logging_config import setup_logging, get_logger, LogLevel, set_log_level


def example_basic_usage():
    """Example 1: Basic logging setup and usage."""
    print("\n" + "="*60)
    print("Example 1: Basic Logging Setup")
    print("="*60 + "\n")

    # Setup logging (typically done once at application start)
    log_file = setup_logging(
        output_dir=Path("./logs"),
        log_level=LogLevel.INFO
    )

    # Get a logger for this module
    logger = get_logger(__name__)

    # Use different log levels
    logger.debug("This is a DEBUG message (won't show - level is INFO)")
    logger.info("Processing 50 FLAC files")
    logger.warning("Missing artist metadata in file.flac")
    logger.error("Failed to read corrupted.flac")

    print(f"\nLog file created: {log_file}")


def example_debug_mode():
    """Example 2: Debug mode for troubleshooting."""
    print("\n" + "="*60)
    print("Example 2: Debug Mode")
    print("="*60 + "\n")

    # Enable debug logging for troubleshooting
    log_file = setup_logging(
        output_dir=Path("./logs"),
        log_level=LogLevel.DEBUG
    )

    logger = get_logger(__name__)

    # Now debug messages will appear
    logger.debug("Cache initialized with 100 slots")
    logger.debug("Loading file from cache: key=file123")
    logger.info("Analysis started")
    logger.debug("Spectral analysis: cutoff detected at 16kHz")

    print(f"\nDebug log file: {log_file}")


def example_dynamic_level():
    """Example 3: Dynamic log level changes."""
    print("\n" + "="*60)
    print("Example 3: Dynamic Log Level Changes")
    print("="*60 + "\n")

    # Start with INFO level
    setup_logging(log_level=LogLevel.INFO)
    logger = get_logger(__name__)

    logger.info("Starting analysis with INFO level")
    logger.debug("This won't show")

    # Switch to DEBUG for detailed troubleshooting
    print("\nSwitching to DEBUG level...")
    set_log_level(LogLevel.DEBUG)

    logger.debug("Now DEBUG messages appear!")
    logger.info("Processing continues...")

    # Back to WARNING for less noise
    print("\nSwitching to WARNING level...")
    set_log_level(LogLevel.WARNING)

    logger.info("This won't show anymore")
    logger.warning("But warnings still appear")


def example_exception_logging():
    """Example 4: Logging exceptions with tracebacks."""
    print("\n" + "="*60)
    print("Example 4: Exception Logging")
    print("="*60 + "\n")

    setup_logging(log_level=LogLevel.INFO)
    logger = get_logger(__name__)

    def risky_operation(filename):
        """Simulate a function that might fail."""
        if not filename.endswith('.flac'):
            raise ValueError(f"Invalid file type: {filename}")
        return f"Processed {filename}"

    # Good exception logging
    try:
        result = risky_operation("song.mp3")
    except Exception as e:
        # exc_info=True includes full traceback
        logger.error(f"Failed to process file: {e}", exc_info=True)

    # Success case
    try:
        result = risky_operation("song.flac")
        logger.info(f"Success: {result}")
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)


def example_console_only():
    """Example 5: Console-only logging (no file)."""
    print("\n" + "="*60)
    print("Example 5: Console-Only Logging")
    print("="*60 + "\n")

    # Disable file logging for quick testing
    setup_logging(
        enable_file_logging=False,
        log_level=LogLevel.INFO
    )

    logger = get_logger(__name__)

    logger.info("This only appears in console")
    logger.warning("No log file is created")


def example_module_logger():
    """Example 6: Module-specific logger usage."""
    print("\n" + "="*60)
    print("Example 6: Module-Specific Logger")
    print("="*60 + "\n")

    setup_logging(log_level=LogLevel.INFO)

    # Each module gets its own logger
    analyzer_logger = get_logger('flac_detective.analyzer')
    metadata_logger = get_logger('flac_detective.metadata')
    repair_logger = get_logger('flac_detective.repair')

    # Logs will show which module they came from
    analyzer_logger.info("Starting spectral analysis")
    metadata_logger.warning("Missing album tag")
    repair_logger.info("Repairing corrupted frame")


def example_best_practices():
    """Example 7: Logging best practices."""
    print("\n" + "="*60)
    print("Example 7: Best Practices")
    print("="*60 + "\n")

    setup_logging(log_level=LogLevel.DEBUG)
    logger = get_logger(__name__)

    # ✅ Good: Include context
    file_path = "/music/song.flac"
    logger.info(f"Processing {file_path}")

    # ✅ Good: Use appropriate levels
    cache_hit_count = 42
    logger.debug(f"Cache statistics: {cache_hit_count} hits")

    # ✅ Good: Log important state changes
    logger.info("Analysis mode: STRICT")

    # ✅ Good: Log before potentially long operations
    file_count = 1000
    logger.info(f"Starting batch analysis of {file_count} files")

    # ❌ Bad: Don't log in tight loops (shown for demonstration)
    # for i in range(1000):
    #     logger.debug(f"Processing sample {i}")  # Too verbose!

    # ✅ Good: Log summary instead
    logger.debug(f"Processed 1000 audio samples")

    # ✅ Good: Include error context
    try:
        # Simulated error
        raise IOError("Permission denied")
    except IOError as e:
        logger.error(f"Cannot access {file_path}: {e}", exc_info=True)


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("FLAC Detective - Logging Configuration Examples")
    print("="*60)

    # Run examples
    example_basic_usage()
    example_debug_mode()
    example_dynamic_level()
    example_exception_logging()
    example_console_only()
    example_module_logger()
    example_best_practices()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60 + "\n")

    print("Next steps:")
    print("1. Check the 'logs/' directory for generated log files")
    print("2. Read docs/LOGGING_GUIDE.md for complete documentation")
    print("3. Use get_logger(__name__) in your modules")
    print()


if __name__ == '__main__':
    main()
