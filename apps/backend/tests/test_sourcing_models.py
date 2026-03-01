from datetime import datetime

from sourcing.models import (
    AggregatedSearchResponse,
    NormalizedResult,
    ProviderQuery,
    ProviderQueryMap,
    ProviderStatusSnapshot,
    SearchIntent,
)


def test_search_intent_keyword_normalization():
    intent = SearchIntent(
        product_category="electronics",
        taxonomy_version="shopping_v1",
        category_path=["Electronics", "Laptops"],
        product_name="MacBook Pro",
        keywords=["Laptop", "laptop", "Apple"],
        features={"ram": ["16 GB", "32 GB"]},
        raw_input="Looking for a new MacBook",
    )

    assert intent.product_category == "electronics"
    assert intent.keywords == ["Apple", "Laptop"]
    assert intent.category_path == ["Electronics", "Laptops"]


def test_provider_query_map_roundtrip():
    provider_query = ProviderQuery(
        provider_id="rainforest",
        query="macbook pro 14",
        filters={"currency": "USD"},
        metadata={"taxonomy_version": "shopping_v1"},
    )
    query_map = ProviderQueryMap()
    query_map.add(provider_query)

    serialized = query_map.model_dump()
    restored = ProviderQueryMap.model_validate(serialized)
    assert restored.get("rainforest") == provider_query


def test_normalized_result_serialization():
    normalized = NormalizedResult(
        title="MacBook Pro 14",
        url="https://example.com/macbook",
        source="rainforest",
        price=1999.99,
        merchant_name="Example Store",
        merchant_domain="example.com",
        raw_data={"id": "abc"},
    )

    payload = normalized.model_dump()
    assert payload["title"] == "MacBook Pro 14"
    assert payload["price"] == 1999.99
    assert payload["merchant_domain"] == "example.com"


def test_aggregated_search_response_structures():
    intent = SearchIntent(product_category="electronics", raw_input="laptop")
    response = AggregatedSearchResponse(
        search_intent=intent,
        provider_queries=ProviderQueryMap(),
        results=[
            NormalizedResult(
                title="MacBook",
                url="https://store.com/macbook",
                source="rainforest",
                merchant_name="Store",
                merchant_domain="store.com",
            )
        ],
        provider_statuses=[
            ProviderStatusSnapshot(provider_id="rainforest", status="ok", result_count=1, latency_ms=123)
        ],
        generated_at=datetime.utcnow(),
    )

    summary = response.provider_summary()
    assert summary["rainforest"].status == "ok"
    assert response.results[0].merchant_name == "Store"
