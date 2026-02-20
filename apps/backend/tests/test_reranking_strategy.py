"""
Tests for the Re-Ranking Strategy (Scorer).

Verifies that:
1. All results are scored and ranked — never dropped.
2. Score breakdown contains expected fields.
3. Vendor results with high vector similarity rank well.
4. Scoring uses vector similarity for vendors, not hardcoded tier matrices.
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
            provenance={"vector_similarity": 0.58}
        ),
        NormalizedResult(
            title="Custom Diamond Ring",
            price=5000.0,
            source="vendor_directory",  # Vendor
            url="https://local-jeweler.com/ring",
            merchant_name="Local Jeweler",
            merchant_domain="local-jeweler.com",
            provenance={"vector_similarity": 0.65}
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


def test_all_results_preserved(mixed_results):
    """Scoring must never drop results — only re-order."""
    intent = SearchIntent(keywords=["truck"], product_category="toys")
    ranked = score_results(results=mixed_results[:3], intent=intent, desire_tier="commodity")
    assert len(ranked) == 3


def test_vendor_with_high_similarity_ranks_well(mixed_results):
    """Vendor with high vector similarity should rank competitively."""
    intent = SearchIntent(keywords=["ring"], product_category="jewelry")
    ranked = score_results(results=mixed_results[3:], intent=intent, desire_tier="bespoke")

    # Vendor with 0.65 similarity should rank above Amazon for a ring query
    assert ranked[0].source == "vendor_directory"
    assert ranked[0].merchant_name == "Local Jeweler"

    # Amazon result should still be present
    amazon_result = next((r for r in ranked if r.source == "rainforest"), None)
    assert amazon_result is not None


def test_score_breakdown(mixed_results):
    """Verify score breakdown contains source_fit (not tier_fit)."""
    intent = SearchIntent(keywords=["truck"], product_category="toys")
    ranked = score_results(results=mixed_results[:1], intent=intent, desire_tier="commodity")

    score_data = ranked[0].provenance["score"]
    assert "source_fit" in score_data
    assert "relevance" in score_data
    assert "price" in score_data
    assert "quality" in score_data
    assert "combined" in score_data


def test_vendor_vector_similarity_drives_source_fit():
    """Vendor source_fit score should reflect vector_similarity, not a hardcoded tier matrix."""
    high_sim = NormalizedResult(
        title="Relevant Vendor", price=None, source="vendor_directory",
        url="https://v1.example", merchant_name="V1", merchant_domain="v1.example",
        provenance={"vector_similarity": 0.65},
    )
    low_sim = NormalizedResult(
        title="Irrelevant Vendor", price=None, source="vendor_directory",
        url="https://v2.example", merchant_name="V2", merchant_domain="v2.example",
        provenance={"vector_similarity": 0.30},
    )

    intent = SearchIntent(keywords=["test"], product_category="general")
    ranked = score_results([high_sim, low_sim], intent=intent)

    high_score = ranked[0].provenance["score"]["source_fit"]
    low_score = ranked[1].provenance["score"]["source_fit"]
    assert high_score > low_score, "Higher vector similarity should produce higher source_fit"
