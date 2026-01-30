import asyncio

import pytest

from sourcing.executors.base import run_provider_with_status
from sourcing.models import NormalizedResult
from sourcing.normalizers import normalize_results_for_provider
from sourcing.repository import SearchResult, SourcingProvider


class DummyProvider(SourcingProvider):
    def __init__(self, delay: float = 0.0):
        self.delay = delay

    async def search(self, query: str, **kwargs):
        if self.delay:
            await asyncio.sleep(self.delay)
        return [
            SearchResult(
                title="Running shoes",
                price=10.0,
                currency="EUR",
                merchant="Test Merchant",
                url="https://example.com/item?utm_source=ads&ref=123",
                merchant_domain="example.com",
                image_url="https://example.com/image.jpg",
                rating=4.5,
                reviews_count=120,
                shipping_info="Free shipping",
                source="dummy",
            )
        ]


@pytest.mark.asyncio
async def test_run_provider_with_status_ok():
    provider = DummyProvider()
    results, status = await run_provider_with_status(
        "dummy", provider, "running shoes", timeout_seconds=1.0
    )

    assert status.status == "ok"
    assert status.result_count == 1
    assert status.latency_ms is not None
    assert results[0].title == "Running shoes"


@pytest.mark.asyncio
async def test_run_provider_with_status_timeout():
    provider = DummyProvider(delay=0.02)
    results, status = await run_provider_with_status(
        "dummy", provider, "running shoes", timeout_seconds=0.001
    )

    assert results == []
    assert status.status == "timeout"
    assert status.message == "Search timed out"


def test_normalize_results_for_provider():
    results = [
        SearchResult(
            title="Running shoes",
            price=10.0,
            currency="EUR",
            merchant="Test Merchant",
            url="https://example.com/item?utm_source=ads&ref=123",
            merchant_domain="example.com",
            image_url="https://example.com/image.jpg",
            rating=4.5,
            reviews_count=120,
            shipping_info="Free shipping",
            source="dummy",
        )
    ]

    normalized = normalize_results_for_provider("rainforest", results)
    assert isinstance(normalized[0], NormalizedResult)
    assert normalized[0].currency == "USD"
    assert normalized[0].canonical_url.startswith("https://example.com/item")
    assert "utm_source" not in normalized[0].canonical_url
    assert "ref=" not in normalized[0].canonical_url
