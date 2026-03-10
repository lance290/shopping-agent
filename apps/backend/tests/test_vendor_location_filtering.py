from unittest.mock import AsyncMock, patch

import pytest

from sourcing.vendor_provider import VendorDirectoryProvider


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, *args, **kwargs):
        return _FakeResult(self._rows)


class _FakeEngine:
    def __init__(self, rows):
        self._rows = rows

    def connect(self):
        return _FakeConnection(self._rows)


@pytest.mark.asyncio
async def test_service_area_search_filters_non_local_vendors_when_local_matches_exist():
    provider = VendorDirectoryProvider("postgresql+asyncpg://fake:fake@localhost/fake")
    provider._engine = _FakeEngine(
        [
            {
                "id": 1,
                "name": "Luxury Ranch Real Estate",
                "description": "Luxury ranch brokerage",
                "tagline": "Colorado ranch specialists",
                "website": "https://luxuryranchrealestate.com",
                "email": "info@luxuryranchrealestate.com",
                "phone": None,
                "image_url": None,
                "category": "luxury_real_estate",
                "embedding_text": None,
                "store_geo_location": "Westcliffe, Colorado",
                "latitude": 38.1347,
                "longitude": -105.4658,
                "distance": 0.12,
                "fts_rank": 0.9,
            },
            {
                "id": 2,
                "name": "The Agency Nashville",
                "description": "Luxury Nashville real estate specialists",
                "tagline": "Serving Nashville luxury estates",
                "website": "https://theagencynashville.com",
                "email": "hello@theagencynashville.com",
                "phone": None,
                "image_url": None,
                "category": "luxury_real_estate",
                "embedding_text": None,
                "store_geo_location": "Nashville, TN",
                "latitude": 36.1627,
                "longitude": -86.7816,
                "distance": 0.19,
                "fts_rank": 0.4,
            },
        ]
    )

    intent_payload = {
        "product_category": "real_estate",
        "product_name": "Luxury real estate agent",
        "keywords": ["luxury", "real", "estate", "agent"],
        "location_context": {
            "relevance": "service_area",
            "confidence": 1.0,
            "targets": {"search_area": "Nashville, TN"},
        },
        "location_resolution": {
            "search_area": {
                "status": "resolved",
                "lat": 36.1627,
                "lon": -86.7816,
                "precision": "city",
            }
        },
    }

    with patch("sourcing.vendor_provider.build_query_embedding", new=AsyncMock(return_value=[0.1, 0.2])):
        with patch("sourcing.vendor_provider._get_distance_threshold", return_value=0.55):
            results = await provider.search(
                "luxury real estate agent",
                context_query="luxury real estate agent in nashville",
                intent_payload=intent_payload,
                limit=10,
            )

    assert results, "Expected at least one local vendor result"
    assert [result.title for result in results] == ["The Agency Nashville"]
    assert all(result.metadata.get("location_match") is True for result in results)


@pytest.mark.asyncio
async def test_vendor_proximity_prefers_nearest_geo_match_over_stronger_semantic_match():
    provider = VendorDirectoryProvider("postgresql+asyncpg://fake:fake@localhost/fake")
    provider._engine = _FakeEngine(
        [
            {
                "id": 1,
                "name": "Far But Relevant Roofer",
                "description": "Highly relevant roofing specialist",
                "tagline": "Roof repair experts",
                "website": "https://farroofer.example.com",
                "email": "hello@farroofer.example.com",
                "phone": None,
                "image_url": None,
                "category": "roofing",
                "embedding_text": None,
                "store_geo_location": "Franklin, TN",
                "latitude": 35.9251,
                "longitude": -86.8689,
                "distance": 0.08,
                "fts_rank": 0.7,
            },
            {
                "id": 2,
                "name": "Closest Roofer",
                "description": "Local roofing contractor",
                "tagline": "Fast local service",
                "website": "https://closestroofer.example.com",
                "email": "hello@closestroofer.example.com",
                "phone": None,
                "image_url": None,
                "category": "roofing",
                "embedding_text": None,
                "store_geo_location": "Nashville, TN",
                "latitude": 36.165,
                "longitude": -86.784,
                "distance": 0.18,
                "fts_rank": 0.3,
            },
        ]
    )

    intent_payload = {
        "product_category": "roofing",
        "product_name": "Roof repair",
        "keywords": ["roof", "repair"],
        "location_context": {
            "relevance": "vendor_proximity",
            "confidence": 1.0,
            "targets": {"service_location": "Nashville, TN"},
        },
        "location_resolution": {
            "service_location": {
                "status": "resolved",
                "lat": 36.1627,
                "lon": -86.7816,
                "precision": "city",
            }
        },
    }

    with patch("sourcing.vendor_provider.build_query_embedding", new=AsyncMock(return_value=[0.1, 0.2])):
        with patch("sourcing.vendor_provider._get_distance_threshold", return_value=0.55):
            results = await provider.search(
                "roof repair",
                context_query="roof repair in nashville",
                intent_payload=intent_payload,
                limit=10,
            )

    assert [result.title for result in results] == ["Closest Roofer", "Far But Relevant Roofer"]
    assert results[0].metadata.get("geo_distance_miles") is not None
    assert results[1].metadata.get("geo_distance_miles") is not None
    assert results[0].metadata["geo_distance_miles"] < results[1].metadata["geo_distance_miles"]


@pytest.mark.asyncio
async def test_vendor_proximity_prefers_exact_geo_match_before_text_only_local_match():
    provider = VendorDirectoryProvider("postgresql+asyncpg://fake:fake@localhost/fake")
    provider._engine = _FakeEngine(
        [
            {
                "id": 1,
                "name": "Text Match Roofer",
                "description": "Roofing services across Nashville",
                "tagline": "Serving Nashville",
                "website": "https://textmatchroofer.example.com",
                "email": "hello@textmatchroofer.example.com",
                "phone": None,
                "image_url": None,
                "category": "roofing",
                "embedding_text": None,
                "store_geo_location": "Nashville, TN",
                "latitude": None,
                "longitude": None,
                "distance": 0.1,
                "fts_rank": 0.8,
            },
            {
                "id": 2,
                "name": "Geo Match Roofer",
                "description": "Nearby roofer",
                "tagline": "Local roofing response",
                "website": "https://geomatchroofer.example.com",
                "email": "hello@geomatchroofer.example.com",
                "phone": None,
                "image_url": None,
                "category": "roofing",
                "embedding_text": None,
                "store_geo_location": "Nashville, TN",
                "latitude": 36.163,
                "longitude": -86.782,
                "distance": 0.22,
                "fts_rank": 0.2,
            },
        ]
    )

    intent_payload = {
        "product_category": "roofing",
        "product_name": "Roof repair",
        "keywords": ["roof", "repair"],
        "location_context": {
            "relevance": "vendor_proximity",
            "confidence": 1.0,
            "targets": {"service_location": "Nashville, TN"},
        },
        "location_resolution": {
            "service_location": {
                "status": "resolved",
                "lat": 36.1627,
                "lon": -86.7816,
                "precision": "city",
            }
        },
    }

    with patch("sourcing.vendor_provider.build_query_embedding", new=AsyncMock(return_value=[0.1, 0.2])):
        with patch("sourcing.vendor_provider._get_distance_threshold", return_value=0.55):
            results = await provider.search(
                "roof repair",
                context_query="roof repair in nashville",
                intent_payload=intent_payload,
                limit=10,
            )

    assert [result.title for result in results] == ["Geo Match Roofer", "Text Match Roofer"]
    assert results[0].metadata.get("geo_distance_miles") is not None
    assert results[1].metadata.get("geo_distance_miles") is None
