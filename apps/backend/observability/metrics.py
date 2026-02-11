"""
Prometheus metrics collection for Shopping Agent Backend.

Provides RED metrics (Rate, Errors, Duration) and business metrics.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    REGISTRY,
)

# Use the default registry
metrics_registry = REGISTRY

# HTTP Metrics (RED - Rate, Errors, Duration)
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=metrics_registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=metrics_registry,
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint"],
    registry=metrics_registry,
)

# Database Metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=metrics_registry,
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size",
    registry=metrics_registry,
)

db_connection_pool_checked_out = Gauge(
    "db_connection_pool_checked_out",
    "Number of connections currently checked out from pool",
    registry=metrics_registry,
)

db_connection_pool_overflow = Gauge(
    "db_connection_pool_overflow",
    "Number of overflow connections",
    registry=metrics_registry,
)

# External API Metrics
llm_api_duration_seconds = Histogram(
    "llm_api_duration_seconds",
    "LLM API call duration in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=metrics_registry,
)

llm_api_errors_total = Counter(
    "llm_api_errors_total",
    "Total LLM API errors",
    ["provider", "error_type"],
    registry=metrics_registry,
)

llm_tokens_used_total = Counter(
    "llm_tokens_used_total",
    "Total tokens consumed from LLM APIs",
    ["provider", "model", "token_type"],  # token_type: prompt, completion
    registry=metrics_registry,
)

# Search Provider Metrics
search_provider_duration_seconds = Histogram(
    "search_provider_duration_seconds",
    "Search provider API duration in seconds",
    ["provider"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=metrics_registry,
)

search_provider_errors_total = Counter(
    "search_provider_errors_total",
    "Total search provider errors",
    ["provider", "error_type"],
    registry=metrics_registry,
)

search_results_count = Histogram(
    "search_results_count",
    "Number of search results returned",
    ["provider"],
    buckets=[0, 1, 5, 10, 20, 50, 100],
    registry=metrics_registry,
)

# Business Metrics
business_events_total = Counter(
    "business_events_total",
    "Total business events",
    ["event_type"],  # row_created, bid_placed, checkout_completed, etc.
    registry=metrics_registry,
)

active_rows_gauge = Gauge(
    "active_rows_gauge",
    "Current number of active shopping rows",
    registry=metrics_registry,
)

active_bids_gauge = Gauge(
    "active_bids_gauge",
    "Current number of active bids",
    registry=metrics_registry,
)

# Cache Metrics (for future Redis integration)
cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
    registry=metrics_registry,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=metrics_registry,
)

# System Metrics
# Guard against duplicate registration (happens during hot reload or testing)
try:
    python_info = Gauge(
        "python_info",
        "Python runtime information",
        ["version", "implementation"],
        registry=metrics_registry,
    )
except ValueError:
    # Already registered - retrieve existing metric
    for collector in metrics_registry._collector_to_names.keys():
        if hasattr(collector, "_name") and collector._name == "python_info":
            python_info = collector
            break
