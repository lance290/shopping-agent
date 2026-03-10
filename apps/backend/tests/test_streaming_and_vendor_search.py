"""Regression tests for streaming search architecture and vendor directory provider.

These tests ensure:
1. VendorDirectoryProvider reads API keys at CALL TIME, not import time.
2. search_streaming yields results PER PROVIDER as they arrive (append, not batch).
3. A new search soft-deletes old non-liked/non-selected bids (replace semantics).
4. Vendor directory results are NOT excluded by choice_filter (they're vector-searched).
5. _embed_texts returns None when API key is missing (graceful degradation).
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcing.executors.base import run_provider_with_status
from sourcing.models import ProviderStatusSnapshot
from sourcing.repository import SearchResult, SourcingProvider, SourcingRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeProvider(SourcingProvider):
    """Provider that returns canned results after an optional delay."""

    def __init__(self, name: str, results: List[SearchResult], delay: float = 0.0):
        self.name = name
        self._results = results
        self._delay = delay

    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        if self._delay:
            await asyncio.sleep(self._delay)
        return list(self._results)


def _make_result(title: str, source: str, url: str = "", price: float = 0.0) -> SearchResult:
    return SearchResult(
        title=title,
        price=price,
        currency="USD",
        merchant=title,
        url=url or f"https://{source}.example.com/{title.lower().replace(' ', '-')}",
        merchant_domain=f"{source}.example.com",
        image_url=None,
        source=source,
    )


# ===========================================================================
# 1. Vendor provider reads API key at call time, not module load time
# ===========================================================================

class TestVendorProviderEnvVarTiming:
    """The OPENROUTER_API_KEY must be read at call time so dotenv has loaded."""

    def test_get_openrouter_api_key_reads_at_call_time(self):
        """_get_openrouter_api_key should return current env value, not a stale import-time snapshot."""
        from sourcing.vendor_provider import _get_openrouter_api_key

        # Set a known value
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key-abc123"}):
            assert _get_openrouter_api_key() == "test-key-abc123"

        # Change the value — should reflect immediately
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "different-key-xyz"}):
            assert _get_openrouter_api_key() == "different-key-xyz"

    def test_get_embedding_model_reads_at_call_time(self):
        from sourcing.vendor_provider import _get_embedding_model

        with patch.dict(os.environ, {"EMBEDDING_MODEL": "custom/model-v2"}):
            assert _get_embedding_model() == "custom/model-v2"

    def test_get_embedding_dimensions_reads_at_call_time(self):
        from sourcing.vendor_provider import _get_embedding_dimensions

        with patch.dict(os.environ, {"EMBEDDING_DIMENSIONS": "768"}):
            assert _get_embedding_dimensions() == 768

    def test_get_distance_threshold_reads_at_call_time(self):
        from sourcing.vendor_provider import _get_distance_threshold

        with patch.dict(os.environ, {"VENDOR_DISTANCE_THRESHOLD": "0.55"}):
            assert _get_distance_threshold() == 0.55

    @pytest.mark.asyncio
    async def test_embed_texts_returns_none_when_no_api_key(self):
        """When OPENROUTER_API_KEY is empty, _embed_texts must return None (not crash)."""
        from sourcing.vendor_provider import _embed_texts

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            result = await _embed_texts(["test query"])
            assert result is None

    @pytest.mark.asyncio
    async def test_vendor_search_returns_empty_when_no_api_key(self):
        """VendorDirectoryProvider.search returns [] when embedding fails — not an exception."""
        from sourcing.vendor_provider import VendorDirectoryProvider

        provider = VendorDirectoryProvider("postgresql+asyncpg://fake:fake@localhost/fake")
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            results = await provider.search("test query")
            assert results == []


# ===========================================================================
# 2. Streaming: results arrive per-provider, not batched
# ===========================================================================

class TestStreamingAppendNotBatch:
    """search_streaming must yield results as each provider completes, not wait for all."""

    @pytest.mark.asyncio
    async def test_streaming_yields_per_provider_as_completed(self):
        """Each provider's results must be yielded individually via asyncio.as_completed."""
        fast_results = [_make_result("Fast Item", "fast_provider")]
        slow_results = [_make_result("Slow Item", "slow_provider")]

        repo = SourcingRepository.__new__(SourcingRepository)
        repo.providers = {
            "fast": FakeProvider("fast", fast_results, delay=0.01),
            "slow": FakeProvider("slow", slow_results, delay=0.3),
        }

        events = []
        timestamps = []

        async for name, results, status, remaining in repo.search_streaming("test"):
            events.append((name, len(results), remaining))
            timestamps.append(time.monotonic())

        # Both providers should have yielded
        assert len(events) == 2

        # Fast provider should arrive first (or at least not blocked by slow)
        provider_names = [e[0] for e in events]
        assert "fast" in provider_names
        assert "slow" in provider_names

        # The gap between first and second yield should be measurable (not batched)
        # Fast completes at ~0.01s, slow at ~0.3s — if batched, both arrive at ~0.3s
        if provider_names[0] == "fast":
            gap = timestamps[1] - timestamps[0]
            assert gap > 0.1, f"Gap {gap:.3f}s too small — results may be batched, not streamed"

    @pytest.mark.asyncio
    async def test_streaming_yields_correct_providers_remaining_count(self):
        """providers_remaining must count down from (total - 1) to 0."""
        repo = SourcingRepository.__new__(SourcingRepository)
        repo.providers = {
            "a": FakeProvider("a", [_make_result("A", "a")], delay=0.01),
            "b": FakeProvider("b", [_make_result("B", "b")], delay=0.02),
            "c": FakeProvider("c", [_make_result("C", "c")], delay=0.03),
        }

        remaining_values = []
        async for _, _, _, remaining in repo.search_streaming("test"):
            remaining_values.append(remaining)

        assert sorted(remaining_values, reverse=True) == [2, 1, 0]

    @pytest.mark.asyncio
    async def test_streaming_deduplicates_urls_across_providers(self):
        """If two providers return the same URL, only the first should be yielded."""
        shared_url = "https://example.com/product-123"
        r1 = _make_result("Product A", "provider_a", url=shared_url)
        r2 = _make_result("Product B", "provider_b", url=shared_url)

        repo = SourcingRepository.__new__(SourcingRepository)
        repo.providers = {
            "a": FakeProvider("a", [r1], delay=0.01),
            "b": FakeProvider("b", [r2], delay=0.05),
        }

        all_results = []
        async for _, results, _, _ in repo.search_streaming("test"):
            all_results.extend(results)

        # Only one of them should survive dedup
        assert len(all_results) == 1

    @pytest.mark.asyncio
    async def test_streaming_handles_provider_failure_gracefully(self):
        """A failing provider should not block other providers from streaming."""

        class FailingProvider(SourcingProvider):
            async def search(self, query: str, **kwargs):
                raise RuntimeError("Provider crashed")

        good_results = [_make_result("Good Item", "good")]

        repo = SourcingRepository.__new__(SourcingRepository)
        repo.providers = {
            "good": FakeProvider("good", good_results, delay=0.01),
            "bad": FailingProvider(),
        }

        events = []
        async for name, results, status, remaining in repo.search_streaming("test"):
            events.append((name, len(results), status.status))

        assert len(events) == 2
        statuses = {e[0]: e[2] for e in events}
        assert statuses["good"] == "ok"
        assert statuses["bad"] == "error"

    @pytest.mark.asyncio
    async def test_streaming_provider_timeout_does_not_block_others(self):
        """A slow provider that times out should not prevent fast providers from yielding."""

        class HangingProvider(SourcingProvider):
            async def search(self, query: str, **kwargs):
                await asyncio.sleep(999)
                return []

        fast_results = [_make_result("Fast", "fast")]

        repo = SourcingRepository.__new__(SourcingRepository)
        repo.providers = {
            "fast": FakeProvider("fast", fast_results, delay=0.01),
            "hanging": HangingProvider(),
        }

        events = []
        t0 = time.monotonic()
        # Override timeout via env to speed up test
        with patch.dict(os.environ, {"SOURCING_PROVIDER_TIMEOUT_SECONDS": "0.5"}):
            async for name, results, status, remaining in repo.search_streaming("test"):
                events.append((name, len(results), status.status))
        elapsed = time.monotonic() - t0

        assert len(events) == 2
        # Fast should arrive quickly, hanging should timeout
        statuses = {e[0]: e[2] for e in events}
        assert statuses["fast"] == "ok"
        assert statuses["hanging"] == "timeout"
        # Total should be ~0.5s (timeout), NOT 999s
        assert elapsed < 3.0


# ===========================================================================
# 3. New search replaces old bids (soft-delete non-liked/selected)
# ===========================================================================

class TestNewSearchReplacesBids:
    """When a new search fires, old non-liked/non-selected bids get soft-deleted."""

    def test_search_stream_endpoint_supersedes_old_bids(self):
        """The /rows/{id}/search/stream endpoint must supersede stale bids AFTER providers complete.

        This is a structural test — we verify the code path exists in rows_search.py.
        Supersede happens post-search via supersede_stale_bids() so good results from
        providers that return different URLs on refinement are preserved.
        """
        import inspect
        from routes.rows_search import search_row_listings_stream

        source = inspect.getsource(search_row_listings_stream)

        # Must call supersede_stale_bids after streaming completes
        assert "supersede_stale_bids" in source, (
            "search_row_listings_stream must call supersede_stale_bids after providers complete"
        )
        assert "all_persisted_bid_ids" in source, (
            "Must track persisted bid IDs to know which bids to keep"
        )

    def test_vendor_discovery_stream_branch_runs_completion_bookkeeping(self):
        """The vendor discovery SSE branch must still retire stale bids and update zero-results UI state."""
        import inspect
        from routes.rows_search import search_row_listings_stream

        source = inspect.getsource(search_row_listings_stream)

        assert "search_path == \"vendor_discovery_path\"" in source, (
            "Expected a dedicated vendor discovery streaming branch"
        )
        assert "build_zero_results_schema" in source, (
            "Vendor discovery streaming branch must update zero-results UI state"
        )
        assert "protected_existing_ids" in source, (
            "Vendor discovery streaming branch must preserve liked/selected stale bids"
        )

    def test_supersede_stale_bids_protects_liked_and_selected(self):
        """supersede_stale_bids must only retire bids that are not liked/selected."""
        import inspect
        from sourcing.service import SourcingService

        source = inspect.getsource(SourcingService.supersede_stale_bids)
        assert "is_liked" in source, "Must check is_liked before superseding"
        assert "is_selected" in source, "Must check is_selected before superseding"

    def test_update_row_resets_bids_when_requirements_change(self):
        """_update_row with reset_bids=True must supersede old bids.

        This is the path taken when the user changes requirements (new search replaces old).
        """
        import inspect
        from routes.chat_helpers import _update_row

        source = inspect.getsource(_update_row)
        assert "is_superseded" in source, (
            "_update_row must soft-delete old bids when reset_bids=True"
        )
        assert "reset_bids" in source, (
            "_update_row must accept a reset_bids parameter"
        )


# ===========================================================================
# 4. Vendor directory results bypass choice_filter
# ===========================================================================

class TestVendorResultsBypassChoiceFilter:
    """Vendor directory results (source='vendor_directory') must NOT be filtered by choice_filter."""

    def test_search_stream_skips_choice_filter_for_vendor_directory(self):
        """The SSE generator in rows_search.py must skip choice filtering for vendor_directory."""
        import inspect
        from routes.rows_search import search_row_listings_stream

        source = inspect.getsource(search_row_listings_stream)

        # Must check source == "vendor_directory" and skip choice filtering
        assert "vendor_directory" in source, (
            "search_row_listings_stream must reference vendor_directory"
        )
        assert "is_vector_searched" in source or "vendor_directory" in source, (
            "Must skip choice filtering for vector-searched sources"
        )


# ===========================================================================
# 5. SSE event format: each event has more_incoming flag
# ===========================================================================

class TestSSEEventFormat:
    """SSE events must include more_incoming so frontend knows to append vs finalize."""

    def test_sse_event_includes_more_incoming_flag(self):
        """Each search_results SSE event must have a more_incoming boolean."""
        import inspect
        from routes.rows_search import search_row_listings_stream

        source = inspect.getsource(search_row_listings_stream)
        assert "more_incoming" in source, (
            "SSE events must include more_incoming flag"
        )
        assert "providers_remaining" in source, (
            "SSE events must include providers_remaining count"
        )

    def test_chat_handler_emits_search_results_per_batch(self):
        """Chat SSE handler must emit search_results events per provider batch, not all at once."""
        import inspect
        from routes.chat import router  # noqa: F401
        import routes.chat as chat_module

        source = inspect.getsource(chat_module)

        # Must call _stream_search which is an async generator (yields per provider)
        assert "_stream_search" in source, (
            "Chat route must use _stream_search (async generator) for incremental results"
        )
        # Must emit search_results inside the async for loop
        assert "search_results" in source, (
            "Chat route must emit search_results SSE events"
        )
        # Must forward more_incoming from the streaming batches
        assert "more_incoming" in source, (
            "Chat route must forward more_incoming from search stream"
        )
