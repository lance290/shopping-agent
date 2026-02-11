"""
Observability infrastructure for Shopping Agent Backend.

Provides:
- Structured logging with correlation IDs
- Sentry error tracking
- Prometheus metrics
- Performance tracing
- Health check utilities
"""

from .logging import get_logger, correlation_id_context, get_correlation_id
from .metrics import (
    metrics_registry,
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    db_query_duration_seconds,
    llm_api_duration_seconds,
    search_provider_duration_seconds,
    business_events_total,
)

__all__ = [
    "get_logger",
    "correlation_id_context",
    "get_correlation_id",
    "metrics_registry",
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
    "db_query_duration_seconds",
    "llm_api_duration_seconds",
    "search_provider_duration_seconds",
    "business_events_total",
]
