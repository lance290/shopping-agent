"""Coupon/swap offer models for Pop savings agent."""

import secrets
from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import Field, SQLModel


class PopSwap(SQLModel, table=True):
    """
    A coupon, rebate, or swap offer sourced from any CouponProvider.

    Unlike Bid (which represents a specific product search result), PopSwap
    represents a brand-funded incentive: "Buy X instead of Y and save $Z."

    Providers:
      - manual: Admin-uploaded via CSV or API
      - homebrew: Brand self-served via portal
      - ibotta: Future IPN integration
      - groflo: Reserved (no API available as of Feb 2026)
    """
    __tablename__ = "pop_swap"

    id: Optional[int] = Field(default=None, primary_key=True)

    # What product/category this swap targets
    category: str = Field(index=True)           # e.g. "steak sauce", "milk", "eggs"
    target_product: Optional[str] = None        # e.g. "A1 Steak Sauce" (what shopper wants)
    swap_product_name: str                       # e.g. "Heinz 57 Sauce" (what brand offers)
    swap_product_image: Optional[str] = None
    swap_product_url: Optional[str] = None       # Link to product page or coupon landing

    # Offer details
    offer_type: str = "coupon"                   # coupon, bogo, discount, rebate, free_trial
    savings_cents: int = 0                       # e.g. 250 = $2.50 off
    discount_percent: Optional[float] = None     # e.g. 0.25 = 25% off (alternative to cents)
    offer_description: Optional[str] = None      # Human-readable: "Save $2.50 on Heinz 57"
    terms: Optional[str] = None                  # Fine print / restrictions

    # Brand info
    brand_name: Optional[str] = None             # e.g. "Heinz"
    brand_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    brand_contact_email: Optional[str] = None

    # Provider sourcing
    provider: str = "manual"                     # manual, homebrew, ibotta, groflo
    provider_offer_id: Optional[str] = None      # External ID from provider (e.g. Ibotta offer_id)
    provider_payout_cents: Optional[int] = None  # What provider pays us per redemption

    # Lifecycle
    is_active: bool = True
    expires_at: Optional[datetime] = None
    max_redemptions: Optional[int] = None        # None = unlimited
    current_redemptions: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class PopSwapClaim(SQLModel, table=True):
    """
    Record of a user claiming a PopSwap offer.
    Links a swap to a specific user + row (list item).
    Tracks through claim → purchase → receipt_verified → paid.
    """
    __tablename__ = "pop_swap_claim"

    id: Optional[int] = Field(default=None, primary_key=True)
    swap_id: int = Field(foreign_key="pop_swap.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    row_id: Optional[int] = Field(default=None, foreign_key="row.id")

    status: str = "claimed"  # claimed, purchased, receipt_verified, paid, expired, canceled

    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    receipt_id: Optional[str] = Field(default=None, foreign_key="receipt.id")


class Campaign(SQLModel, table=True):
    """
    A funded rebate campaign where a CPG brand pre-pays credits to conquest
    competitor products. When a shopper buys the swap product and scans their
    receipt, the campaign budget is debited and the shopper's wallet is credited.

    Distinct from CouponCampaign (outreach tracking) — this model holds real money.
    """
    __tablename__ = "campaign"

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    name: str
    swap_product_name: str
    swap_product_image: Optional[str] = None
    swap_product_url: Optional[str] = None
    budget_total_cents: int = 0
    budget_remaining_cents: int = 0
    payout_per_swap_cents: int = 0
    target_categories: Optional[str] = None
    target_competitors: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "active"  # active, paused, depleted, expired
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    @property
    def is_active_now(self) -> bool:
        now = datetime.utcnow()
        if self.status != "active":
            return False
        if self.budget_remaining_cents <= 0:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class CouponCampaign(SQLModel, table=True):
    """
    Tracks a brand outreach campaign (PRD-08).

    When high-velocity items lack active coupons, the system creates a campaign
    and sends a magic link to the brand PM. The PM uses the link to submit a
    coupon via the brand portal.
    """
    __tablename__ = "coupon_campaign"

    id: Optional[int] = Field(default=None, primary_key=True)
    brand_name: str = Field(index=True)
    brand_contact_email: Optional[str] = None
    category: str                              # e.g. "laundry detergent"
    target_product: Optional[str] = None       # e.g. "Tide Pods 42ct"
    intent_count: int = 0                      # how many users want this product
    status: str = "pending"                    # pending, sent, claimed, expired
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    swap_id: Optional[int] = Field(default=None, foreign_key="pop_swap.id")


def _default_token() -> str:
    return secrets.token_urlsafe(32)


def _default_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=7)


class BrandPortalToken(SQLModel, table=True):
    """
    Magic-link token for brand portal access (PRD-08).

    A PM receives a URL like /brands/claim?token=XYZ. The token maps to
    a campaign so the PM can submit a coupon for the right product.
    """
    __tablename__ = "brand_portal_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(default_factory=_default_token, index=True, unique=True)
    campaign_id: int = Field(foreign_key="coupon_campaign.id")
    brand_email: Optional[str] = None
    is_used: bool = False
    expires_at: datetime = Field(default_factory=_default_expiry)
    created_at: datetime = Field(default_factory=datetime.utcnow)
