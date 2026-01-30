"""
Structured logging configuration for SSIS-to-dbt migration.

This module provides consistent logging setup across all components,
with support for both console (rich) and file output.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.logging import RichHandler

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Default log format for file output
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Sensitive patterns to redact from log messages
SENSITIVE_PATTERNS = [
    "password",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "token",
    "credential",
]


class SanitizingFilter(logging.Filter):
    """
    Filter that sanitizes sensitive information from log records.

    Prevents accidental logging of passwords, API keys, and other secrets.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize the log message before output."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for pattern in SENSITIVE_PATTERNS:
                if pattern in msg_lower:
                    # Check if this looks like it might contain a value
                    if "=" in record.msg or ":" in record.msg:
                        record.msg = self._redact_sensitive(record.msg)
                        break
        return True

    def _redact_sensitive(self, msg: str) -> str:
        """Redact sensitive values from message."""
        import re

        for pattern in SENSITIVE_PATTERNS:
            # Match pattern=value or pattern: value
            msg = re.sub(
                rf"({pattern}\s*[=:]\s*)([^\s,;]+)",
                r"\1***REDACTED***",
                msg,
                flags=re.IGNORECASE,
            )
        return msg


class StructuredLogger:
    """
    Factory for creating consistently configured loggers.

    Provides both rich console output and file logging with
    automatic sensitive data filtering.
    """

    _initialized = False
    _log_dir: Optional[Path] = None
    _log_file: Optional[Path] = None

    @classmethod
    def setup(
        cls,
        level: int = logging.INFO,
        log_dir: Optional[str] = None,
        log_to_file: bool = True,
        console_output: bool = True,
    ) -> None:
        """
        Initialize the logging configuration.

        Args:
            level: Logging level (default INFO)
            log_dir: Directory for log files (default: ./logs)
            log_to_file: Whether to write logs to file
            console_output: Whether to output to console
        """
        if cls._initialized:
            return

        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Add sanitizing filter to root logger
        root_logger.addFilter(SanitizingFilter())

        # Console handler
        if console_output:
            if RICH_AVAILABLE:
                console_handler = RichHandler(
                    console=Console(stderr=True),
                    show_time=True,
                    show_path=False,
                    markup=True,
                    rich_tracebacks=True,
                    tracebacks_show_locals=False,  # Don't show locals (may contain secrets)
                )
                console_handler.setLevel(level)
            else:
                console_handler = logging.StreamHandler(sys.stderr)
                console_handler.setLevel(level)
                console_handler.setFormatter(
                    logging.Formatter(FILE_FORMAT, DATE_FORMAT)
                )
            root_logger.addHandler(console_handler)

        # File handler
        if log_to_file:
            cls._log_dir = Path(log_dir) if log_dir else Path("./logs")
            cls._log_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cls._log_file = cls._log_dir / f"ssis_migration_{timestamp}.log"

            file_handler = logging.FileHandler(cls._log_file)
            file_handler.setLevel(logging.DEBUG)  # File gets all levels
            file_handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
            file_handler.addFilter(SanitizingFilter())
            root_logger.addHandler(file_handler)

        cls._initialized = True

        # Log initialization
        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized (level={logging.getLevelName(level)})")
        if cls._log_file:
            logger.info(f"Log file: {cls._log_file}")

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger with the given name.

        Automatically initializes logging if not already done.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            cls.setup()
        return logging.getLogger(name)

    @classmethod
    def get_log_file(cls) -> Optional[Path]:
        """Get the path to the current log file."""
        return cls._log_file


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[str] = None,
    log_to_file: bool = True,
    console_output: bool = True,
) -> None:
    """
    Convenience function to set up logging.

    Args:
        level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_file: Whether to write to file
        console_output: Whether to write to console
    """
    level_int = getattr(logging, level.upper(), logging.INFO)
    StructuredLogger.setup(
        level=level_int,
        log_dir=log_dir,
        log_to_file=log_to_file,
        console_output=console_output,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return StructuredLogger.get_logger(name)
