"""Coupon/swap offer models for Pop savings agent."""

from typing import Optional
from datetime import datetime
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
