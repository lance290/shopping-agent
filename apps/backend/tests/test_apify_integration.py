"""Tests for the dynamic Apify integration: Store search, LLM selection, normalizers, and orchestrator wiring."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sourcing.discovery.adapters.apify import (
    ApifyDiscoveryAdapter,
    _normalize_generic,
    _normalize_google_maps,
    _normalize_instagram,
    _normalize_tripadvisor,
    _normalize_website_content,
    format_store_results_for_prompt,
    search_apify_store,
)
from sourcing.discovery.adapters.base import DiscoveryCandidate
from sourcing.discovery.apify_selector import (
    ActorSelection,
    ActorSelectionResponse,
    _build_intent_summary,
    _build_search_terms_prompt,
    _build_selection_prompt,
    _extract_json,
    select_apify_actors,
)
from sourcing.models import LocationContext, LocationTargets, SearchIntent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_intent(
    raw_input: str = "find HVAC repair in Austin",
    product_name: str = "HVAC repair",
    product_category: str = "home_services",
    relevance: str = "service_area",
    search_strategies: list = None,
    source_archetypes: list = None,
    execution_mode: str = None,
) -> SearchIntent:
    return SearchIntent(
        product_category=product_category,
        product_name=product_name,
        raw_input=raw_input,
        confidence=0.9,
        location_context=LocationContext(
            relevance=relevance,
            confidence=0.9,
            targets=LocationTargets(service_location="Austin, TX"),
        ),
        search_strategies=search_strategies or [],
        source_archetypes=source_archetypes or [],
        execution_mode=execution_mode,
    )


FAKE_STORE_ITEMS = [
    {
        "username": "compass",
        "name": "crawler-google-places",
        "title": "Google Maps Scraper",
        "description": "Scrape Google Maps places data",
        "readmeSummary": "Extract names, addresses, phone numbers...",
        "stats": {"totalUsers": 5000, "totalRuns": 100000},
        "currentPricingInfo": {"pricingModel": "FREE"},
    },
    {
        "username": "apify",
        "name": "instagram-scraper",
        "title": "Instagram Scraper",
        "description": "Scrape Instagram profiles and posts",
        "readmeSummary": "Get followers, posts, hashtags...",
        "stats": {"totalUsers": 3000, "totalRuns": 50000},
        "currentPricingInfo": {"pricingModel": "PAY_PER_RESULT"},
    },
]


# ---------------------------------------------------------------------------
# Store search tests
# ---------------------------------------------------------------------------

class TestSearchApifyStore:
    @pytest.mark.asyncio
    async def test_returns_formatted_results(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": {"items": FAKE_STORE_ITEMS}}

        with patch("sourcing.discovery.adapters.apify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await search_apify_store("google maps")

        assert len(results) == 2
        assert results[0]["actor_id"] == "compass/crawler-google-places"
        assert results[0]["title"] == "Google Maps Scraper"
        assert results[0]["total_users"] == 5000
        assert results[1]["actor_id"] == "apify/instagram-scraper"

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self):
        with patch("sourcing.discovery.adapters.apify.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await search_apify_store("anything")

        assert results == []


class TestFormatStoreResults:
    def test_formats_actors_for_prompt(self):
        actors = [
            {"actor_id": "a/b", "title": "Test", "description": "Desc", "total_users": 10, "total_runs": 100, "pricing": "FREE", "readme_summary": "Summary here"},
        ]
        text = format_store_results_for_prompt(actors)
        assert "a/b" in text
        assert "Test" in text
        assert "FREE" in text
        assert "Summary here" in text

    def test_handles_empty_list(self):
        text = format_store_results_for_prompt([])
        assert "No Actors found" in text


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------

class TestGoogleMapsNormalizer:
    def test_normalizes_google_maps_items(self):
        items = [
            {
                "title": "Joe's HVAC",
                "website": "https://joeshvac.com",
                "url": "https://maps.google.com/place/joes-hvac",
                "totalScore": 4.8,
                "reviewsCount": 120,
                "description": "HVAC repair and installation",
                "phone": "+15125551234",
                "phoneUnformatted": "+15125551234",
                "address": "123 Main St, Austin, TX",
                "imageUrl": "https://img.example/joe.jpg",
            },
        ]
        candidates = _normalize_google_maps(items, query="HVAC Austin")
        assert len(candidates) == 1
        c = candidates[0]
        assert c.title == "Joe's HVAC"
        assert c.url == "https://joeshvac.com"
        assert c.phone == "+15125551234"
        assert c.trust_signals["rating"] == 4.8
        assert c.trust_signals["reviews_count"] == 120
        assert c.official_site is True
        assert c.first_party_contact is True
        assert c.adapter_id == "apify_google_maps"

    def test_skips_items_without_title(self):
        items = [{"url": "https://example.com"}]
        assert _normalize_google_maps(items, query="test") == []


class TestInstagramNormalizer:
    def test_normalizes_instagram_items(self):
        items = [
            {
                "ownerUsername": "artisan_jeweler",
                "ownerFullName": "Artisan Jeweler",
                "followersCount": 50000,
                "likesCount": 1200,
                "caption": "Custom rings made to order",
                "displayUrl": "https://img.example/ring.jpg",
                "externalUrl": "https://artisanjeweler.com",
            },
        ]
        candidates = _normalize_instagram(items, query="custom rings")
        assert len(candidates) == 1
        c = candidates[0]
        assert c.title == "Artisan Jeweler"
        assert "instagram.com/artisan_jeweler" in c.url
        assert c.trust_signals["followers"] == 50000
        assert c.first_party_contact is True
        assert c.source_type == "social_profile"


class TestTripAdvisorNormalizer:
    def test_normalizes_tripadvisor_items(self):
        items = [
            {
                "name": "The Grand Hotel",
                "url": "https://tripadvisor.com/Hotel-Grand",
                "rating": 4.5,
                "reviewsCount": 800,
                "description": "Luxury hotel in downtown",
                "phone": "+15125559999",
                "address": "456 Oak Ave",
            },
        ]
        candidates = _normalize_tripadvisor(items, query="luxury hotel Austin")
        assert len(candidates) == 1
        c = candidates[0]
        assert c.title == "The Grand Hotel"
        assert c.trust_signals["rating"] == 4.5
        assert c.first_party_contact is True

    def test_skips_items_without_name(self):
        items = [{"url": "https://example.com", "rating": 3.0}]
        assert _normalize_tripadvisor(items, query="test") == []


class TestWebsiteContentNormalizer:
    def test_normalizes_website_content(self):
        items = [
            {
                "url": "https://plumber-austin.com",
                "title": "Austin Plumbing Pros",
                "text": "We provide 24/7 plumbing services in Austin, TX. Call us!",
            },
        ]
        candidates = _normalize_website_content(items, query="plumber Austin")
        assert len(candidates) == 1
        c = candidates[0]
        assert c.title == "Austin Plumbing Pros"
        assert c.source_type == "official_vendor_site"
        assert "plumbing services" in c.snippet


class TestGenericNormalizer:
    def test_normalizes_unknown_schema(self):
        items = [
            {"title": "Random Vendor", "url": "https://random.com", "description": "Stuff", "phone": "555-1234"},
            {"name": "Named Vendor", "website": "https://named.com", "address": "123 St"},
        ]
        candidates = _normalize_generic(items, query="vendors")
        assert len(candidates) == 2
        assert candidates[0].title == "Random Vendor"
        assert candidates[0].phone == "555-1234"
        assert candidates[1].title == "Named Vendor"
        assert candidates[1].url == "https://named.com"

    def test_skips_items_without_url(self):
        items = [{"title": "No URL Vendor"}]
        assert _normalize_generic(items, query="test") == []


# ---------------------------------------------------------------------------
# Apify Selector tests
# ---------------------------------------------------------------------------

class TestExtractJson:
    def test_plain_json(self):
        assert _extract_json('["a", "b"]') == ["a", "b"]

    def test_fenced_json(self):
        assert _extract_json('```json\n["a", "b"]\n```') == ["a", "b"]

    def test_fenced_without_lang(self):
        assert _extract_json('```\n{"key": 1}\n```') == {"key": 1}


class TestBuildIntentSummary:
    def test_includes_all_fields(self):
        intent = _make_intent(
            search_strategies=["local_network_first"],
            source_archetypes=["local_directory"],
            execution_mode="sourcing_only",
        )
        summary = _build_intent_summary("HVAC repair Austin", intent, "local_service_discovery", "Austin, TX")
        assert "HVAC repair Austin" in summary
        assert "local_network_first" in summary
        assert "local_directory" in summary
        assert "sourcing_only" in summary
        assert "Austin, TX" in summary


class TestSelectApifyActors:
    @pytest.mark.asyncio
    async def test_returns_skip_when_no_search_terms(self):
        with patch("services.llm_core.call_gemini", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "[]"
            result = await select_apify_actors(
                query="AA batteries",
                intent=_make_intent(raw_input="AA batteries", product_name="AA batteries", product_category="commodity", relevance="none"),
                discovery_mode="local_service_discovery",
            )
        assert result.actors == []
        assert "no scraper needed" in result.skip_reason.lower()

    @pytest.mark.asyncio
    async def test_returns_actors_on_success(self):
        call_count = 0

        async def fake_gemini(prompt, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return '["google maps scraper"]'
            return '{"actors": [{"actor_id": "compass/crawler-google-places", "run_input": {"searchStringsArray": ["HVAC Austin"]}, "reason": "local business data"}], "skip_reason": ""}'

        with patch("services.llm_core.call_gemini", new_callable=AsyncMock, side_effect=fake_gemini):
            with patch("sourcing.discovery.apify_selector.search_apify_store", new_callable=AsyncMock) as mock_store:
                mock_store.return_value = [
                    {"actor_id": "compass/crawler-google-places", "title": "Google Maps Scraper", "description": "desc", "total_users": 5000, "total_runs": 100000, "pricing": "FREE"},
                ]
                result = await select_apify_actors(
                    query="HVAC repair in Austin",
                    intent=_make_intent(),
                    discovery_mode="local_service_discovery",
                    location_hint="Austin, TX",
                )

        assert len(result.actors) == 1
        assert result.actors[0].actor_id == "compass/crawler-google-places"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_llm_failure(self):
        with patch("services.llm_core.call_gemini", new_callable=AsyncMock, side_effect=Exception("LLM down")):
            result = await select_apify_actors(
                query="test",
                intent=_make_intent(),
                discovery_mode="local_service_discovery",
            )
        assert result.actors == []
        assert "failed" in result.skip_reason.lower()


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------

class TestApifyDiscoveryAdapter:
    @pytest.mark.asyncio
    async def test_run_actor_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            adapter = ApifyDiscoveryAdapter()
            adapter.api_key = None
            batch = await adapter.run_actor(
                actor_id="test/actor",
                run_input={},
                query="test",
            )
        assert batch.status == "error"
        assert "APIFY_API_TOKEN" in batch.error_message

    @pytest.mark.asyncio
    async def test_search_stub_returns_error(self):
        adapter = ApifyDiscoveryAdapter()
        batch = await adapter.search("test", discovery_mode="local_service_discovery")
        assert batch.status == "error"
        assert "run_actor()" in batch.error_message

    def test_supported_modes_covers_all_discovery_modes(self):
        adapter = ApifyDiscoveryAdapter()
        expected = {
            "local_service_discovery",
            "luxury_brokerage_discovery",
            "destination_service_discovery",
            "uhnw_goods_discovery",
            "asset_market_discovery",
            "advisory_discovery",
        }
        assert adapter.supported_modes == expected


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------

class TestActorSelectionModels:
    def test_actor_selection_roundtrip(self):
        sel = ActorSelection(
            actor_id="test/actor",
            run_input={"search": "query"},
            reason="testing",
        )
        assert sel.actor_id == "test/actor"
        assert sel.run_input == {"search": "query"}

    def test_actor_selection_response_empty(self):
        resp = ActorSelectionResponse(skip_reason="not needed")
        assert resp.actors == []
        assert resp.skip_reason == "not needed"

    def test_actor_selection_response_with_actors(self):
        resp = ActorSelectionResponse(
            actors=[
                ActorSelection(actor_id="a/b", run_input={"x": 1}, reason="test"),
            ],
        )
        assert len(resp.actors) == 1
