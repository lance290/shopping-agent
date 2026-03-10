import pytest
from unittest.mock import AsyncMock, patch

from models.rows import Row
from sourcing.discovery.adapters.base import DiscoveryCandidate, DiscoveryBatch
from sourcing.discovery.adapters.organic import _search_organic
from sourcing.discovery.classification import classify_candidate
from sourcing.discovery.gating import gate_discovery_candidates
from sourcing.discovery.llm_rerank import rerank_gated_candidates
from sourcing.discovery.orchestrator import DiscoveryOrchestrator
from sourcing.models import LocationContext, LocationTargets, SearchIntent


def _intent(raw_input: str, relevance: str = "service_area", category: str = "luxury_real_estate") -> SearchIntent:
    return SearchIntent(
        product_category=category,
        product_name="luxury real estate agent" if category == "luxury_real_estate" else raw_input,
        raw_input=raw_input,
        keywords=["luxury", "real estate", "agent"] if category == "luxury_real_estate" else raw_input.split(),
        location_context=LocationContext(
            relevance=relevance,
            confidence=0.95,
            targets=LocationTargets(search_area="Nashville, TN"),
        ),
    )


@pytest.mark.asyncio
async def test_organic_adapter_defaults_to_unknown_provenance():
    with patch("sourcing.discovery.adapters.organic._get_json", AsyncMock(return_value={
        "organic_results": [
            {"title": "Example Vendor", "link": "https://example.com", "snippet": "Call us at 615-555-1212"}
        ]
    })):
        with patch("os.getenv", side_effect=lambda key, default="": "test-key" if key == "SERPAPI_API_KEY" else default):
            results = await _search_organic("nashville luxury brokerage", max_results=3, timeout_seconds=1.0)

    assert len(results) == 1
    assert results[0].source_type == "unknown"
    assert results[0].official_site is False


def test_classification_distinguishes_brokerage_from_listing_page():
    row = Row(title="Sell mansion", is_service=True, service_category="real_estate", desire_tier="service")
    intent = _intent("sell my modern belle meade mansion")

    brokerage = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="The Agency Nashville | Luxury Real Estate Team",
        url="https://agencynashville.com/team",
        source_url="https://agencynashville.com/team",
        source_type="unknown",
        canonical_domain="agencynashville.com",
        snippet="Belle Meade luxury real estate specialists serving Nashville.",
    )
    listing = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Luxury Waterfront Homes for sale in New York",
        url="https://luxuryportal.example/listings/123",
        source_url="https://luxuryportal.example/listings/123",
        source_type="unknown",
        canonical_domain="luxuryportal.example",
        snippet="View property details and similar listings.",
    )

    brokerage_class = classify_candidate(brokerage, discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)
    listing_class = classify_candidate(listing, discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)

    assert brokerage_class.candidate_type == "brokerage_or_agent_site"
    assert listing_class.candidate_type == "listing_or_inventory_page"


def test_location_sensitive_gating_suppresses_non_local_when_local_exists():
    row = Row(title="Sell mansion", is_service=True, service_category="real_estate", desire_tier="service")
    intent = _intent("sell my modern belle meade mansion")

    local = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Belle Meade Estates | Nashville Luxury Team",
        url="https://bellemeadeestates.example",
        source_url="https://bellemeadeestates.example",
        source_type="unknown",
        canonical_domain="bellemeadeestates.example",
        snippet="Nashville luxury real estate experts in Belle Meade.",
        email="team@bellemeadeestates.example",
    )
    remote = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Hamptons Waterfront Luxury Portfolio",
        url="https://hamptonsluxury.example/listings",
        source_url="https://hamptonsluxury.example/listings",
        source_type="unknown",
        canonical_domain="hamptonsluxury.example",
        snippet="Luxury homes and listings in New York and the Hamptons.",
    )

    classify_candidate(local, discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)
    classify_candidate(remote, discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)
    gated = gate_discovery_candidates([local, remote], discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)

    admitted_domains = {item.candidate.canonical_domain for item in gated if item.admissible}
    assert admitted_domains == {"bellemeadeestates.example"}


@pytest.mark.asyncio
async def test_llm_rerank_falls_back_to_heuristics_when_llm_fails():
    row = Row(title="Find broker", is_service=True, service_category="real_estate", desire_tier="service")
    intent = _intent("nashville luxury real estate broker")
    strong = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Nashville Luxury Team",
        url="https://nashvilleluxury.example",
        source_url="https://nashvilleluxury.example",
        source_type="unknown",
        canonical_domain="nashvilleluxury.example",
        snippet="Nashville luxury real estate team in Belle Meade.",
        email="hello@nashvilleluxury.example",
    )
    okay = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Luxury Agent Directory",
        url="https://directory.example/agents",
        source_url="https://directory.example/agents",
        source_type="unknown",
        canonical_domain="directory.example",
        snippet="Compare luxury agents.",
    )
    classify_candidate(strong, discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)
    classify_candidate(okay, discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)
    gated = gate_discovery_candidates([strong, okay], discovery_mode="luxury_brokerage_discovery", intent=intent, row=row)

    with patch("sourcing.discovery.llm_rerank.call_gemini", AsyncMock(side_effect=RuntimeError("timeout"))):
        reranked, decisions = await rerank_gated_candidates(gated, intent=intent, row=row)

    assert decisions == {}
    assert reranked[0].candidate.canonical_domain == "nashvilleluxury.example"


def test_goods_mode_allows_marketplace_candidates():
    row = Row(title="Buy rare whisky", is_service=False, service_category=None, desire_tier="high_value")
    intent = _intent("buy rare whisky collection", relevance="none", category="spirits")
    marketplace = DiscoveryCandidate(
        adapter_id="google_organic",
        query="rare whisky auction",
        title="Rare Whisky Auction Exchange",
        url="https://auction.example/rare-whisky",
        source_url="https://auction.example/rare-whisky",
        source_type="unknown",
        canonical_domain="auction.example",
        snippet="Marketplace for rare whisky collectors and auctions.",
    )
    classify_candidate(marketplace, discovery_mode="uhnw_goods_discovery", intent=intent, row=row)
    gated = gate_discovery_candidates([marketplace], discovery_mode="uhnw_goods_discovery", intent=intent, row=row)
    assert gated[0].admissible is True
    assert gated[0].candidate.classification["candidate_type"] == "marketplace_or_exchange"


@pytest.mark.asyncio
async def test_orchestrator_filters_listing_pages_before_normalization():
    row = Row(id=1, user_id=1, title="Sell mansion", is_service=True, service_category="real_estate", desire_tier="service")
    intent = _intent("sell my belle meade mansion")
    listing = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Luxury Waterfront Homes for sale in New York",
        url="https://luxuryportal.example/listings/123",
        source_url="https://luxuryportal.example/listings/123",
        source_type="unknown",
        canonical_domain="luxuryportal.example",
        snippet="Luxury homes for sale in New York.",
    )
    brokerage = DiscoveryCandidate(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        title="Belle Meade Estates",
        url="https://bellemeadeestates.example",
        source_url="https://bellemeadeestates.example",
        source_type="unknown",
        canonical_domain="bellemeadeestates.example",
        snippet="Nashville Belle Meade luxury brokerage.",
        email="hello@bellemeadeestates.example",
    )

    orchestrator = DiscoveryOrchestrator(session=None, sourcing_service=None)
    batch = DiscoveryBatch(
        adapter_id="google_organic",
        query="nashville luxury real estate brokerage",
        results=[listing, brokerage],
        status="ok",
        latency_ms=10,
    )
    with patch("sourcing.discovery.classification.enrich_candidates_for_classification", AsyncMock(return_value=None)), \
         patch("sourcing.discovery.llm_rerank.call_gemini", AsyncMock(side_effect=RuntimeError("no llm"))):
        results = await orchestrator._process_batch(
            row=row,
            discovery_session_id="sess",
            discovery_mode="luxury_brokerage_discovery",
            query=batch.query,
            search_intent=intent,
            batch=batch,
        )

    assert [result.merchant_domain for result in results] == ["bellemeadeestates.example"]
