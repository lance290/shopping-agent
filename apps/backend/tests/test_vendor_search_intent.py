"""
Iron-clad tests for LLM intent-driven vendor search.

These tests enforce:
1. _weighted_blend produces correct normalized vectors
2. extract_vendor_query reads product_name from search_intent
3. Vector similarity flows through normalizer → scorer pipeline
4. Vendor provider uses vendor_query (intent) not raw query (noise)
5. Repository routes vendor_query to vendor_directory only

If any of these tests fail, the LLM's understanding of user intent
is no longer driving vendor search results.
"""

import json
import math
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from sourcing.models import NormalizedResult, SearchIntent
from sourcing.scorer import score_results, _relevance_score


# =============================================================================
# 1. Weighted Embedding Blend — Math Correctness
# =============================================================================

class TestWeightedBlend:
    """_weighted_blend must produce correct weighted + normalized vectors."""

    def _get_blend(self):
        from sourcing.vendor_provider import _weighted_blend
        return _weighted_blend

    def test_single_vector_unchanged(self):
        """A single vector with weight 1.0 should be returned normalized."""
        blend = self._get_blend()
        vec = [3.0, 4.0]  # norm = 5
        result = blend([vec], [1.0])
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6

    def test_output_is_unit_length(self):
        """Blended vector must be L2-normalized (unit length)."""
        blend = self._get_blend()
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        result = blend([v1, v2], [0.7, 0.3])
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-6, f"Expected unit length, got {norm}"

    def test_70_30_weights_favor_first(self):
        """70/30 blend should be closer to the first vector."""
        blend = self._get_blend()
        v1 = [1.0, 0.0]  # "private jet charter"
        v2 = [0.0, 1.0]  # "nashville"
        result = blend([v1, v2], [0.7, 0.3])
        # v1 component should be larger than v2 component
        assert result[0] > result[1], (
            f"70% weight vector should dominate: got [{result[0]:.3f}, {result[1]:.3f}]"
        )

    def test_equal_weights_equal_components(self):
        """50/50 blend of orthogonal unit vectors should have equal components."""
        blend = self._get_blend()
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        result = blend([v1, v2], [0.5, 0.5])
        assert abs(result[0] - result[1]) < 1e-6

    def test_identical_vectors_stay_identical(self):
        """Blending identical vectors should return the same direction."""
        blend = self._get_blend()
        v1 = [0.6, 0.8]
        result = blend([v1, v1], [0.7, 0.3])
        # Should be normalized version of v1
        assert abs(result[0] - 0.6) < 1e-6
        assert abs(result[1] - 0.8) < 1e-6

    def test_high_dimensional(self):
        """Works with 1536-dim vectors (production size)."""
        blend = self._get_blend()
        import random
        random.seed(42)
        v1 = [random.gauss(0, 1) for _ in range(1536)]
        v2 = [random.gauss(0, 1) for _ in range(1536)]
        result = blend([v1, v2], [0.7, 0.3])
        assert len(result) == 1536
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-6

    def test_zero_vector_handled(self):
        """If one vector is all zeros, blend should still normalize."""
        blend = self._get_blend()
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 0.0, 0.0]
        result = blend([v1, v2], [0.7, 0.3])
        norm = math.sqrt(sum(x * x for x in result))
        assert abs(norm - 1.0) < 1e-6


# =============================================================================
# 2. extract_vendor_query — LLM Intent Extraction
# =============================================================================

class TestExtractVendorQuery:
    """extract_vendor_query must correctly extract product_name from search_intent."""

    def _get_svc(self):
        from sourcing.service import SourcingService
        return SourcingService

    def _make_row(self, search_intent=None):
        row = MagicMock()
        row.search_intent = search_intent if search_intent else None
        return row

    def test_extracts_product_name(self):
        svc = self._get_svc()
        row = self._make_row({"product_name": "Private jet charter", "raw_input": "jet to nashville"})
        result = svc.extract_vendor_query(row)
        assert result == "Private jet charter"

    def test_falls_back_to_raw_input(self):
        svc = self._get_svc()
        row = self._make_row({"raw_input": "custom jewelry"})
        result = svc.extract_vendor_query(row)
        assert result == "custom jewelry"

    def test_prefers_product_name_over_raw_input(self):
        svc = self._get_svc()
        row = self._make_row({
            "product_name": "Diamond engagement ring",
            "raw_input": "ring for my girlfriend something nice maybe diamond"
        })
        result = svc.extract_vendor_query(row)
        assert result == "Diamond engagement ring"

    def test_returns_none_for_no_intent(self):
        svc = self._get_svc()
        row = self._make_row(None)
        result = svc.extract_vendor_query(row)
        assert result is None

    def test_returns_none_for_empty_intent(self):
        svc = self._get_svc()
        row = self._make_row({})
        result = svc.extract_vendor_query(row)
        assert result is None

    def test_returns_none_for_null_row(self):
        svc = self._get_svc()
        result = svc.extract_vendor_query(None)
        assert result is None

    def test_handles_malformed_json(self):
        svc = self._get_svc()
        row = MagicMock()
        row.search_intent = "not valid json {{"
        result = svc.extract_vendor_query(row)
        assert result is None

    def test_real_jet_charter_intent(self):
        """Regression: the exact intent from a 'jet to nashville' search."""
        svc = self._get_svc()
        row = self._make_row({
            "product_category": "private_aviation",
            "product_name": "Private jet charter",
            "keywords": ["private", "jet", "charter"],
            "raw_input": "Private jet charter",
            "min_price": None,
            "max_price": None,
        })
        result = svc.extract_vendor_query(row)
        assert result == "Private jet charter"

    def test_real_roblox_intent(self):
        """Regression: the exact intent from a Roblox gift card search."""
        svc = self._get_svc()
        row = self._make_row({
            "product_category": "gift_cards",
            "product_name": "Roblox gift card",
            "keywords": ["roblox", "gift", "card"],
            "raw_input": "Roblox gift card",
            "min_price": 50.01,
        })
        result = svc.extract_vendor_query(row)
        assert result == "Roblox gift card"


# =============================================================================
# 3. Vector Similarity Scoring — Scorer Uses Embedding Distance
# =============================================================================

class TestVectorSimilarityScoring:
    """Scorer must use vector_similarity for vendor results, not keyword matching."""

    def _make_vendor_result(self, name, vec_sim):
        return NormalizedResult(
            title=name,
            url=f"https://{name.lower().replace(' ', '')}.com",
            source="vendor_directory",
            merchant_name=name,
            merchant_domain=f"{name.lower().replace(' ', '')}.com",
            provenance={"vector_similarity": vec_sim},
        )

    def _make_marketplace_result(self, title, source="rainforest"):
        return NormalizedResult(
            title=title,
            url=f"https://amazon.com/{title.lower().replace(' ', '-')}",
            source=source,
            price=50.0,
            merchant_name="Amazon",
            merchant_domain="amazon.com",
            provenance={},
        )

    def test_high_similarity_vendor_scores_higher(self):
        """Vendor with high vector similarity should score higher than low."""
        high = self._make_vendor_result("Jettly", 0.62)  # 1 - 0.38 distance
        low = self._make_vendor_result("Random Nashville Hotel", 0.46)  # 1 - 0.54 distance
        
        high_score = _relevance_score(high, None)
        low_score = _relevance_score(low, None)
        
        assert high_score > low_score, (
            f"Jettly (sim={0.62}) scored {high_score:.3f} vs "
            f"Random Hotel (sim={0.46}) scored {low_score:.3f}"
        )

    def test_vendor_scoring_ignores_keywords(self):
        """Vendor relevance should come from vector_similarity, not name keywords."""
        # "Gepetto" has no keywords matching "toy truck" but has high similarity
        gepetto = self._make_vendor_result("Gepetto", 0.60)
        intent = SearchIntent(keywords=["toy", "truck"], product_category="toys")
        
        score = _relevance_score(gepetto, intent)
        # Should use vector_similarity, NOT fall through to keyword matching
        expected_min = (0.60 - 0.40) / 0.25  # = 0.80
        assert score >= expected_min - 0.01, (
            f"Gepetto should score ~{expected_min:.2f} from vector_similarity, got {score:.3f}"
        )

    def test_marketplace_uses_keyword_matching(self):
        """Marketplace results should still use keyword matching, not vector_similarity."""
        amazon = self._make_marketplace_result("LEGO Toy Truck Set")
        intent = SearchIntent(keywords=["toy", "truck"], product_category="toys")
        
        score = _relevance_score(amazon, intent)
        # Should use keyword matching — both "toy" and "truck" match title
        assert score > 0.3, f"Amazon result with keyword match should score well, got {score:.3f}"

    def test_full_ranking_vendors_by_similarity(self):
        """In a mixed result set, vendors should rank by vector similarity."""
        results = [
            self._make_vendor_result("Jettly", 0.62),
            self._make_vendor_result("PrivateFly", 0.61),
            self._make_vendor_result("Random Nashville Hotel", 0.46),
            self._make_vendor_result("Nashville SC Soccer", 0.44),
        ]
        intent = SearchIntent(keywords=["private", "jet", "charter"], product_category="aviation")
        ranked = score_results(results, intent=intent, desire_tier="service")
        
        # Top 2 should be Jettly and PrivateFly
        top_names = [r.title for r in ranked[:2]]
        assert "Jettly" in top_names
        assert "PrivateFly" in top_names
        
        # Bottom 2 should be the Nashville randoms
        bottom_names = [r.title for r in ranked[2:]]
        assert "Nashville SC Soccer" in bottom_names or "Random Nashville Hotel" in bottom_names

    def test_no_vector_similarity_falls_through(self):
        """If no vector_similarity in provenance, use keyword matching as fallback."""
        result = NormalizedResult(
            title="Some Vendor",
            url="https://somevendor.com",
            source="vendor_directory",
            merchant_name="Some Vendor",
            merchant_domain="somevendor.com",
            provenance={},  # No vector_similarity
        )
        intent = SearchIntent(keywords=["toy"], product_category="toys")
        score = _relevance_score(result, intent)
        # Should fall through to keyword matching (base 0.05)
        assert score >= 0.05


# =============================================================================
# 4. Normalizer Preserves vector_similarity
# =============================================================================

class TestNormalizerPreservesVectorSimilarity:
    """The normalizer must preserve match_score as vector_similarity in provenance."""

    def test_match_score_flows_to_provenance(self):
        from sourcing.normalizers import _build_provenance
        from sourcing.repository import SearchResult
        
        result = SearchResult(
            title="Jettly",
            merchant="Jettly",
            url="https://jettly.com",
            source="vendor_directory",
            match_score=0.62,
        )
        prov = _build_provenance(result, "vendor_directory")
        assert "vector_similarity" in prov, "match_score not preserved as vector_similarity"
        assert prov["vector_similarity"] == 0.62

    def test_zero_match_score_not_stored(self):
        from sourcing.normalizers import _build_provenance
        from sourcing.repository import SearchResult
        
        result = SearchResult(
            title="Amazon Widget",
            merchant="Amazon",
            url="https://amazon.com/widget",
            source="rainforest",
            match_score=0.0,
        )
        prov = _build_provenance(result, "rainforest")
        assert "vector_similarity" not in prov, "Zero match_score should not be stored"

    def test_no_match_score_not_stored(self):
        from sourcing.normalizers import _build_provenance
        from sourcing.repository import SearchResult
        
        result = SearchResult(
            title="Google Result",
            merchant="Web",
            url="https://example.com",
            source="google_cse",
        )
        prov = _build_provenance(result, "google_cse")
        assert "vector_similarity" not in prov


# =============================================================================
# 5. Repository Routes vendor_query to vendor_directory Only
# =============================================================================

class TestRepositoryVendorQueryRouting:
    """Repository must send vendor_query to vendor_directory, full query to others."""

    @pytest.mark.asyncio
    async def test_vendor_gets_intent_query(self):
        """vendor_directory provider should receive the LLM's product_name."""
        from sourcing.repository import SourcingRepository

        repo = SourcingRepository.__new__(SourcingRepository)
        
        captured_queries = {}
        
        async def mock_vendor_search(query, **kwargs):
            captured_queries["vendor_directory"] = query
            captured_queries["vendor_context"] = kwargs.get("context_query")
            return []
        
        async def mock_web_search(query, **kwargs):
            captured_queries["web"] = query
            return []
        
        vendor_mock = MagicMock()
        vendor_mock.search = mock_vendor_search
        
        web_mock = MagicMock()
        web_mock.search = mock_web_search
        
        repo.providers = {
            "vendor_directory": vendor_mock,
            "rainforest": web_mock,
        }
        
        await repo.search_all_with_status(
            "private jet charter san diego nashville",
            vendor_query="Private jet charter",
        )
        
        assert captured_queries.get("vendor_directory") == "Private jet charter", (
            f"Vendor got '{captured_queries.get('vendor_directory')}' instead of clean intent"
        )
        assert captured_queries.get("vendor_context") == "private jet charter san diego nashville", (
            "Vendor should receive full query as context_query for blending"
        )
        assert captured_queries.get("web") == "private jet charter san diego nashville", (
            "Web providers should get the full query with locations"
        )

    @pytest.mark.asyncio
    async def test_no_vendor_query_falls_back(self):
        """Without vendor_query, vendor_directory should get the raw query."""
        from sourcing.repository import SourcingRepository

        repo = SourcingRepository.__new__(SourcingRepository)
        
        captured_queries = {}
        
        async def mock_search(query, **kwargs):
            captured_queries["query"] = query
            return []
        
        vendor_mock = MagicMock()
        vendor_mock.search = mock_search
        
        repo.providers = {"vendor_directory": vendor_mock}
        
        await repo.search_all_with_status("standing desk")
        
        assert captured_queries.get("query") == "standing desk"
