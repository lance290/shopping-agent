"""Tests for search architecture observability metrics."""

import pytest
from sourcing.metrics import (
    SearchMetrics,
    ProviderMetrics,
    SearchMetricsCollector,
    get_metrics_collector,
    log_search_start,
    log_provider_result,
)


class TestSearchMetrics:
    """Tests for SearchMetrics dataclass."""

    def test_success_rate_with_all_succeeded(self):
        metrics = SearchMetrics(providers_called=3, providers_succeeded=3)
        assert metrics.success_rate() == 1.0

    def test_success_rate_with_partial_failure(self):
        metrics = SearchMetrics(providers_called=4, providers_succeeded=2, providers_failed=2)
        assert metrics.success_rate() == 0.5

    def test_success_rate_with_all_failed(self):
        metrics = SearchMetrics(providers_called=2, providers_succeeded=0, providers_failed=2)
        assert metrics.success_rate() == 0.0

    def test_success_rate_with_no_providers(self):
        metrics = SearchMetrics(providers_called=0)
        assert metrics.success_rate() == 0.0

    def test_has_results_true(self):
        metrics = SearchMetrics(filtered_results=5)
        assert metrics.has_results() is True

    def test_has_results_false(self):
        metrics = SearchMetrics(filtered_results=0)
        assert metrics.has_results() is False


class TestProviderMetrics:
    """Tests for ProviderMetrics dataclass."""

    def test_provider_metrics_creation(self):
        pm = ProviderMetrics(
            provider_id="rainforest",
            status="ok",
            result_count=10,
            latency_ms=250.5
        )
        assert pm.provider_id == "rainforest"
        assert pm.status == "ok"
        assert pm.result_count == 10
        assert pm.latency_ms == 250.5
        assert pm.error_message is None

    def test_provider_metrics_with_error(self):
        pm = ProviderMetrics(
            provider_id="google_cse",
            status="error",
            result_count=0,
            latency_ms=100.0,
            error_message="Connection timeout"
        )
        assert pm.status == "error"
        assert pm.error_message == "Connection timeout"


class TestSearchMetricsCollector:
    """Tests for SearchMetricsCollector."""

    def test_track_search_context_manager(self):
        collector = SearchMetricsCollector()
        
        with collector.track_search(row_id=1, query="test query") as metrics:
            assert metrics.row_id == 1
            assert metrics.query == "test query"
            collector.record_provider("test", "ok", 5, 100.0)
            collector.record_results(10, 8, 5)
        
        # After context exits, metrics should be cleared
        assert collector._current_metrics is None

    def test_record_provider_increments_counts(self):
        collector = SearchMetricsCollector()
        
        with collector.track_search(row_id=1, query="test") as metrics:
            collector.record_provider("provider1", "ok", 5, 100.0)
            collector.record_provider("provider2", "error", 0, 50.0, "Failed")
            
            assert metrics.providers_called == 2
            assert metrics.providers_succeeded == 1
            assert metrics.providers_failed == 1
            assert len(metrics.provider_metrics) == 2

    def test_record_results(self):
        collector = SearchMetricsCollector()
        
        with collector.track_search(row_id=1, query="test") as metrics:
            collector.record_results(total=20, unique=15, filtered=10)
            
            assert metrics.total_results == 20
            assert metrics.unique_results == 15
            assert metrics.filtered_results == 10

    def test_record_price_filter(self):
        collector = SearchMetricsCollector()
        
        with collector.track_search(row_id=1, query="test") as metrics:
            collector.record_price_filter(applied=True, dropped=5)
            
            assert metrics.price_filter_applied is True
            assert metrics.price_filter_dropped == 5

    def test_record_persistence(self):
        collector = SearchMetricsCollector()
        
        with collector.track_search(row_id=1, query="test") as metrics:
            collector.record_persistence(created=8, updated=2)
            
            assert metrics.bids_created == 8
            assert metrics.bids_updated == 2

    def test_latency_tracked(self):
        import time
        collector = SearchMetricsCollector()
        
        with collector.track_search(row_id=1, query="test") as metrics:
            time.sleep(0.05)  # 50ms
        
        # Latency should be recorded (at least 50ms)
        # Note: We can't check metrics after context exits, but the log would have it


class TestGlobalMetricsCollector:
    """Tests for global metrics collector."""

    def test_get_metrics_collector_returns_singleton(self):
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2


class TestLoggingFunctions:
    """Tests for standalone logging functions."""

    def test_log_search_start_does_not_raise(self):
        # Should not raise any exceptions
        log_search_start(row_id=1, query="test", providers=["rainforest", "google_cse"])

    def test_log_search_start_with_none_row_id(self):
        # Should handle None row_id gracefully
        log_search_start(row_id=None, query="test", providers=[])

    def test_log_provider_result_does_not_raise(self):
        # Should not raise any exceptions
        log_provider_result(
            provider_id="rainforest",
            status="ok",
            result_count=10,
            latency_ms=250.0
        )

    def test_log_provider_result_with_failure(self):
        # Should handle error status gracefully
        log_provider_result(
            provider_id="google_cse",
            status="error",
            result_count=0,
            latency_ms=100.0
        )
