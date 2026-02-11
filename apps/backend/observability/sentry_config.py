"""
Sentry error tracking integration.

Provides error tracking, performance monitoring, and release tracking.
"""

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from .logging import get_logger

logger = get_logger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry error tracking.

    Environment variables:
    - SENTRY_DSN: Sentry Data Source Name (required)
    - SENTRY_ENVIRONMENT: Environment name (development, staging, production)
    - SENTRY_RELEASE: Release version (e.g., git commit SHA)
    - SENTRY_TRACES_SAMPLE_RATE: Percentage of transactions to trace (0.0-1.0)
    - SENTRY_PROFILES_SAMPLE_RATE: Percentage of transactions to profile (0.0-1.0)
    - SENTRY_ENABLE: Set to "false" to disable Sentry (useful for local dev)
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    sentry_enable = os.getenv("SENTRY_ENABLE", "true").lower() == "true"

    if not sentry_dsn or not sentry_enable:
        logger.info("Sentry is disabled (SENTRY_DSN not set or SENTRY_ENABLE=false)")
        return

    environment = os.getenv("SENTRY_ENVIRONMENT") or os.getenv("ENVIRONMENT", "development")
    release = os.getenv("SENTRY_RELEASE") or os.getenv("RAILWAY_GIT_COMMIT_SHA") or "unknown"

    # Sample rates (lower in development to reduce noise)
    is_production = environment == "production"
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0" if is_production else "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1" if is_production else "0.0"))

    # Configure Sentry
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=f"shopping-agent-backend@{release}",
        # Integrations
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above
                event_level=logging.ERROR,  # Only send errors and above as events
            ),
        ],
        # Performance monitoring
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        # Additional configuration
        send_default_pii=False,  # Don't send personally identifiable information
        attach_stacktrace=True,
        max_breadcrumbs=50,
        # Request/response data
        request_bodies="medium",  # Capture request bodies up to medium size
        # Before send hook for additional filtering
        before_send=before_send_hook,
    )

    logger.info(
        "Sentry initialized",
        extra={
            "environment": environment,
            "release": release,
            "traces_sample_rate": traces_sample_rate,
            "profiles_sample_rate": profiles_sample_rate,
        },
    )


def before_send_hook(event, hint):
    """
    Filter and modify events before sending to Sentry.

    Use this to:
    - Filter out specific errors
    - Scrub sensitive data
    - Add custom tags
    """
    # Don't send client disconnection errors (normal behavior)
    if "exception" in event:
        for exc_value in event["exception"].get("values", []):
            if "client disconnected" in str(exc_value.get("value", "")).lower():
                return None

    # Add correlation ID if available
    from .logging import get_correlation_id

    correlation_id = get_correlation_id()
    if correlation_id:
        event.setdefault("tags", {})["correlation_id"] = correlation_id
        event.setdefault("extra", {})["correlation_id"] = correlation_id

    return event


def capture_exception(exc: Exception, **kwargs) -> None:
    """
    Capture an exception and send to Sentry with additional context.

    Args:
        exc: Exception to capture
        **kwargs: Additional context (tags, extra data, user info, etc.)
    """
    with sentry_sdk.push_scope() as scope:
        # Add correlation ID
        from .logging import get_correlation_id

        correlation_id = get_correlation_id()
        if correlation_id:
            scope.set_tag("correlation_id", correlation_id)

        # Add custom tags
        for key, value in kwargs.get("tags", {}).items():
            scope.set_tag(key, value)

        # Add extra context
        for key, value in kwargs.get("extra", {}).items():
            scope.set_extra(key, value)

        # Add user context
        if "user" in kwargs:
            scope.set_user(kwargs["user"])

        # Capture exception
        sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: str = "info", **kwargs) -> None:
    """
    Capture a message and send to Sentry.

    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context
    """
    with sentry_sdk.push_scope() as scope:
        # Add correlation ID
        from .logging import get_correlation_id

        correlation_id = get_correlation_id()
        if correlation_id:
            scope.set_tag("correlation_id", correlation_id)

        # Add custom tags and context
        for key, value in kwargs.get("tags", {}).items():
            scope.set_tag(key, value)

        for key, value in kwargs.get("extra", {}).items():
            scope.set_extra(key, value)

        # Capture message
        sentry_sdk.capture_message(message, level=level)
