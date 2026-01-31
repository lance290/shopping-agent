"""Search architecture observability metrics.

This module provides structured logging and metrics tracking for the search pipeline.
Metrics tracked:
- search_success_rate: Percentage of searches returning results
- price_filter_accuracy: How often price filters correctly applied
- provider_status_reporting: Provider health and performance
- search_latency: End-to-end and per-provider latencies
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger("sourcing.metrics")


@dataclass
class ProviderMetrics:
    """Metrics for a single provider execution."""
    provider_id: str
    status: str  # ok, error, timeout, exhausted, rate_limited
    result_count: int
    latency_ms: float
    error_message: Optional[str] = None


@dataclass
class SearchMetrics:
    """Aggregated metrics for a single search operation."""
    row_id: Optional[int] = None
    query: str = ""
    total_results: int = 0
    unique_results: int = 0
    filtered_results: int = 0
    providers_called: int = 0
    providers_succeeded: int = 0
    providers_failed: int = 0
    total_latency_ms: float = 0.0
    provider_metrics: List[ProviderMetrics] = field(default_factory=list)
    price_filter_applied: bool = False
    price_filter_dropped: int = 0
    bids_created: int = 0
    bids_updated: int = 0
    is_streaming: bool = False

    def success_rate(self) -> float:
        """Calculate provider success rate."""
        if self.providers_called == 0:
            return 0.0
        return self.providers_succeeded / self.providers_called

    def has_results(self) -> bool:
        """Check if search returned any results."""
        return self.filtered_results > 0


class SearchMetricsCollector:
    """Collector for search operation metrics."""

    def __init__(self):
        self._current_metrics: Optional[SearchMetrics] = None
        self._start_time: Optional[float] = None

    @contextmanager
    def track_search(self, row_id: Optional[int] = None, query: str = "", is_streaming: bool = False):
        """Context manager to track a search operation."""
        self._current_metrics = SearchMetrics(row_id=row_id, query=query, is_streaming=is_streaming)
        self._start_time = time.time()
        try:
            yield self._current_metrics
        finally:
            if self._current_metrics and self._start_time:
                self._current_metrics.total_latency_ms = (time.time() - self._start_time) * 1000
                self._log_metrics()
            self._current_metrics = None
            self._start_time = None

    def record_provider(self, provider_id: str, status: str, result_count: int, 
                       latency_ms: float, error_message: Optional[str] = None):
        """Record metrics for a provider execution."""
        if not self._current_metrics:
            return

        provider_metric = ProviderMetrics(
            provider_id=provider_id,
            status=status,
            result_count=result_count,
            latency_ms=latency_ms,
            error_message=error_message
        )
        self._current_metrics.provider_metrics.append(provider_metric)
        self._current_metrics.providers_called += 1

        if status == "ok":
            self._current_metrics.providers_succeeded += 1
        else:
            self._current_metrics.providers_failed += 1

    def record_results(self, total: int, unique: int, filtered: int):
        """Record result counts."""
        if not self._current_metrics:
            return
        self._current_metrics.total_results = total
        self._current_metrics.unique_results = unique
        self._current_metrics.filtered_results = filtered

    def record_price_filter(self, applied: bool, dropped: int):
        """Record price filter application."""
        if not self._current_metrics:
            return
        self._current_metrics.price_filter_applied = applied
        self._current_metrics.price_filter_dropped = dropped

    def record_persistence(self, created: int, updated: int):
        """Record bid persistence counts."""
        if not self._current_metrics:
            return
        self._current_metrics.bids_created = created
        self._current_metrics.bids_updated = updated

    def _log_metrics(self):
        """Log the collected metrics in structured format."""
        m = self._current_metrics
        if not m:
            return

        # Build provider summary
        provider_summary = []
        for pm in m.provider_metrics:
            provider_summary.append({
                "id": pm.provider_id,
                "status": pm.status,
                "results": pm.result_count,
                "latency_ms": round(pm.latency_ms, 1),
            })

        # Log structured metrics
        log_data = {
            "event": "search_complete",
            "row_id": m.row_id,
            "query_length": len(m.query),
            "is_streaming": m.is_streaming,
            "results": {
                "total": m.total_results,
                "unique": m.unique_results,
                "after_filter": m.filtered_results,
            },
            "providers": {
                "called": m.providers_called,
                "succeeded": m.providers_succeeded,
                "failed": m.providers_failed,
                "success_rate": round(m.success_rate(), 2),
                "details": provider_summary,
            },
            "price_filter": {
                "applied": m.price_filter_applied,
                "dropped": m.price_filter_dropped,
            },
            "persistence": {
                "created": m.bids_created,
                "updated": m.bids_updated,
            },
            "latency_ms": round(m.total_latency_ms, 1),
            "success": m.has_results(),
        }

        # Determine log level based on outcome
        if m.providers_failed == m.providers_called and m.providers_called > 0:
            logger.error("Search failed - all providers failed", extra=log_data)
        elif m.providers_failed > 0:
            logger.warning("Search completed with provider failures", extra=log_data)
        elif not m.has_results():
            logger.warning("Search completed but no results", extra=log_data)
        else:
            logger.info("Search completed successfully", extra=log_data)


# Global collector instance
_metrics_collector = SearchMetricsCollector()


def get_metrics_collector() -> SearchMetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


def log_search_start(row_id: Optional[int], query: str, providers: List[str]):
    """Log search operation start."""
    logger.info(
        "Search started",
        extra={
            "event": "search_start",
            "row_id": row_id,
            "query_length": len(query),
            "providers_requested": providers,
        }
    )


def log_provider_result(provider_id: str, status: str, result_count: int, latency_ms: float):
    """Log individual provider result."""
    logger.info(
        f"Provider {provider_id} completed",
        extra={
            "event": "provider_complete",
            "provider_id": provider_id,
            "status": status,
            "result_count": result_count,
            "latency_ms": round(latency_ms, 1),
        }
    )
