"""Tests for tile provenance data pipeline.

Covers:
- task-001: NormalizedResult provenance field + normalizer builds provenance
- task-002: _persist_results enriches provenance with search intent + chat excerpts
- task-004: End-to-end provenance through BidWithProvenance
"""
import json
import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sourcing.models import NormalizedResult
from sourcing.repository import SearchResult
from sourcing.normalizers import _build_provenance, _normalize_result, normalize_generic_results
from sourcing.service import SourcingService
from models import Bid, BidWithProvenance, Row, Seller


# ---------------------------------------------------------------------------
# task-001: TestNormalizerProvenance
# ---------------------------------------------------------------------------

class TestNormalizerProvenance:
    """Verify _build_provenance and _normalize_result produce structured provenance."""

    def test_build_provenance_basic(self):
        """Provenance includes product_info with title."""
        result = SearchResult(
            title="Blue Widget",
            price=25.0,
            merchant="Amazon",
            url="https://amazon.com/widget",
            source="rainforest",
        )
        prov = _build_provenance(result, "rainforest")

        assert prov["product_info"]["title"] == "Blue Widget"
        assert prov["source_provider"] == "rainforest"
        assert isinstance(prov["matched_features"], list)
        assert isinstance(prov["chat_excerpts"], list)
        assert len(prov["chat_excerpts"]) == 0

    def test_build_provenance_high_rating(self):
        """High rating produces a matched feature."""
        result = SearchResult(
            title="Widget",
            price=10.0,
            merchant="Store",
            url="https://store.com/w",
            source="test",
            rating=4.7,
        )
        prov = _build_provenance(result, "test")
        assert any("4.7" in f for f in prov["matched_features"])

    def test_build_provenance_low_rating_excluded(self):
        """Rating <= 4.0 does NOT produce a matched feature."""
        result = SearchResult(
            title="Widget",
            price=10.0,
            merchant="Store",
            url="https://store.com/w",
            source="test",
            rating=3.5,
        )
        prov = _build_provenance(result, "test")
        assert not any("rated" in f.lower() for f in prov["matched_features"])

    def test_build_provenance_shipping_info(self):
        """Shipping info becomes a matched feature."""
        result = SearchResult(
            title="Widget",
            price=10.0,
            merchant="Store",
            url="https://store.com/w",
            source="test",
            shipping_info="Free 2-day shipping",
        )
        prov = _build_provenance(result, "test")
        assert "Free 2-day shipping" in prov["matched_features"]

    def test_build_provenance_popular_reviews(self):
        """Many reviews produces a 'Popular' matched feature."""
        result = SearchResult(
            title="Widget",
            price=10.0,
            merchant="Store",
            url="https://store.com/w",
            source="test",
            reviews_count=500,
        )
        prov = _build_provenance(result, "test")
        assert any("500" in f for f in prov["matched_features"])

    def test_build_provenance_low_reviews_excluded(self):
        """Reviews <= 100 does NOT produce a feature."""
        result = SearchResult(
            title="Widget",
            price=10.0,
            merchant="Store",
            url="https://store.com/w",
            source="test",
            reviews_count=50,
        )
        prov = _build_provenance(result, "test")
        assert not any("review" in f.lower() for f in prov["matched_features"])

    def test_build_provenance_high_match_score(self):
        """match_score > 0.7 produces 'Strong match' feature."""
        result = SearchResult(
            title="Widget",
            price=10.0,
            merchant="Store",
            url="https://store.com/w",
            source="test",
            match_score=0.85,
        )
        prov = _build_provenance(result, "test")
        assert any("Strong match" in f for f in prov["matched_features"])

    def test_build_provenance_combined(self):
        """Multiple signals produce multiple matched features."""
        result = SearchResult(
            title="Premium Widget",
            price=50.0,
            merchant="TopStore",
            url="https://topstore.com/w",
            source="rainforest",
            rating=4.8,
            reviews_count=1200,
            shipping_info="Free shipping",
            match_score=0.9,
        )
        prov = _build_provenance(result, "rainforest")
        assert len(prov["matched_features"]) == 4

    def test_normalize_result_includes_provenance(self):
        """_normalize_result populates provenance on NormalizedResult."""
        result = SearchResult(
            title="Test Product",
            price=29.99,
            merchant="TestMerchant",
            url="https://test.com/product",
            source="google_cse",
            rating=4.5,
        )
        normalized = _normalize_result(result, "google_cse")

        assert isinstance(normalized.provenance, dict)
        assert normalized.provenance["product_info"]["title"] == "Test Product"
        assert normalized.provenance["source_provider"] == "google_cse"

    def test_normalize_generic_results_all_have_provenance(self):
        """All results from normalize_generic_results have provenance."""
        results = [
            SearchResult(
                title=f"Item {i}",
                price=float(i * 10),
                merchant="Store",
                url=f"https://store.com/{i}",
                source="test",
            )
            for i in range(5)
        ]
        normalized = normalize_generic_results(results, "test")
        assert len(normalized) == 5
        for nr in normalized:
            assert nr.provenance is not None
            assert "product_info" in nr.provenance
            assert "matched_features" in nr.provenance

    def test_normalized_result_provenance_default_empty(self):
        """NormalizedResult provenance defaults to empty dict if not provided."""
        nr = NormalizedResult(
            title="X",
            url="https://x.com",
            source="test",
            merchant_name="X",
            merchant_domain="x.com",
        )
        assert nr.provenance == {}


# ---------------------------------------------------------------------------
# task-002: TestPersistProvenance
# ---------------------------------------------------------------------------

class TestEnrichedProvenance:
    """Verify _build_enriched_provenance merges search intent + chat."""

    def _make_service(self):
        """Create a SourcingService with mocked session/repo."""
        mock_session = MagicMock()
        mock_repo = MagicMock()
        return SourcingService(session=mock_session, sourcing_repo=mock_repo)

    def _make_normalized_result(self, **kwargs):
        defaults = dict(
            title="Test Product",
            url="https://test.com/p",
            source="rainforest",
            merchant_name="TestStore",
            merchant_domain="test.com",
            provenance={
                "product_info": {"title": "Test Product", "brand": None, "specs": {}},
                "matched_features": ["Free shipping"],
                "chat_excerpts": [],
                "source_provider": "rainforest",
            },
        )
        defaults.update(kwargs)
        return NormalizedResult(**defaults)

    def test_enriches_with_keywords(self):
        """Search intent keywords are appended to matched_features."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = {"keywords": ["blue", "widget"]}
        row.chat_history = None

        prov = svc._build_enriched_provenance(res, row)

        assert any("Matches: blue, widget" in f for f in prov["matched_features"])

    def test_enriches_with_brand_from_intent(self):
        """Brand from search intent is set on product_info if not already set."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = {"brand": "Acme", "keywords": []}
        row.chat_history = None

        prov = svc._build_enriched_provenance(res, row)

        assert prov["product_info"]["brand"] == "Acme"

    def test_does_not_overwrite_existing_brand(self):
        """If brand already set in provenance, search intent brand is ignored."""
        svc = self._make_service()
        res = self._make_normalized_result(
            provenance={
                "product_info": {"title": "X", "brand": "Original", "specs": {}},
                "matched_features": [],
                "chat_excerpts": [],
                "source_provider": "test",
            }
        )
        row = MagicMock()
        row.search_intent = {"brand": "Override", "keywords": []}
        row.chat_history = None

        prov = svc._build_enriched_provenance(res, row)

        assert prov["product_info"]["brand"] == "Original"

    def test_enriches_with_features_from_intent(self):
        """Features from search intent are appended to matched_features."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = {
            "keywords": [],
            "features": {"color": "blue", "size": "large"},
        }
        row.chat_history = None

        prov = svc._build_enriched_provenance(res, row)

        assert any("color: blue" in f for f in prov["matched_features"])
        assert any("size: large" in f for f in prov["matched_features"])

    def test_extracts_chat_excerpts(self):
        """Up to 3 user+assistant messages from chat_history become chat_excerpts."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = None
        row.chat_history = [
            {"role": "user", "content": "I need a blue widget"},
            {"role": "assistant", "content": "Sure, let me search"},
            {"role": "user", "content": "Under $50 please"},
            {"role": "user", "content": "Make it large"},
        ]

        prov = svc._build_enriched_provenance(res, row)

        assert len(prov["chat_excerpts"]) == 3
        assert prov["chat_excerpts"][0]["role"] == "user"
        assert prov["chat_excerpts"][0]["content"] == "I need a blue widget"
        assert prov["chat_excerpts"][1]["role"] == "assistant"
        assert prov["chat_excerpts"][2]["role"] == "user"

    def test_chat_excerpts_truncated_to_200_chars(self):
        """Long chat messages are truncated to 200 characters."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = None
        row.chat_history = [
            {"role": "user", "content": "x" * 500},
        ]

        prov = svc._build_enriched_provenance(res, row)

        assert len(prov["chat_excerpts"]) == 1
        assert len(prov["chat_excerpts"][0]["content"]) == 200

    def test_no_row_still_produces_valid_json(self):
        """When row is None, provenance is still valid JSON."""
        svc = self._make_service()
        res = self._make_normalized_result()

        prov = svc._build_enriched_provenance(res, None)

        assert "matched_features" in prov
        assert "product_info" in prov

    def test_malformed_search_intent_handled(self):
        """Malformed search_intent JSON doesn't crash."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = "{ invalid json }"
        row.chat_history = None

        prov = svc._build_enriched_provenance(res, row)
        assert isinstance(prov["matched_features"], list)

    def test_malformed_chat_history_handled(self):
        """Malformed chat_history JSON doesn't crash."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = None
        row.chat_history = "not valid json"

        prov = svc._build_enriched_provenance(res, row)
        assert prov.get("chat_excerpts", []) == []

    def test_preserves_existing_features(self):
        """Existing matched_features from normalizer are preserved."""
        svc = self._make_service()
        res = self._make_normalized_result()
        row = MagicMock()
        row.search_intent = {"keywords": ["extra"]}
        row.chat_history = None

        prov = svc._build_enriched_provenance(res, row)

        # "Free shipping" was in the original provenance
        assert "Free shipping" in prov["matched_features"]
        assert any("extra" in f for f in prov["matched_features"])


# ---------------------------------------------------------------------------
# task-004: TestEndToEndProvenance (BidWithProvenance computed fields)
# ---------------------------------------------------------------------------

class TestBidWithProvenanceComputed:
    """Verify BidWithProvenance computed fields parse enriched provenance."""

    def test_full_provenance_parsed(self):
        """BidWithProvenance correctly parses all provenance sections."""
        provenance = json.dumps({
            "product_info": {
                "title": "Test",
                "brand": "Acme",
                "specs": {"color": "red"},
            },
            "matched_features": ["Highly rated (4.8★)", "Free shipping"],
            "chat_excerpts": [
                {"role": "user", "content": "I want red widgets"},
            ],
        })

        bwp = BidWithProvenance(
            row_id=1,
            price=50.0,
            total_cost=50.0,
            item_title="Test",
            provenance=provenance,
        )

        assert bwp.provenance_data is not None
        assert bwp.product_info["brand"] == "Acme"
        assert len(bwp.matched_features) == 2
        assert bwp.matched_features[0] == "Highly rated (4.8★)"
        assert len(bwp.chat_excerpts) == 1
        assert bwp.chat_excerpts[0]["content"] == "I want red widgets"

    def test_null_provenance_returns_none(self):
        """Null provenance returns None for all computed fields."""
        bwp = BidWithProvenance(
            row_id=1,
            price=50.0,
            total_cost=50.0,
            item_title="Test",
            provenance=None,
        )

        assert bwp.provenance_data is None
        assert bwp.product_info is None
        assert bwp.matched_features is None
        assert bwp.chat_excerpts is None

    def test_empty_provenance_returns_none(self):
        """Empty provenance dict is falsy — computed fields return None."""
        bwp = BidWithProvenance(
            row_id=1,
            price=50.0,
            total_cost=50.0,
            item_title="Test",
            provenance=json.dumps({}),
        )

        assert bwp.provenance_data == {}
        assert bwp.product_info is None
        assert bwp.matched_features is None
        assert bwp.chat_excerpts is None

    def test_malformed_provenance_returns_none(self):
        """Malformed provenance JSON returns None gracefully."""
        bwp = BidWithProvenance(
            row_id=1,
            price=50.0,
            total_cost=50.0,
            item_title="Test",
            provenance="{ broken json",
        )

        assert bwp.provenance_data is None
