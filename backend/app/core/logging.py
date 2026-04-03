"""
Application logging configuration module.

Handles structured logging setup with support for both development
(human-readable) and production (JSON) output formats.
"""

import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger

from app.core.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context fields."""

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name


def setup_logging() -> logging.Logger:
    """
    Configure application logging with environment-specific settings.

    Configures logging based on DEBUG setting:
    - Development (DEBUG=True): Human-readable format to console
    - Production (DEBUG=False): JSON format to console

    Returns:
        logging.Logger: Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if settings.debug:
        # Development: Human-readable format
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Production: JSON structured format
        formatter = CustomJsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    configure_module_loggers()

    return root_logger


def configure_module_loggers() -> None:
    """
    Configure logging levels for specific modules.

    Reduces verbosity from third-party libraries in non-debug mode.
    """
    # Reduce verbosity from uvicorn access logs in production
    logging.getLogger("uvicorn.access").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )

    # Reduce verbosity from SQLAlchemy in production
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )

    # Reduce verbosity from SQLAlchemy pool in production
    logging.getLogger("sqlalchemy.pool").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )

    # Application loggers
    logging.getLogger("app").setLevel(logging.DEBUG if settings.debug else logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a module.

    Args:
        name: The logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)
