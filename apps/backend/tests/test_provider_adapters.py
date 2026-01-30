import pytest

from sourcing.adapters import build_provider_query_map
from sourcing.models import SearchIntent


def test_build_provider_query_map_for_known_providers():
    intent = SearchIntent(
        product_category="running_shoes",
        taxonomy_version="shopping_v1",
        keywords=["lightweight"],
        max_price=80,
        condition="new",
        raw_input="lightweight running shoes",
    )

    query_map = build_provider_query_map(intent, ["rainforest", "google_cse", "unknown"])

    rainforest_query = query_map.get("rainforest")
    assert rainforest_query is not None
    assert "running" in rainforest_query.query
    assert rainforest_query.filters.get("max_price") == 80
    assert rainforest_query.metadata.get("taxonomy_version") == "shopping_v1"

    google_query = query_map.get("google_cse")
    assert google_query is not None
    assert "running" in google_query.query
    assert "category_path" in google_query.metadata


def test_provider_query_map_skips_missing_providers():
    intent = SearchIntent(product_category="laptop", raw_input="gaming laptop")
    query_map = build_provider_query_map(intent, ["unknown"])

    assert query_map.queries == {}
