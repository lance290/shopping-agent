"""Phase 4 endpoint and model tests.

Tests cover:
- PRD 00: Stripe Connect onboarding, seller earnings
- PRD 04: Seller bookmarks
- PRD 05: Multi-vendor batch checkout
- PRD 09: Admin metrics
- PRD 10: Anti-fraud detection, clickout fraud fields
- PRD 11: User signals, user preferences, score persistence
- PRD 12: Outreach timeout monitoring
- Model field additions across all PRDs
"""

import pytest
from datetime import datetime, timedelta

# ── Model Tests ──────────────────────────────────────────────────────────


def test_bid_score_fields():
    """PRD 11: Bid model has personalized ranking score fields."""
    from models import Bid
    bid = Bid(
        row_id=1,
        seller_id=1,
        price=100.0,
        combined_score=0.85,
        relevance_score=0.90,
        price_score=0.70,
        quality_score=0.80,
        diversity_bonus=0.95,
        source_tier="marketplace",
    )
    assert bid.combined_score == 0.85
    assert bid.relevance_score == 0.90
    assert bid.price_score == 0.70
    assert bid.quality_score == 0.80
    assert bid.diversity_bonus == 0.95
    assert bid.source_tier == "marketplace"


def test_bid_score_fields_default_none():
    """PRD 11: Score fields default to None."""
    from models import Bid
    bid = Bid(row_id=1, seller_id=1, price=50.0)
    assert bid.combined_score is None
    assert bid.relevance_score is None
    assert bid.source_tier is None


def test_clickout_event_fraud_fields():
    """PRD 10: ClickoutEvent has anti-fraud fields."""
    from models import ClickoutEvent
    event = ClickoutEvent(
        canonical_url="https://example.com/item",
        is_suspicious=True,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0 test-bot",
    )
    assert event.is_suspicious is True
    assert event.ip_address == "192.168.1.1"
    assert event.user_agent == "Mozilla/5.0 test-bot"


def test_clickout_event_fraud_defaults():
    """PRD 10: Fraud fields default to safe values."""
    from models import ClickoutEvent
    event = ClickoutEvent(canonical_url="https://example.com/item")
    assert event.is_suspicious is False
    assert event.ip_address is None
    assert event.user_agent is None


def test_user_trust_level():
    """PRD 10: User model has trust_level field."""
    from models import User
    user = User(trust_level="trusted")
    assert user.trust_level == "trusted"

    default_user = User()
    assert default_user.trust_level == "standard"


def test_merchant_verification_fields():
    """PRD 10: Merchant model has verification and reputation fields."""
    from models import Merchant
    merchant = Merchant(
        business_name="Test Corp",
        contact_name="Test",
        email="test@example.com",
        verification_level="email_verified",
        reputation_score=4.5,
    )
    assert merchant.verification_level == "email_verified"
    assert merchant.reputation_score == 4.5

    default_merchant = Merchant(
        business_name="Default",
        contact_name="Default",
        email="default@example.com",
    )
    assert default_merchant.verification_level == "unverified"
    assert default_merchant.reputation_score == 0.0


def test_outreach_event_timeout_fields():
    """PRD 12: OutreachEvent has timeout tracking fields."""
    from models import OutreachEvent
    now = datetime.utcnow()
    event = OutreachEvent(
        row_id=1,
        vendor_email="vendor@example.com",
        status="sent",
        timeout_hours=72,
        expired_at=now,
        followup_sent_at=now,
    )
    assert event.status == "sent"
    assert event.timeout_hours == 72
    assert event.expired_at == now
    assert event.followup_sent_at == now

    default_event = OutreachEvent(
        row_id=1,
        vendor_email="vendor@example.com",
    )
    assert default_event.status == "pending"
    assert default_event.timeout_hours == 48
    assert default_event.expired_at is None
    assert default_event.followup_sent_at is None


def test_user_signal_model():
    """PRD 11: UserSignal model for ranking personalization."""
    from models import UserSignal
    signal = UserSignal(
        user_id=1,
        bid_id=42,
        row_id=10,
        signal_type="thumbs_up",
        value=1.0,
    )
    assert signal.user_id == 1
    assert signal.bid_id == 42
    assert signal.signal_type == "thumbs_up"
    assert signal.value == 1.0


def test_user_preference_model():
    """PRD 11: UserPreference model for learned preferences."""
    from models import UserPreference
    pref = UserPreference(
        user_id=1,
        preference_key="brand",
        preference_value="Nike",
        weight=2.5,
    )
    assert pref.preference_key == "brand"
    assert pref.preference_value == "Nike"
    assert pref.weight == 2.5


def test_seller_bookmark_model():
    """PRD 04: SellerBookmark model."""
    from models import SellerBookmark
    bookmark = SellerBookmark(
        merchant_id=1,
        row_id=10,
    )
    assert bookmark.merchant_id == 1
    assert bookmark.row_id == 10


# ── Service Tests ─────────────────────────────────────────────────────────


def test_fraud_assessment_safe():
    """PRD 10: Normal clickout is not flagged."""
    from services.fraud import assess_clickout
    result = assess_clickout(
        ip_address="10.0.0.1",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        user_id=1,
    )
    assert result is False


def test_fraud_assessment_bot_ua():
    """PRD 10: Bot user agents are flagged."""
    from services.fraud import assess_clickout
    result = assess_clickout(
        ip_address="10.0.0.2",
        user_agent="Mozilla/5.0 (compatible; Googlebot/2.1)",
        user_id=None,
    )
    # "bot" is in SUSPICIOUS_PATTERNS
    assert result is True


def test_fraud_assessment_headless():
    """PRD 10: Headless browser user agents are flagged."""
    from services.fraud import assess_clickout
    result = assess_clickout(
        ip_address="10.0.0.3",
        user_agent="HeadlessChrome/120.0.0.0",
        user_id=None,
    )
    assert result is True


def test_fraud_assessment_none_values():
    """PRD 10: None values don't crash."""
    from services.fraud import assess_clickout
    result = assess_clickout(
        ip_address=None,
        user_agent=None,
        user_id=None,
    )
    assert result is False


# ── Scoring Tests ─────────────────────────────────────────────────────────


def test_scorer_dimensions():
    """PRD 11: Scorer enriches provenance with score breakdown."""
    from sourcing.scorer import score_results
    from sourcing.models import NormalizedResult

    results = [
        NormalizedResult(
            title="Test Widget",
            url="https://example.com/widget",
            price=29.99,
            currency="USD",
            source="test",
            merchant_name="Test Store",
            merchant_domain="example.com",
        ),
    ]

    scored = score_results(results)
    assert len(scored) == 1
    assert "score" in scored[0].provenance
    score = scored[0].provenance["score"]
    assert "combined" in score
    assert "price" in score
    assert "relevance" in score
    assert "quality" in score
    assert "diversity" in score
    assert 0 <= score["combined"] <= 1


def test_scorer_ordering():
    """PRD 11: Scorer sorts results by combined score descending."""
    from sourcing.scorer import score_results
    from sourcing.models import NormalizedResult

    results = [
        NormalizedResult(
            title="Expensive Widget",
            url="https://example.com/expensive",
            price=999.99,
            currency="USD",
            source="test",
            merchant_name="Store",
            merchant_domain="example.com",
        ),
        NormalizedResult(
            title="Budget Widget",
            url="https://example.com/budget",
            price=9.99,
            currency="USD",
            source="test",
            merchant_name="Store",
            merchant_domain="example.com",
            rating=4.8,
            reviews_count=500,
        ),
    ]

    scored = score_results(results, max_price=50.0)
    # Budget widget should rank higher with max_price constraint
    assert scored[0].title == "Budget Widget"


# ── Integration-like tests ────────────────────────────────────────────────


def test_checkout_models():
    """PRD 05: Checkout request/response models."""
    from routes.checkout import CheckoutCreateRequest, BatchCheckoutRequest, BatchCheckoutResponse

    # Single checkout
    req = CheckoutCreateRequest(bid_id=1, row_id=1)
    assert req.bid_id == 1
    assert req.success_url == ""

    # Batch checkout
    batch_req = BatchCheckoutRequest(bid_ids=[1, 2, 3], row_id=1)
    assert len(batch_req.bid_ids) == 3

    # Batch response
    resp = BatchCheckoutResponse(
        sessions=[{"bid_id": 1, "checkout_url": "https://checkout.stripe.com/..."}],
        total_amount=150.50,
        currency="USD",
    )
    assert resp.total_amount == 150.50


def test_stripe_connect_response_model():
    """PRD 00: Stripe Connect response models."""
    from routes.stripe_connect import OnboardingResponse, EarningsSummary

    onboard = OnboardingResponse(
        onboarding_url="https://connect.stripe.com/setup/...",
        account_id="acct_123",
    )
    assert onboard.account_id == "acct_123"

    earnings = EarningsSummary(
        total_earnings=1234.56,
        pending_payouts=100.00,
        completed_transactions=42,
        commission_rate=0.05,
    )
    assert earnings.completed_transactions == 42


def test_signal_create_model():
    """PRD 11: Signal creation request model."""
    from routes.signals import SignalCreate

    signal = SignalCreate(
        bid_id=1,
        signal_type="thumbs_up",
        value=1.0,
    )
    assert signal.signal_type == "thumbs_up"
    assert signal.bid_id == 1


# ── Reputation Service Tests ─────────────────────────────────────────────


def test_reputation_account_maturity_score():
    """PRD 10 R2: Account maturity scoring."""
    from services.reputation import _account_maturity_score
    from models import Merchant

    # New account (< 7 days)
    new_merchant = Merchant(
        business_name="New Corp",
        contact_name="Test",
        email="new@example.com",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    assert _account_maturity_score(new_merchant) == 1.0

    # Week-old account
    week_merchant = Merchant(
        business_name="Week Corp",
        contact_name="Test",
        email="week@example.com",
        created_at=datetime.utcnow() - timedelta(days=14),
    )
    assert _account_maturity_score(week_merchant) == 2.0

    # Month-old account
    month_merchant = Merchant(
        business_name="Month Corp",
        contact_name="Test",
        email="month@example.com",
        created_at=datetime.utcnow() - timedelta(days=60),
    )
    assert _account_maturity_score(month_merchant) == 3.0

    # Mature account (180+ days)
    mature_merchant = Merchant(
        business_name="Old Corp",
        contact_name="Test",
        email="old@example.com",
        created_at=datetime.utcnow() - timedelta(days=200),
    )
    assert _account_maturity_score(mature_merchant) == 5.0


def test_reputation_verification_score():
    """PRD 10 R2: Verification level scoring."""
    from services.reputation import _verification_score
    from models import Merchant

    levels = {
        "unverified": 1.0,
        "email_verified": 2.5,
        "identity_verified": 4.0,
        "premium": 5.0,
    }

    for level, expected in levels.items():
        merchant = Merchant(
            business_name="Test",
            contact_name="Test",
            email=f"{level}@example.com",
            verification_level=level,
        )
        assert _verification_score(merchant) == expected, f"Failed for level {level}"


def test_reputation_unknown_verification_level():
    """PRD 10 R2: Unknown verification level defaults to 1.0."""
    from services.reputation import _verification_score
    from models import Merchant

    merchant = Merchant(
        business_name="Test",
        contact_name="Test",
        email="test@example.com",
        verification_level="unknown_level",
    )
    assert _verification_score(merchant) == 1.0


def test_email_outreach_disclosure():
    """PRD 08 R4: Outreach email templates include affiliate disclosure."""
    import inspect
    from services.email import send_outreach_email, send_reminder_email

    # Check the source code of both functions for disclosure text
    outreach_src = inspect.getsource(send_outreach_email)
    assert "referral fee or commission" in outreach_src, "Outreach email missing disclosure"

    reminder_src = inspect.getsource(send_reminder_email)
    assert "referral fee or commission" in reminder_src, "Reminder email missing disclosure"
