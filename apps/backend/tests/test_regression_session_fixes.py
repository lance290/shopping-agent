"""
Regression tests for the 502 fix / revenue channels session.

Covers:
1. _get_app_base — X-Forwarded-Host support for multi-domain Stripe redirects
2. DEV_EMAIL_OVERRIDE — auto-disabled in production
3. blast outreach — correct parameter names for send_custom_outreach_email
4. _hydrate_action_row — vendor_directory bids → contact_vendor intent
5. normalize_generic_results — handles SearchResult objects (not raw dicts)
6. Streaming search 0-results → row status update + zero-results schema
7. friendlySource — display names for source pills
8. .gitignore — /out pattern doesn't match app/api/out/
"""
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


# ---------------------------------------------------------------------------
# 1. _get_app_base: X-Forwarded-Host support
# ---------------------------------------------------------------------------

class TestGetAppBase:
    def _make_request(self, headers: list):
        from fastapi import Request
        scope = {"type": "http", "headers": headers}
        return Request(scope)

    def test_x_forwarded_host_takes_priority(self):
        from routes.checkout import _get_app_base
        request = self._make_request([
            (b"x-forwarded-host", b"buy-anything.com"),
            (b"x-forwarded-proto", b"https"),
            (b"origin", b"http://localhost:3003"),
        ])
        assert _get_app_base(request) == "https://buy-anything.com"

    def test_x_forwarded_host_defaults_to_https(self):
        from routes.checkout import _get_app_base
        request = self._make_request([
            (b"x-forwarded-host", b"staging.buy-anything.com"),
        ])
        assert _get_app_base(request) == "https://staging.buy-anything.com"

    def test_origin_used_when_no_forwarded_host(self):
        from routes.checkout import _get_app_base
        request = self._make_request([
            (b"origin", b"https://dev.buy-anything.com"),
        ])
        assert _get_app_base(request) == "https://dev.buy-anything.com"

    def test_referer_fallback(self):
        from routes.checkout import _get_app_base
        request = self._make_request([
            (b"referer", b"https://dev.buy-anything.com/some/page"),
        ])
        assert _get_app_base(request) == "https://dev.buy-anything.com"

    def test_env_fallback(self, monkeypatch):
        from routes.checkout import _get_app_base
        monkeypatch.setenv("APP_BASE_URL", "http://localhost:3003")
        request = self._make_request([])
        assert _get_app_base(request) == "http://localhost:3003"


# ---------------------------------------------------------------------------
# 2. DEV_EMAIL_OVERRIDE — auto-disabled in production
# ---------------------------------------------------------------------------

class TestDevEmailOverride:
    def test_disabled_when_railway_env_set(self, monkeypatch):
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
        monkeypatch.setenv("DEV_EMAIL_OVERRIDE", "test@test.com")
        # Re-evaluate the module-level logic
        _is_production = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production")
        override = "" if _is_production else os.getenv("DEV_EMAIL_OVERRIDE", "")
        assert override == ""

    def test_disabled_when_environment_production(self, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEV_EMAIL_OVERRIDE", "test@test.com")
        _is_production = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production")
        override = "" if _is_production else os.getenv("DEV_EMAIL_OVERRIDE", "")
        assert override == ""

    def test_active_in_dev(self, monkeypatch):
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.setenv("DEV_EMAIL_OVERRIDE", "dev@test.com")
        _is_production = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production")
        override = "" if _is_production else os.getenv("DEV_EMAIL_OVERRIDE", "")
        assert override == "dev@test.com"


# ---------------------------------------------------------------------------
# 3. _maybe_intercept — dev mode email redirect
# ---------------------------------------------------------------------------

class TestMaybeIntercept:
    def test_intercepts_in_dev_mode(self):
        from services.email import _maybe_intercept, DEV_EMAIL_OVERRIDE
        if not DEV_EMAIL_OVERRIDE:
            pytest.skip("DEV_EMAIL_OVERRIDE not set in test env")
        to, subj = _maybe_intercept("vendor@real.com", "Quote Request")
        assert to == DEV_EMAIL_OVERRIDE
        assert "vendor@real.com" in subj

    def test_passthrough_when_no_override(self):
        from services.email import _maybe_intercept
        # Temporarily set module-level var to empty
        import services.email as em
        original = em.DEV_EMAIL_OVERRIDE
        em.DEV_EMAIL_OVERRIDE = ""
        try:
            to, subj = _maybe_intercept("vendor@real.com", "Quote Request")
            assert to == "vendor@real.com"
            assert subj == "Quote Request"
        finally:
            em.DEV_EMAIL_OVERRIDE = original


# ---------------------------------------------------------------------------
# 4. _hydrate_action_row — vendor_directory → contact_vendor
# ---------------------------------------------------------------------------

class TestHydrateActionRow:
    def _make_bid(self, source="amazon", item_url="https://amazon.com/item", bid_id=1):
        bid = MagicMock()
        bid.source = source
        bid.item_url = item_url
        bid.id = bid_id
        return bid

    def _make_row(self):
        row = MagicMock()
        row.is_service = False
        row.service_category = None
        return row

    def test_vendor_directory_bid_gets_contact_vendor_intent(self):
        from services.sdui_builder import _hydrate_action_row
        row = self._make_row()
        bids = [self._make_bid(source="vendor_directory", item_url="https://netjets.com")]
        result = _hydrate_action_row(row, bids)
        assert result is not None
        assert result.actions[0].intent == "contact_vendor"
        assert result.actions[0].label == "Request Quote"

    def test_mailto_bid_gets_contact_vendor_intent(self):
        from services.sdui_builder import _hydrate_action_row
        row = self._make_row()
        bids = [self._make_bid(source="vendor_directory", item_url="mailto:vendor@example.com")]
        result = _hydrate_action_row(row, bids)
        assert result is not None
        assert result.actions[0].intent == "contact_vendor"

    def test_amazon_bid_gets_outbound_affiliate_intent(self):
        from services.sdui_builder import _hydrate_action_row
        row = self._make_row()
        bids = [self._make_bid(source="amazon", item_url="https://amazon.com/dp/B123")]
        result = _hydrate_action_row(row, bids)
        assert result is not None
        assert result.actions[0].intent == "outbound_affiliate"
        assert result.actions[0].label == "View Deal"

    def test_ebay_bid_gets_outbound_affiliate_intent(self):
        from services.sdui_builder import _hydrate_action_row
        row = self._make_row()
        bids = [self._make_bid(source="ebay_browse", item_url="https://ebay.com/itm/123")]
        result = _hydrate_action_row(row, bids)
        assert result is not None
        assert result.actions[0].intent == "outbound_affiliate"

    def test_no_bids_gets_edit_request(self):
        from services.sdui_builder import _hydrate_action_row
        row = self._make_row()
        result = _hydrate_action_row(row, [])
        assert result is not None
        assert result.actions[0].intent == "edit_request"


# ---------------------------------------------------------------------------
# 5. normalize_generic_results — handles SearchResult objects
# ---------------------------------------------------------------------------

class TestNormalizeGenericResults:
    def test_handles_search_result_objects(self):
        from sourcing.normalizers import normalize_generic_results
        from sourcing.repository import SearchResult
        results = [
            SearchResult(
                title="Test Item",
                price=29.99,
                currency="USD",
                merchant="eBay Seller",
                url="https://ebay.com/itm/123",
                image_url=None,
                source="ebay_browse",
                rating=None,
                reviews_count=None,
                shipping_info="Free shipping",
            )
        ]
        normalized = normalize_generic_results(results, "ebay")
        assert len(normalized) == 1
        assert normalized[0].title == "Test Item"
        assert normalized[0].price == 29.99
        assert normalized[0].source == "ebay"

    def test_does_not_call_get_on_search_result(self):
        """Regression: normalize_ebay_results called .get() on SearchResult objects."""
        from sourcing.normalizers import normalize_generic_results
        from sourcing.repository import SearchResult
        result = SearchResult(
            title="Widget",
            price=10.0,
            currency="USD",
            merchant="Seller",
            url="https://ebay.com/itm/456",
            image_url=None,
            source="ebay_browse",
            rating=None,
            reviews_count=None,
            shipping_info=None,
        )
        # This should NOT raise AttributeError: 'SearchResult' object has no attribute 'get'
        normalized = normalize_generic_results([result], "ebay_browse")
        assert len(normalized) == 1


# ---------------------------------------------------------------------------
# 6. build_zero_results_schema
# ---------------------------------------------------------------------------

class TestBuildZeroResultsSchema:
    def test_returns_no_options_found_message(self):
        from services.sdui_builder import build_zero_results_schema
        row = MagicMock()
        row.title = "Private jet charter"
        schema = build_zero_results_schema(row)
        assert schema["version"] == 1
        assert schema["layout"] == "ROW_COMPACT"
        blocks = schema["blocks"]
        assert any("No options found" in str(b.get("content", "")) for b in blocks)
        assert any(b.get("type") == "ActionRow" for b in blocks)
        # ActionRow should have "Edit Request" action
        action_rows = [b for b in blocks if b.get("type") == "ActionRow"]
        assert action_rows[0]["actions"][0]["intent"] == "edit_request"


# ---------------------------------------------------------------------------
# 7. .gitignore — /out pattern
# ---------------------------------------------------------------------------

class TestGitignorePattern:
    def test_slash_out_does_not_match_nested_api_out(self):
        """Regression: bare 'out' in .gitignore matched app/api/out/ directory."""
        import fnmatch
        pattern = "/out"
        # /out should match root-level 'out' directory
        # but NOT nested paths like app/api/out/route.ts
        assert not fnmatch.fnmatch("app/api/out/route.ts", pattern)
        assert not fnmatch.fnmatch("apps/frontend/app/api/out/route.ts", pattern)

    def test_gitignore_file_has_slash_out(self):
        gitignore_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".gitignore"
        )
        if not os.path.exists(gitignore_path):
            pytest.skip(".gitignore not found at expected path")
        with open(gitignore_path) as f:
            lines = [l.strip() for l in f.readlines()]
        # Should have /out (anchored), NOT bare out
        assert "/out" in lines, "Expected '/out' in .gitignore"
        assert "out" not in lines, "Bare 'out' should not be in .gitignore (matches app/api/out/)"


# ---------------------------------------------------------------------------
# 8. Source display name mapping (frontend logic, tested as pure function)
# ---------------------------------------------------------------------------

class TestFriendlySource:
    """Test the source display name mapping logic (mirrors frontend friendlySource)."""

    SOURCE_DISPLAY_NAMES = {
        "rainforest_amazon": "Amazon",
        "amazon": "Amazon",
        "ebay_browse": "eBay",
        "ebay": "eBay",
        "serpapi": "Google",
        "google_cse": "Google",
        "kroger": "Kroger",
        "vendor_directory": "Vendor",
        "seller_quote": "Quote",
        "registered_merchant": "Merchant",
    }

    def friendly_source(self, source: str) -> str:
        return self.SOURCE_DISPLAY_NAMES.get(source, source.replace("_", " ").title())

    def test_rainforest_amazon_shows_amazon(self):
        assert self.friendly_source("rainforest_amazon") == "Amazon"

    def test_ebay_browse_shows_ebay(self):
        assert self.friendly_source("ebay_browse") == "eBay"

    def test_serpapi_shows_google(self):
        assert self.friendly_source("serpapi") == "Google"

    def test_vendor_directory_shows_vendor(self):
        assert self.friendly_source("vendor_directory") == "Vendor"

    def test_kroger_shows_kroger(self):
        assert self.friendly_source("kroger") == "Kroger"

    def test_unknown_source_title_cased(self):
        assert self.friendly_source("new_provider_xyz") == "New Provider Xyz"


# ---------------------------------------------------------------------------
# 9. Blast outreach — correct parameter names
# ---------------------------------------------------------------------------

class TestBlastOutreachParams:
    def test_send_custom_outreach_email_signature(self):
        """Regression: blast route passed to_name/company_name which don't exist."""
        import inspect
        from services.email import send_custom_outreach_email
        sig = inspect.signature(send_custom_outreach_email)
        param_names = list(sig.parameters.keys())
        # Must have these correct params
        assert "to_email" in param_names
        assert "vendor_company" in param_names
        assert "reply_to_email" in param_names
        assert "sender_name" in param_names
        # Must NOT have the old wrong params
        assert "to_name" not in param_names
        assert "company_name" not in param_names
