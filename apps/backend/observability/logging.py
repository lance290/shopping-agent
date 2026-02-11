"""
Structured logging with correlation IDs and JSON formatting.

Usage:
    from observability import get_logger

    logger = get_logger(__name__)
    logger.info("User action", extra={
        "user_id": 123,
        "action": "create_row",
        "resource_id": "row-456"
    })
"""

import logging
import os
import uuid
from contextvars import ContextVar
from typing import Optional, Dict, Any

from pythonjsonlogger import jsonlogger

# Context variable for correlation ID (thread-safe request tracking)
_correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id_ctx.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return f"req-{uuid.uuid4().hex[:16]}"


class correlation_id_context:
    """Context manager for setting correlation ID."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.token = None

    def __enter__(self):
        self.token = _correlation_id_ctx.set(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        _correlation_id_ctx.reset(self.token)


class CorrelationIDFilter(logging.Filter):
    """Adds correlation_id to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        correlation_id = get_correlation_id()
        record.correlation_id = correlation_id if correlation_id else "none"
        return True


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive data from log records."""

    SENSITIVE_KEYS = {
        "password", "token", "api_key", "secret", "authorization",
        "credit_card", "ssn", "stripe_secret", "clerk_secret"
    }

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact sensitive data in message
        if hasattr(record, "args") and record.args:
            record.args = self._redact_dict(record.args)

        # Redact sensitive data in extra fields
        for key in list(record.__dict__.keys()):
            if key.lower() in self.SENSITIVE_KEYS:
                setattr(record, key, "[REDACTED]")

        return True

    def _redact_dict(self, data: Any) -> Any:
        """Recursively redact sensitive keys in dictionaries."""
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if k.lower() in self.SENSITIVE_KEYS else self._redact_dict(v)
                for k, v in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return [self._redact_dict(item) for item in data]
        return data


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["correlation_id"] = getattr(record, "correlation_id", "none")

        # Add environment context
        log_record["environment"] = os.getenv("ENVIRONMENT", "development")
        log_record["service"] = "shopping-agent-backend"

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_logging() -> None:
    """
    Setup structured logging for the application.

    Environment variables:
    - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - LOG_FORMAT: json or text (default: json in production, text in dev)
    - ENVIRONMENT: development, staging, production
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json" if os.getenv("ENVIRONMENT") == "production" else "text")

    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler()

    # Set formatter based on environment
    if log_format == "json":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(correlation_id)s %(message)s",
            rename_fields={"timestamp": "@timestamp"}
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)

    # Add filters
    handler.addFilter(CorrelationIDFilter())
    handler.addFilter(SensitiveDataFilter())

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with structured logging configured.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Setup logging on module import
setup_logging()
