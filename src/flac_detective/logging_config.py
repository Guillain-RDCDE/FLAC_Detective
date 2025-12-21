"""Centralized logging configuration for FLAC Detective.

This module provides a unified logging setup for the entire application with:
- Configurable log levels
- Rich console output (when available)
- File-based logging for persistence
- Structured log formatting
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Try to import Rich for beautiful console output
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.theme import Theme

    # Custom theme for FLAC Detective
    custom_theme = Theme(
        {
            "info": "dim cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "fake": "bold red",
            "suspicious": "bold yellow",
            "authentic": "bold green",
        }
    )

    console = Console(theme=custom_theme)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


class LogLevel:
    """Documented log levels for FLAC Detective.

    Attributes:
        DEBUG: Detailed diagnostic information for developers.
               Used for troubleshooting, cache operations, internal state.

        INFO: General informational messages about program flow.
              Used for file processing, analysis results, progress updates.

        WARNING: Warnings about potential issues that don't prevent execution.
                 Used for missing metadata, unusual file formats, degraded quality.

        ERROR: Error messages for serious problems.
               Used for file access errors, corrupted files, analysis failures.

        CRITICAL: Critical errors that may cause program termination.
                  Used for unrecoverable errors, system issues.
    """

    DEBUG = logging.DEBUG  # 10
    INFO = logging.INFO  # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR  # 40
    CRITICAL = logging.CRITICAL  # 50


def setup_logging(
    output_dir: Optional[Path] = None,
    log_level: int = LogLevel.INFO,
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    date_format: str = "%Y-%m-%d %H:%M:%S",
) -> Optional[Path]:
    """Setup centralized logging for FLAC Detective.

    This function configures both console and file logging handlers with
    appropriate formatters and log levels.

    Args:
        output_dir: Directory where log files will be saved.
                   If None and enable_file_logging is True, uses current directory.
        log_level: Minimum log level to capture (use LogLevel constants).
                  Default is INFO.
        enable_file_logging: If True, creates a file handler for persistent logs.
        enable_console_logging: If True, creates a console handler for terminal output.
        log_format: Format string for log messages.
        date_format: Format string for timestamps.

    Returns:
        Path to the created log file if file logging is enabled, None otherwise.

    Examples:
        >>> # Basic setup with default settings
        >>> log_file = setup_logging()

        >>> # Debug mode with custom output directory
        >>> log_file = setup_logging(
        ...     output_dir=Path("./logs"),
        ...     log_level=LogLevel.DEBUG
        ... )

        >>> # Console only (no file logging)
        >>> setup_logging(enable_file_logging=False)

    Note:
        - If Rich is available, console output will use RichHandler for better formatting
        - File logging always uses standard Python logging format for compatibility
        - Previous handlers are removed to avoid duplicate log entries
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []

    log_file = None

    # File Handler (for persistent logs)
    if enable_file_logging:
        if output_dir is None:
            output_dir = Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = output_dir / f"flac_detective_{log_timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Console Handler
    if enable_console_logging:
        if HAS_RICH:
            # Rich Handler for beautiful console output
            rich_handler = RichHandler(
                console=console,
                show_time=True,
                omit_repeated_times=False,
                show_path=False,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
            )
            rich_handler.setLevel(log_level)
            root_logger.addHandler(rich_handler)
        else:
            # Fallback to standard StreamHandler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_formatter = logging.Formatter(log_format, datefmt=date_format)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)

    # Log the setup completion
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured: level={logging.getLevelName(log_level)}")
    if log_file:
        logger.debug(f"Log file: {log_file}")

    return log_file


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    This is a convenience function to get properly configured loggers
    throughout the application.

    Args:
        name: Name of the module/component requesting the logger.
              Use __name__ for automatic module detection.

    Returns:
        Configured logger instance.

    Example:
        >>> # In your module
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing file...")
        >>> logger.warning("Unusual metadata detected")
    """
    return logging.getLogger(name)


def set_log_level(level: int) -> None:
    """Change the log level for all handlers dynamically.

    Args:
        level: New log level (use LogLevel constants).

    Example:
        >>> # Enable debug mode during troubleshooting
        >>> set_log_level(LogLevel.DEBUG)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)

    logger = logging.getLogger(__name__)
    logger.info(f"Log level changed to {logging.getLevelName(level)}")
