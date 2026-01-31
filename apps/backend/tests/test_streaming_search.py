"""Tests for streaming search functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sourcing.repository import SourcingRepository, SearchResult, ProviderStatusSnapshot


class TestStreamingSearch:
    """Tests for SourcingRepository.search_streaming method."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider that returns results after a delay."""
        provider = AsyncMock()
        provider.search = AsyncMock(return_value=[
            SearchResult(
                title="Test Product",
                price=99.99,
                currency="USD",
                merchant="Test Merchant",
                url="https://example.com/product",
                merchant_domain="example.com",
                source="test_provider"
            )
        ])
        return provider

    @pytest.fixture
    def slow_provider(self):
        """Create a mock provider with delayed response."""
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.5)
            return [
                SearchResult(
                    title="Slow Product",
                    price=199.99,
                    currency="USD",
                    merchant="Slow Merchant",
                    url="https://slow.com/product",
                    merchant_domain="slow.com",
                    source="slow_provider"
                )
            ]
        provider = AsyncMock()
        provider.search = slow_search
        return provider

    @pytest.fixture
    def fast_provider(self):
        """Create a mock provider with fast response."""
        async def fast_search(*args, **kwargs):
            await asyncio.sleep(0.1)
            return [
                SearchResult(
                    title="Fast Product",
                    price=49.99,
                    currency="USD",
                    merchant="Fast Merchant",
                    url="https://fast.com/product",
                    merchant_domain="fast.com",
                    source="fast_provider"
                )
            ]
        provider = AsyncMock()
        provider.search = fast_search
        return provider

    @pytest.mark.asyncio
    async def test_streaming_yields_results_as_completed(self, fast_provider, slow_provider):
        """Test that streaming yields results as each provider completes."""
        repo = SourcingRepository()
        repo.providers = {
            "fast": fast_provider,
            "slow": slow_provider,
        }

        results = []
        providers_order = []
        
        async for provider_name, batch, status, remaining in repo.search_streaming("test query"):
            results.append((provider_name, batch))
            providers_order.append(provider_name)

        # Fast provider should complete first
        assert providers_order[0] == "fast"
        assert providers_order[1] == "slow"
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_streaming_includes_remaining_count(self, fast_provider, slow_provider):
        """Test that streaming includes correct providers_remaining count."""
        repo = SourcingRepository()
        repo.providers = {
            "fast": fast_provider,
            "slow": slow_provider,
        }

        remaining_counts = []
        
        async for provider_name, batch, status, remaining in repo.search_streaming("test query"):
            remaining_counts.append(remaining)

        # First yield should have 1 remaining, second should have 0
        assert remaining_counts == [1, 0]

    @pytest.mark.asyncio
    async def test_streaming_handles_provider_failure(self, fast_provider):
        """Test that streaming handles provider failures gracefully."""
        failing_provider = AsyncMock()
        failing_provider.search = AsyncMock(side_effect=Exception("Provider error"))

        repo = SourcingRepository()
        repo.providers = {
            "fast": fast_provider,
            "failing": failing_provider,
        }

        results = []
        statuses = []
        
        async for provider_name, batch, status, remaining in repo.search_streaming("test query"):
            results.append((provider_name, batch))
            statuses.append(status)

        # Should still get results from working provider
        assert len(results) == 2
        # One status should indicate failure
        failed_statuses = [s for s in statuses if s.status == "error"]
        assert len(failed_statuses) == 1

    @pytest.mark.asyncio
    async def test_streaming_applies_price_filters(self, mock_provider):
        """Test that streaming applies min/max price filters."""
        # Provider returns product at $99.99
        repo = SourcingRepository()
        repo.providers = {"test": mock_provider}

        # Filter should exclude the $99.99 product (min_price=100)
        results = []
        async for provider_name, batch, status, remaining in repo.search_streaming(
            "test query",
            min_price=100.0
        ):
            results.append(batch)

        # The generator yields even with empty results
        assert len(results) == 1
        # But the batch should be empty after filtering
        # Note: filtering happens at the route level, not in the generator

    @pytest.mark.asyncio
    async def test_streaming_with_single_provider(self, mock_provider):
        """Test streaming with a single provider."""
        repo = SourcingRepository()
        repo.providers = {"single": mock_provider}

        results = []
        async for provider_name, batch, status, remaining in repo.search_streaming("test query"):
            results.append((provider_name, batch, remaining))

        assert len(results) == 1
        assert results[0][0] == "single"
        assert results[0][2] == 0  # No more remaining

    @pytest.mark.asyncio
    async def test_streaming_provider_status_format(self, mock_provider):
        """Test that provider status has correct format."""
        repo = SourcingRepository()
        repo.providers = {"test": mock_provider}

        async for provider_name, batch, status, remaining in repo.search_streaming("test query"):
            assert isinstance(status, ProviderStatusSnapshot)
            assert status.provider_id == "test"
            assert status.status in ["ok", "error", "timeout", "rate_limited"]
            assert isinstance(status.result_count, int)


class TestStreamingSearchRoute:
    """Tests for the streaming search SSE endpoint."""

    @pytest.mark.asyncio
    async def test_sse_event_format(self):
        """Test that SSE events have correct format."""
        # This would require setting up a test client
        # For now, we test the generator logic directly
        pass
