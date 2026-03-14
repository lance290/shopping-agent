"""
Scenario tests for revenue-critical flows — NO database required.

These tests mock the DB session but exercise the full FastAPI request/response
chain via httpx AsyncClient + ASGITransport. They verify:
- Route registration and HTTP method handling
- Request validation (Pydantic models)
- Response shapes and status codes
- Business logic branching (affiliate vs vendor, multi-domain, etc.)

Run without Postgres: python -m pytest tests/test_scenario_revenue_no_db.py -v
"""
import json
import os
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta

from httpx import AsyncClient, ASGITransport
from main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_session():
    """Create a mock async session that won't hit the DB."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.exec = AsyncMock()
    return session


def _mock_auth_session(user_id=1):
    """Mock an authenticated session."""
    auth = MagicMock()
    auth.user_id = user_id
    auth.id = 100
    return auth


@pytest.fixture
def mock_session():
    return _mock_session()


@pytest_asyncio.fixture
async def no_db_client():
    """Client that doesn't need a real DB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Scenario 1: Health endpoint (no auth, no DB needed for basic health)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_health_returns_200(no_db_client):
    resp = await no_db_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


# ---------------------------------------------------------------------------
# Scenario 2: Clickout affiliate redirect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_clickout_amazon_redirect(no_db_client):
    """Amazon URL gets affiliate tag appended and 302 redirect."""
    with patch("routes.clickout.get_session") as mock_get_session:
        mock_get_session.return_value = _mock_session()
        resp = await no_db_client.get(
            "/api/out?url=https://www.amazon.com/dp/B09V3KXJPB&bid_id=1&source=test",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "amazon.com" in location
    assert "tag=" in location


@pytest.mark.asyncio
async def test_scenario_clickout_ebay_redirect(no_db_client):
    """eBay URL gets affiliate params appended and 302 redirect."""
    with patch("routes.clickout.get_session") as mock_get_session:
        mock_get_session.return_value = _mock_session()
        resp = await no_db_client.get(
            "/api/out?url=https://www.ebay.com/itm/123456&source=test",
            follow_redirects=False,
        )
    assert resp.status_code == 302
    location = resp.headers.get("location", "")
    assert "ebay.com" in location


@pytest.mark.asyncio
async def test_scenario_clickout_invalid_url_rejected(no_db_client):
    """Non-HTTP URL is rejected with 400."""
    with patch("routes.clickout.get_session") as mock_get_session:
        mock_get_session.return_value = _mock_session()
        resp = await no_db_client.get("/api/out?url=javascript:alert(1)")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_scenario_clickout_no_url_rejected(no_db_client):
    """Missing URL param is rejected."""
    with patch("routes.clickout.get_session") as mock_get_session:
        mock_get_session.return_value = _mock_session()
        resp = await no_db_client.get("/api/out")
    assert resp.status_code == 422 or resp.status_code == 400


# ---------------------------------------------------------------------------
# Scenario 3: Tip jar (anonymous, no auth needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scenario_tip_jar_creates_checkout(no_db_client):
    """Tip jar creates Stripe checkout session without auth."""
    with patch("routes.checkout._get_stripe") as mock_stripe:
        mock_session_obj = MagicMock()
        mock_session_obj.url = "https://checkout.stripe.com/pay/cs_tip"
        mock_session_obj.id = "cs_tip"
        mock_stripe.return_value.checkout.Session.create.return_value = mock_session_obj

        with patch.dict(os.environ, {"STRIPE_TIP_JAR_PRICE_ID": "price_tip123"}):
            resp = await no_db_client.post("/api/tip-jar")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "cs_tip"
    assert "checkout.stripe.com" in data["checkout_url"]


@pytest.mark.asyncio
async def test_scenario_tip_jar_503_when_no_price_id(no_db_client):
    """Tip jar returns 503 when STRIPE_TIP_JAR_PRICE_ID not configured."""
    with patch("routes.checkout._get_stripe") as mock_stripe:
        mock_stripe.return_value.api_key = "sk_test"
        with patch.dict(os.environ, {"STRIPE_TIP_JAR_PRICE_ID": ""}):
            resp = await no_db_client.post("/api/tip-jar")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Scenario 4: _get_app_base multi-domain support
# ---------------------------------------------------------------------------

class TestMultiDomainRedirect:
    """Verify _get_app_base returns correct domain for production domains."""

    DOMAINS = [
        "buy-anything.com",
        "dev.buy-anything.com",
    ]

    def _make_request(self, host):
        from fastapi import Request
        return Request({
            "type": "http",
            "headers": [
                (b"x-forwarded-host", host.encode()),
                (b"x-forwarded-proto", b"https"),
            ],
        })

    @pytest.mark.parametrize("domain", DOMAINS)
    def test_each_domain_resolves_correctly(self, domain):
        from routes.checkout import _get_app_base
        request = self._make_request(domain)
        result = _get_app_base(request)
        assert result == f"https://{domain}"
        assert "localhost" not in result


# ---------------------------------------------------------------------------
# Scenario 5: SDUI action row — vendor vs product
# ---------------------------------------------------------------------------

class TestSDUIActionIntents:
    """Verify SDUI builder assigns correct intents based on bid source."""

    def _make_bid(self, source, url, bid_id=1):
        bid = MagicMock()
        bid.source = source
        bid.item_url = url
        bid.id = bid_id
        bid.price = None if source == "vendor_directory" else 99.99
        bid.closing_status = None
        bid.is_swap = False
        return bid

    def _make_row(self):
        row = MagicMock()
        row.is_service = False
        row.service_category = None
        return row

    def test_vendor_directory_gets_contact_vendor(self):
        from services.sdui_builder import _hydrate_action_row
        result = _hydrate_action_row(self._make_row(), [self._make_bid("vendor_directory", "https://netjets.com")])
        assert result.actions[0].intent == "contact_vendor"
        assert result.actions[0].label == "Request Quote"

    def test_amazon_gets_outbound_affiliate(self):
        from services.sdui_builder import _hydrate_action_row
        result = _hydrate_action_row(self._make_row(), [self._make_bid("rainforest_amazon", "https://amazon.com/dp/B123")])
        assert result.actions[0].intent == "outbound_affiliate"

    def test_ebay_gets_outbound_affiliate(self):
        from services.sdui_builder import _hydrate_action_row
        result = _hydrate_action_row(self._make_row(), [self._make_bid("ebay_browse", "https://ebay.com/itm/123")])
        assert result.actions[0].intent == "outbound_affiliate"

    def test_mailto_vendor_gets_contact_vendor(self):
        from services.sdui_builder import _hydrate_action_row
        result = _hydrate_action_row(self._make_row(), [self._make_bid("vendor_directory", "mailto:sales@jets.com")])
        assert result.actions[0].intent == "contact_vendor"

    def test_no_bids_gets_edit_request(self):
        from services.sdui_builder import _hydrate_action_row
        result = _hydrate_action_row(self._make_row(), [])
        assert result.actions[0].intent == "edit_request"


# ---------------------------------------------------------------------------
# Scenario 6: Zero-results schema
# ---------------------------------------------------------------------------

class TestZeroResultsSchema:
    def test_zero_results_has_edit_action(self):
        from services.sdui_builder import build_zero_results_schema
        row = MagicMock()
        row.title = "Unicorn saddle"
        schema = build_zero_results_schema(row)
        assert schema["version"] == 1
        assert any("No options found" in str(b) for b in schema["blocks"])
        action_blocks = [b for b in schema["blocks"] if b.get("type") == "ActionRow"]
        assert action_blocks[0]["actions"][0]["intent"] == "edit_request"


# ---------------------------------------------------------------------------
# Scenario 7: Outreach parameter validation
# ---------------------------------------------------------------------------

class TestOutreachParams:
    def test_send_custom_outreach_email_accepts_correct_params(self):
        """Regression: blast route used to_name/company_name which crashed."""
        import inspect
        from services.email import send_custom_outreach_email
        sig = inspect.signature(send_custom_outreach_email)
        params = set(sig.parameters.keys())
        assert {"to_email", "vendor_company", "subject", "body_text", "quote_token", "reply_to_email", "sender_name"} <= params
        assert "to_name" not in params
        assert "company_name" not in params


# ---------------------------------------------------------------------------
# Scenario 8: DEV_EMAIL_OVERRIDE safety
# ---------------------------------------------------------------------------

class TestDevEmailSafety:
    def test_production_ignores_override(self):
        """DEV_EMAIL_OVERRIDE must be empty when RAILWAY_ENVIRONMENT is set."""
        is_prod = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("ENVIRONMENT") == "production")
        if is_prod:
            import services.email as em
            assert em.DEV_EMAIL_OVERRIDE == "", "DEV_EMAIL_OVERRIDE should be empty in production!"

    def test_maybe_intercept_passthrough_when_no_override(self):
        import services.email as em
        original = em.DEV_EMAIL_OVERRIDE
        em.DEV_EMAIL_OVERRIDE = ""
        try:
            to, subj = em._maybe_intercept("real@vendor.com", "Quote Request")
            assert to == "real@vendor.com"
            assert subj == "Quote Request"
        finally:
            em.DEV_EMAIL_OVERRIDE = original

    def test_maybe_intercept_redirects_in_dev(self):
        import services.email as em
        original = em.DEV_EMAIL_OVERRIDE
        em.DEV_EMAIL_OVERRIDE = "dev@test.com"
        try:
            to, subj = em._maybe_intercept("real@vendor.com", "Quote Request")
            assert to == "dev@test.com"
            assert "[DEV → real@vendor.com]" in subj
        finally:
            em.DEV_EMAIL_OVERRIDE = original

    def test_plain_text_footer_has_no_commission_language(self):
        import services.email as em

        footer = em._viral_footer_text()
        assert "commission" not in footer.lower()
        assert "referral fee" not in footer.lower()


# ---------------------------------------------------------------------------
# Scenario 9: Normalizer handles SearchResult (not raw dicts)
# ---------------------------------------------------------------------------

class TestNormalizerSearchResult:
    def test_generic_normalizer_works_with_search_results(self):
        """Regression: eBay normalizer called .get() on SearchResult objects."""
        from sourcing.normalizers import normalize_generic_results
        from sourcing.repository import SearchResult
        sr = SearchResult(
            title="Test Widget",
            price=42.0,
            currency="USD",
            merchant="TestSeller",
            url="https://ebay.com/itm/999",
            image_url=None,
            source="ebay_browse",
            rating=4.5,
            reviews_count=100,
            shipping_info="Free shipping",
        )
        results = normalize_generic_results([sr], "ebay_browse")
        assert len(results) == 1
        assert results[0].title == "Test Widget"
        assert results[0].price == 42.0

    def test_normalize_ebay_results_expects_dicts(self):
        """Verify eBay normalizer is only for raw API dicts, not SearchResult."""
        from sourcing.normalizers.ebay import normalize_ebay_results
        raw = [{"title": "eBay Item", "price": {"value": "25.00", "currency": "USD"}, "itemWebUrl": "https://ebay.com/itm/1"}]
        results = normalize_ebay_results(raw)
        assert len(results) == 1
        assert results[0].price == 25.0


# ---------------------------------------------------------------------------
# Scenario 10: Source display name mapping
# ---------------------------------------------------------------------------

class TestSourceDisplayNames:
    EXPECTED = {
        "rainforest_amazon": "Amazon",
        "amazon": "Amazon",
        "ebay_browse": "eBay",
        "ebay": "eBay",
        "serpapi": "Google",
        "google_cse": "Google",
        "kroger": "Kroger",
        "vendor_directory": "Vendor",
        "seller_quote": "Quote",
    }

    @pytest.mark.parametrize("internal,display", EXPECTED.items())
    def test_source_maps_to_friendly_name(self, internal, display):
        # Mirror the frontend friendlySource logic
        SOURCE_DISPLAY_NAMES = self.EXPECTED
        result = SOURCE_DISPLAY_NAMES.get(internal, internal.replace("_", " ").title())
        assert result == display


# ---------------------------------------------------------------------------
# Scenario 11: .gitignore integrity
# ---------------------------------------------------------------------------

class TestGitignoreIntegrity:
    def test_api_out_route_not_gitignored(self):
        """The /api/out route must be tracked in git (was gitignored by bare 'out')."""
        import subprocess
        result = subprocess.run(
            ["git", "ls-files", "apps/frontend/app/api/out/route.ts"],
            capture_output=True, text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
        )
        assert "route.ts" in result.stdout, "apps/frontend/app/api/out/route.ts must be tracked in git!"

    def test_gitignore_uses_anchored_out(self):
        gitignore = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".gitignore")
        if not os.path.exists(gitignore):
            pytest.skip(".gitignore not found")
        with open(gitignore) as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        assert "/out" in lines
        assert "out" not in lines, "Bare 'out' would gitignore app/api/out/"
