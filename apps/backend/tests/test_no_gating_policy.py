"""
Regression tests: NO GATING — only re-ranking.

These tests enforce the architectural invariant that:
1. All providers run for ALL queries regardless of desire_tier.
2. No results are ever dropped/filtered by tier — only re-ranked.
3. The chat flow never skips search for any tier (including advisory).
4. Price constraints are extracted from all LLM key variants.

If any of these tests fail, it means someone re-introduced filtering/gating
that violates the "trust providers, only re-rank" policy.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sourcing.models import NormalizedResult, SearchIntent
from sourcing.scorer import score_results


# =============================================================================
# 1. _filter_providers_by_tier MUST be a pass-through
# =============================================================================

class TestProviderTierPassThrough:
    """_filter_providers_by_tier must NEVER filter providers."""

    def _get_repo_with_providers(self):
        """Create a SourcingRepository-like object with mock providers."""
        from sourcing.repository import SourcingRepository

        repo = SourcingRepository.__new__(SourcingRepository)
        repo.providers = {
            "rainforest": MagicMock(),
            "searchapi": MagicMock(),
            "serpapi": MagicMock(),
            "google_cse": MagicMock(),
            "google_shopping": MagicMock(),
            "vendor_directory": MagicMock(),
            "ticketmaster": MagicMock(),
        }
        return repo

    @pytest.mark.parametrize("tier", [
        None, "commodity", "considered", "service", "bespoke", "high_value", "advisory",
        "unknown_future_tier",
    ])
    def test_all_providers_returned_for_every_tier(self, tier):
        repo = self._get_repo_with_providers()
        result = repo._filter_providers_by_tier(repo.providers, desire_tier=tier)
        assert set(result.keys()) == set(repo.providers.keys()), (
            f"Tier '{tier}' filtered providers! Got {set(result.keys())} "
            f"but expected {set(repo.providers.keys())}"
        )

    def test_provider_count_unchanged(self):
        repo = self._get_repo_with_providers()
        for tier in ["commodity", "service", "advisory", "bespoke", None]:
            result = repo._filter_providers_by_tier(repo.providers, desire_tier=tier)
            assert len(result) == len(repo.providers), (
                f"Tier '{tier}' changed provider count from {len(repo.providers)} to {len(result)}"
            )


# =============================================================================
# 2. Scoring re-ranks but NEVER drops results
# =============================================================================

class TestScoringNeverDrops:
    """score_results must return ALL input results — just re-ordered."""

    @pytest.fixture
    def diverse_results(self):
        return [
            NormalizedResult(
                title="Amazon Widget", price=25.0, source="rainforest",
                url="https://amazon.com/widget", merchant_name="Amazon",
                merchant_domain="amazon.com", provenance={}
            ),
            NormalizedResult(
                title="eBay Widget", price=15.0, source="ebay_browse",
                url="https://ebay.com/widget", merchant_name="eBay Seller",
                merchant_domain="ebay.com", provenance={}
            ),
            NormalizedResult(
                title="Local Vendor Widget", price=45.0, source="vendor_directory",
                url="https://localvendor.com/widget", merchant_name="Local Vendor",
                merchant_domain="localvendor.com", provenance={}
            ),
            NormalizedResult(
                title="Google Widget", price=30.0, source="google_shopping",
                url="https://google.com/widget", merchant_name="Google Merchant",
                merchant_domain="google.com", provenance={}
            ),
        ]

    @pytest.mark.parametrize("tier", [
        "commodity", "considered", "service", "bespoke", "high_value", "advisory", None,
    ])
    def test_all_results_preserved_for_every_tier(self, diverse_results, tier):
        intent = SearchIntent(keywords=["widget"], product_category="general")
        ranked = score_results(results=diverse_results, intent=intent, desire_tier=tier)

        assert len(ranked) == len(diverse_results), (
            f"Tier '{tier}' dropped results! Got {len(ranked)} but expected {len(diverse_results)}"
        )

        input_urls = {r.url for r in diverse_results}
        output_urls = {r.url for r in ranked}
        assert input_urls == output_urls, (
            f"Tier '{tier}' lost results! Missing: {input_urls - output_urls}"
        )

    @pytest.mark.parametrize("tier", [
        "commodity", "considered", "service", "bespoke", "high_value", "advisory",
    ])
    def test_vendor_results_never_dropped(self, diverse_results, tier):
        intent = SearchIntent(keywords=["widget"], product_category="general")
        ranked = score_results(results=diverse_results, intent=intent, desire_tier=tier)

        vendor_results = [r for r in ranked if r.source == "vendor_directory"]
        assert len(vendor_results) >= 1, (
            f"Tier '{tier}' dropped vendor_directory results!"
        )

    @pytest.mark.parametrize("tier", [
        "commodity", "considered", "service", "bespoke", "high_value", "advisory",
    ])
    def test_marketplace_results_never_dropped(self, diverse_results, tier):
        intent = SearchIntent(keywords=["widget"], product_category="general")
        ranked = score_results(results=diverse_results, intent=intent, desire_tier=tier)

        marketplace_results = [r for r in ranked if r.source in ("rainforest", "ebay_browse", "google_shopping")]
        assert len(marketplace_results) >= 1, (
            f"Tier '{tier}' dropped marketplace results!"
        )


# =============================================================================
# 3. Price constraint extraction handles all LLM key variants
# =============================================================================

class TestPriceConstraintExtraction:
    """_extract_price_constraints must handle all LLM-generated key formats."""

    def _get_service(self):
        from sourcing.service import SourcingService
        svc = SourcingService.__new__(SourcingService)
        return svc

    def _make_row(self, choice_answers=None, search_intent=None):
        row = MagicMock()
        row.choice_answers = json.dumps(choice_answers) if choice_answers else None
        row.search_intent = json.dumps(search_intent) if search_intent else None
        return row

    def test_min_price_key(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"min_price": 50})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0

    def test_price_min_key(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"price_min": 50})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0

    def test_minimum_price_key(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"minimum_price": 50})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0

    def test_max_price_key(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"max_price": 100})
        min_p, max_p = svc._extract_price_constraints(row)
        assert max_p == 100.0

    def test_price_max_key(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"price_max": 100})
        min_p, max_p = svc._extract_price_constraints(row)
        assert max_p == 100.0

    def test_maximum_price_key(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"maximum_price": 100})
        min_p, max_p = svc._extract_price_constraints(row)
        assert max_p == 100.0

    def test_price_gt_string(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"price": ">50"})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0

    def test_price_lt_string(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"price": "<100"})
        min_p, max_p = svc._extract_price_constraints(row)
        assert max_p == 100.0

    def test_price_range_string(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"price": "50-100"})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0
        assert max_p == 100.0

    def test_price_with_dollar_sign(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"price": ">$50"})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0

    def test_search_intent_takes_priority(self):
        svc = self._get_service()
        row = self._make_row(
            choice_answers={"price_min": 25},
            search_intent={"min_price": 50}
        )
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0, "search_intent should take priority over choice_answers"

    def test_fallback_to_choice_answers_when_intent_null(self):
        svc = self._get_service()
        row = self._make_row(
            choice_answers={"price_min": 50},
            search_intent={"min_price": None, "max_price": None}
        )
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0, "Should fall back to choice_answers when intent has null prices"

    def test_no_constraints_returns_none(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"color": "red"})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p is None
        assert max_p is None

    def test_swapped_min_max_corrected(self):
        svc = self._get_service()
        row = self._make_row(choice_answers={"min_price": 100, "max_price": 50})
        min_p, max_p = svc._extract_price_constraints(row)
        assert min_p == 50.0
        assert max_p == 100.0


# =============================================================================
# 4. Chat flow: search ALWAYS runs (no tier gating)
# =============================================================================

class TestChatNoTierGating:
    """
    Verify that the chat endpoint source code does NOT contain
    tier-based search gating patterns. This is a static analysis test
    that reads chat.py directly to catch regressions.
    """

    def _read_chat_source(self):
        import pathlib
        chat_path = pathlib.Path(__file__).parent.parent / "routes" / "chat.py"
        return chat_path.read_text()

    def test_no_advisory_search_skip(self):
        """Chat must NOT skip search for advisory tier."""
        source = self._read_chat_source()
        assert 'tier != "advisory"' not in source, (
            "Found 'tier != \"advisory\"' in chat.py — search is being gated by tier!"
        )
        assert "tier != 'advisory'" not in source, (
            "Found \"tier != 'advisory'\" in chat.py — search is being gated by tier!"
        )

    def test_no_tier_based_search_conditional(self):
        """Chat must NOT conditionally run search based on tier value."""
        source = self._read_chat_source()
        import re
        gating_pattern = re.compile(
            r'if\s+.*tier.*:.*\n\s+.*_stream_search',
            re.MULTILINE
        )
        matches = gating_pattern.findall(source)
        assert len(matches) == 0, (
            f"Found tier-gated search pattern in chat.py: {matches}"
        )

    def test_no_advisory_else_branch(self):
        """Chat must NOT have an else branch that skips search for advisory."""
        source = self._read_chat_source()
        assert "Advisory tier" not in source, (
            "Found 'Advisory tier' comment in chat.py — suggests advisory skip logic"
        )

    def test_no_empty_results_for_tier(self):
        """Chat must NOT return empty results based on tier classification."""
        source = self._read_chat_source()
        import re
        # Pattern: tier-based conditional that yields empty search_results
        empty_for_tier = re.compile(
            r'tier.*advisory.*\n.*search_results.*\n.*results.*\[\]',
            re.MULTILINE
        )
        matches = empty_for_tier.findall(source)
        assert len(matches) == 0, (
            f"Found tier-gated empty results in chat.py: {matches}"
        )
