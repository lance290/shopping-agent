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
    assert vendor_result.provenance["score"]["tier_fit"] == 0.85  # Slight preference for retail but no heavy penalty (vendors span all tiers)


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
    assert amazon_result.provenance["score"]["tier_fit"] == 0.2  # Heavy penalty


def test_score_breakdown(mixed_results):
    """Verify score breakdown contains tier_fit."""
    intent = SearchIntent(keywords=["truck"], product_category="toys")
    ranked = score_results(
        results=mixed_results[:1],
        intent=intent,
        desire_tier="commodity"
    )
    
    score_data = ranked[0].provenance["score"]
    assert "tier_fit" in score_data
    assert score_data["tier_fit"] == 1.0  # Amazon is perfect fit for commodity


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


def test_vendor_obvious_commodity_prefers_vendor():
    """Commodity query can still prefer vendors when intent strongly matches vendor inventory."""
    intent = SearchIntent(
        product_category="gift_cards",
        product_name="Roblox gift card",
        keywords=["roblox", "gift", "card"],
        raw_input="roblox gift cards over $50",
    )
    results = [
        NormalizedResult(
            title="Roblox Gift Card - 50",
            price=50.0,
            source="rainforest",
            url="https://amazon.com/roblox-50",
            merchant_name="Amazon",
            merchant_domain="amazon.com",
            provenance={},
        ),
        NormalizedResult(
            title="Gaming GiftCard Vendor",
            price=None,
            source="vendor_directory",
            url="https://giftcardvendor.example",
            merchant_name="GiftCard Vendor",
            merchant_domain="giftcardvendor.example",
            provenance={"vector_similarity": 0.62},
        ),
    ]

    ranked = score_results(results, intent=intent, desire_tier="commodity")

    assert ranked[0].source == "vendor_directory"
    assert ranked[0].provenance["score"]["vendor_preferred"] is True
    amazon_result = next(r for r in ranked if r.source == "rainforest")
    assert amazon_result.provenance["score"]["affiliate_multiplier"] < 1.0
