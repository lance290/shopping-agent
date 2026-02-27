"""Deal pipeline models: proxy messaging, escrow, and state machine."""

import secrets
from datetime import datetime
from typing import Optional, Any

import sqlalchemy as sa
from sqlmodel import Field, SQLModel, Column


class Deal(SQLModel, table=True):
    """
    Tracks the financial and fulfillment state of a buyer-vendor transaction.
    Lifecycle: NEGOTIATING -> TERMS_AGREED -> FUNDED -> IN_TRANSIT -> COMPLETED
    """
    __tablename__ = "deal"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Links
    row_id: int = Field(foreign_key="row.id", index=True)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id", index=True)
    buyer_user_id: int = Field(foreign_key="user.id", index=True)

    # State machine
    status: str = Field(
        default="negotiating",
        index=True,
    )  # negotiating, terms_agreed, funded, in_transit, completed, disputed, canceled

    # Proxy email
    proxy_email_alias: str = Field(
        default_factory=lambda: secrets.token_hex(4),
        unique=True,
        index=True,
    )  # e.g. "a7f9b2c1" — prefixed with vendor slug at send time

    # Financials
    vendor_quoted_price: Optional[float] = None  # What the vendor quoted
    platform_fee_pct: float = 0.01  # 1% buyer markup
    platform_fee_amount: Optional[float] = None  # Computed: vendor_quoted_price * platform_fee_pct
    buyer_total: Optional[float] = None  # Computed: vendor_quoted_price + platform_fee_amount
    currency: str = "USD"

    # Stripe
    stripe_payment_intent_id: Optional[str] = Field(default=None, index=True)
    stripe_transfer_id: Optional[str] = None  # Payout to vendor
    stripe_connect_account_id: Optional[str] = None  # Vendor's connected account

    # Metadata
    agreed_terms_summary: Optional[str] = None  # AI-extracted summary of agreed terms
    fulfillment_notes: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    terms_agreed_at: Optional[datetime] = None
    funded_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None

    def compute_buyer_total(self) -> None:
        """Compute the buyer-facing total from the vendor quote + platform fee."""
        if self.vendor_quoted_price is not None:
            self.platform_fee_amount = round(self.vendor_quoted_price * self.platform_fee_pct, 2)
            self.buyer_total = round(self.vendor_quoted_price + self.platform_fee_amount, 2)


class DealMessage(SQLModel, table=True):
    """
    Immutable ledger of proxy-routed messages between buyer and vendor.
    Every intercepted email is saved here for dispute resolution and AI analysis.
    """
    __tablename__ = "deal_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    deal_id: int = Field(foreign_key="deal.id", index=True)

    # Who sent it
    sender_type: str  # buyer, vendor, system
    sender_email: Optional[str] = None

    # Content
    subject: Optional[str] = None
    content_text: str  # Stripped plain-text (no quoted reply chains)
    content_html: Optional[str] = None  # Original HTML if needed
    attachments: Optional[Any] = Field(
        default=None, sa_column=Column(sa.JSON, nullable=True)
    )  # [{url, filename, content_type}]

    # Resend metadata
    resend_message_id: Optional[str] = None  # Resend's inbound message ID

    # AI analysis
    ai_classification: Optional[str] = None  # e.g. "negotiating", "terms_agreed", "general"
    ai_confidence: Optional[float] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
