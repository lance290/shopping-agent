"""
Tests for the Re-Ranking Strategy (Scorer + Tier Logic).

Verifies that:
1. Commodity searches prioritize Big Box results but don't exclude Vendors (Goodwill scenario).
2. Bespoke searches prioritize Vendor results but don't exclude Big Box (Vintage eBay scenario).
3. Scores are adjusted correctly based on desire_tier.
"""

import pytest
from sourcing.scorer import score_results
from sourcing.models import NormalizedResult, SearchIntent


@pytest.fixture
def mixed_results():
    """Create a mix of results from different providers."""
    return [
        NormalizedResult(
            title="LEGO Truck",
            price=25.0,
            source="rainforest",  # Amazon
            url="https://amazon.com/lego-truck",
            merchant_name="Amazon",
            merchant_domain="amazon.com",
            provenance={}
        ),
        NormalizedResult(
            title="Vintage Toy Truck",
            price=15.0,
            source="ebay_browse",  # eBay
            url="https://ebay.com/toy-truck",
            merchant_name="eBay Seller",
            merchant_domain="ebay.com",
            provenance={}
        ),
        NormalizedResult(
            title="Hand-Carved Wooden Truck",
            price=45.0,
            source="vendor_directory",  # Vendor
            url="https://goodwill.org/truck",
            merchant_name="Goodwill",
            merchant_domain="goodwill.org",
            provenance={}
        ),
        NormalizedResult(
            title="Custom Diamond Ring",
            price=5000.0,
            source="vendor_directory",  # Vendor
            url="https://local-jeweler.com/ring",
            merchant_name="Local Jeweler",
            merchant_domain="local-jeweler.com",
            provenance={}
        ),
        NormalizedResult(
            title="Cubic Zirconia Ring",
            price=50.0,
            source="rainforest",  # Amazon
            url="https://amazon.com/ring",
            merchant_name="Amazon",
            merchant_domain="amazon.com",
            provenance={}
        ),
    ]


def test_commodity_ranking(mixed_results):
    """
    Scenario: User wants a 'toy truck' (Commodity).
    Expectation: Amazon/eBay results should rank higher than Vendor results, 
    but Vendor results (Goodwill) should still be present.
    """
    intent = SearchIntent(keywords=["truck"], product_category="toys")
    
    ranked = score_results(
        results=mixed_results[:3],  # Just the trucks
        intent=intent,
        desire_tier="commodity"
    )
    
    # Top result should be Amazon or eBay (Big Box)
    assert ranked[0].source in ["rainforest", "ebay_browse"]
    
    # Vendor result should be present but ranked lower
    vendor_result = next((r for r in ranked if r.source == "vendor_directory"), None)
    assert vendor_result is not None
    assert vendor_result.provenance["score"]["source_fit"] == 0.3  # Penalized but not zero


def test_bespoke_ranking(mixed_results):
    """
    Scenario: User wants a 'custom ring' (Bespoke).
    Expectation: Vendor results should rank higher than Amazon results.
    """
    intent = SearchIntent(keywords=["ring"], product_category="jewelry")
    
    ranked = score_results(
        results=mixed_results[3:],  # Just the rings
        intent=intent,
        desire_tier="bespoke"
    )
    
    # Top result should be Vendor
    assert ranked[0].source == "vendor_directory"
    assert ranked[0].merchant_name == "Local Jeweler"
    
    # Amazon result should be present but ranked lower
    amazon_result = next((r for r in ranked if r.source == "rainforest"), None)
    assert amazon_result is not None
    assert amazon_result.provenance["score"]["source_fit"] == 0.2  # Heavy penalty


def test_score_breakdown(mixed_results):
    """Verify score breakdown contains tier_fit."""
    intent = SearchIntent(keywords=["truck"], product_category="toys")
    ranked = score_results(
        results=mixed_results[:1],
        intent=intent,
        desire_tier="commodity"
    )
    
    score_data = ranked[0].provenance["score"]
    assert "source_fit" in score_data
    assert score_data["source_fit"] == 1.0  # Amazon is perfect fit for commodity


def test_advisory_tier(mixed_results):
    """
    Scenario: Advisory tier.
    Expectation: Vendors preferred over Big Box, but generally scores should be lower/handled carefully.
    """
    intent = SearchIntent(keywords=["truck"], product_category="toys")
    ranked = score_results(
        results=mixed_results[:3],
        intent=intent,
        desire_tier="advisory"
    )
    
    # Vendor should be top for advisory if forced to rank
    assert ranked[0].source == "vendor_directory"


def test_vendor_proximity_geo_weight_boosts_local_vendor():
    intent = SearchIntent.model_validate(
        {
            "keywords": ["roof", "repair"],
            "product_category": "roofing",
            "location_context": {
                "relevance": "vendor_proximity",
                "confidence": 1.0,
                "targets": {"service_location": "Nashville, TN"},
            },
        }
    )
    local = NormalizedResult(
        title="Local Roofing Pro",
        price=None,
        source="vendor_directory",
        url="https://localroof.example.com",
        merchant_name="Local Roofing Pro",
        merchant_domain="localroof.example.com",
        raw_data={"search_metadata": {"semantic_score": 0.55, "fts_score": 0.40, "geo_score": 0.95}},
        provenance={"vector_similarity": 0.55},
    )
    distant = NormalizedResult(
        title="National Roofing Network",
        price=None,
        source="vendor_directory",
        url="https://nationalroof.example.com",
        merchant_name="National Roofing Network",
        merchant_domain="nationalroof.example.com",
        raw_data={"search_metadata": {"semantic_score": 0.70, "fts_score": 0.45, "geo_score": 0.05}},
        provenance={"vector_similarity": 0.70},
    )

    ranked = score_results([distant, local], intent=intent, desire_tier="service")

    assert ranked[0].merchant_name == "Local Roofing Pro"


def test_endpoint_mode_does_not_depend_on_hq_distance():
    intent = SearchIntent.model_validate(
        {
            "keywords": ["private", "jet", "charter"],
            "product_category": "private_aviation",
            "location_context": {
                "relevance": "endpoint",
                "confidence": 1.0,
                "targets": {"origin": "San Diego, CA", "destination": "Nashville, TN"},
            },
        }
    )
    route_fit = NormalizedResult(
        title="Private Aviation Specialist",
        price=None,
        source="vendor_directory",
        url="https://aviation.example.com",
        merchant_name="Private Aviation Specialist",
        merchant_domain="aviation.example.com",
        raw_data={"search_metadata": {"semantic_score": 0.90, "fts_score": 0.40, "geo_score": 0.0, "constraint_score": 0.85}},
        provenance={"vector_similarity": 0.90},
    )
    weak_fit = NormalizedResult(
        title="Nearby Office But Weak Match",
        price=None,
        source="vendor_directory",
        url="https://nearby.example.com",
        merchant_name="Nearby Office But Weak Match",
        merchant_domain="nearby.example.com",
        raw_data={"search_metadata": {"semantic_score": 0.35, "fts_score": 0.20, "geo_score": 1.0, "constraint_score": 0.0}},
        provenance={"vector_similarity": 0.35},
    )

    ranked = score_results([weak_fit, route_fit], intent=intent, desire_tier="service")

    assert ranked[0].merchant_name == "Private Aviation Specialist"


def test_marketplace_results_do_not_get_neutral_geo_boost():
    intent = SearchIntent.model_validate(
        {
            "keywords": ["tacos"],
            "product_category": "food",
            "location_context": {
                "relevance": "vendor_proximity",
                "confidence": 1.0,
                "targets": {"service_location": "Austin, TX"},
            },
        }
    )
    marketplace = NormalizedResult(
        title="Frozen Tacos Pack",
        price=8.0,
        source="rainforest",
        url="https://amazon.example.com/tacos",
        merchant_name="Amazon",
        merchant_domain="amazon.example.com",
        raw_data={"search_metadata": {"geo_score": 1.0}},
        provenance={},
    )
    vendor = NormalizedResult(
        title="Local Taco Stand",
        price=None,
        source="vendor_directory",
        url="https://localtaco.example.com",
        merchant_name="Local Taco Stand",
        merchant_domain="localtaco.example.com",
        raw_data={"search_metadata": {"semantic_score": 0.55, "fts_score": 0.35, "geo_score": 0.95}},
        provenance={"vector_similarity": 0.55},
    )

    ranked = score_results([marketplace, vendor], intent=intent, desire_tier="service")

    assert ranked[0].source == "vendor_directory"
    assert marketplace.provenance["score"]["geo"] == 0.0
