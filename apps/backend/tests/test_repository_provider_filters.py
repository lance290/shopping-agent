import pytest

from sourcing.repository import SearchResult, SourcingRepository


class DummyProvider:
    def __init__(self, provider_id: str):
        self.provider_id = provider_id

    async def search(self, query: str, **kwargs):
        return [
            SearchResult(
                title=f"{self.provider_id} result for {query}",
                price=100.0,
                merchant=self.provider_id,
                url=f"https://{self.provider_id}.example.com/item",
                merchant_domain=f"{self.provider_id}.example.com",
                source=self.provider_id,
            )
        ]


def _make_repo_with_providers(provider_ids):
    repo = SourcingRepository.__new__(SourcingRepository)
    repo.providers = {provider_id: DummyProvider(provider_id) for provider_id in provider_ids}
    return repo


def test_provider_filter_aliases_are_normalized():
    repo = _make_repo_with_providers(["amazon", "serpapi", "vendor_directory"])
    allow = repo._normalize_provider_filter(["rainforest", "google", "ebay", "vendor_directory"])
    assert allow == {"amazon", "serpapi", "ebay", "vendor_directory"}


@pytest.mark.asyncio
async def test_search_all_with_status_accepts_rainforest_alias():
    repo = _make_repo_with_providers(["amazon", "serpapi", "vendor_directory"])

    result = await repo.search_all_with_status("standing desk", providers=["rainforest"])

    assert len(result.provider_statuses) == 1
    assert result.provider_statuses[0].provider_id == "amazon"
    assert all(r.source == "amazon" for r in result.results)


@pytest.mark.asyncio
async def test_all_providers_run_for_travel_queries():
    """Travel queries should run ALL providers — no heuristic suppression."""
    repo = _make_repo_with_providers(["amazon", "serpapi", "vendor_directory"])

    result = await repo.search_all_with_status(
        "flights from San Diego to NYC round trip",
        providers=["amazon", "serpapi", "vendor_directory"],
    )

    provider_ids = {status.provider_id for status in result.provider_statuses}
    assert provider_ids == {"amazon", "serpapi", "vendor_directory"}
