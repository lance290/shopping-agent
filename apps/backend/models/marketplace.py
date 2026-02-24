"""Marketplace models: quotes, contracts, and vendor interactions.

VendorProfile, Merchant, and SellerBookmark tables were merged into the unified
`vendor` table (see migration s02_unify_vendor_model). Their class names are
preserved as aliases to Vendor for backward compatibility.
"""

from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel

from models.bids import Vendor

# Backward-compatible aliases for merged models
VendorProfile = Vendor
Merchant = Vendor


class SellerQuote(SQLModel, table=True):
    """
    Seller-submitted quotes via magic link.
    Converts to Bid once submitted.
    """
    __tablename__ = "seller_quote"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)

    # Magic link auth
    token: str = Field(unique=True, index=True)  # Magic link token
    token_expires_at: Optional[datetime] = None

    # Seller info (from outreach or form)
    seller_email: str
    seller_name: Optional[str] = None
    seller_company: Optional[str] = None
    seller_phone: Optional[str] = None

    # Quote details
    price: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None

    # Choice factor answers (JSON)
    answers: Optional[str] = None  # JSON object: { "aircraft_type": "Citation XLS", ... }

    # Attachments (JSON array of URLs)
    attachments: Optional[str] = None

    # Status tracking
    status: str = "pending"  # pending, submitted, accepted, rejected

    # Converted bid reference
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None


class OutreachEvent(SQLModel, table=True):
    """
    Tracks vendor outreach emails sent for a row.
    """
    __tablename__ = "outreach_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)

    # Vendor info
    vendor_email: str
    vendor_name: Optional[str] = None
    vendor_company: Optional[str] = None
    vendor_source: str = "llm"  # llm, wattdata, manual

    # Email tracking
    message_id: Optional[str] = None  # SendGrid message ID

    # Magic link for this vendor
    quote_token: Optional[str] = Field(default=None, index=True)

    # Event timestamps
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    quote_submitted_at: Optional[datetime] = None

    # Opt-out
    opt_out: bool = False

    # Vendor Unresponsiveness (PRD 12)
    status: str = "pending"  # "pending", "sent", "delivered", "opened", "responded", "expired"
    timeout_hours: int = 48  # Hours before marking as expired
    expired_at: Optional[datetime] = None
    followup_sent_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class DealHandoff(SQLModel, table=True):
    """
    Tracks email handoff when buyer selects a quote.
    MVP closing mechanism before Stripe/DocuSign.
    """
    __tablename__ = "deal_handoff"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    quote_id: Optional[int] = Field(default=None, foreign_key="seller_quote.id", index=True)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id", index=True)

    # Buyer info (for email)
    buyer_user_id: int = Field(foreign_key="user.id")
    buyer_email: str
    buyer_name: Optional[str] = None
    buyer_phone: Optional[str] = None

    # Vendor info
    vendor_email: Optional[str] = None
    vendor_name: Optional[str] = None

    # Deal value (for tracking)
    deal_value: Optional[float] = None
    currency: str = "USD"

    # Acceptance flow (Phase 3)
    acceptance_token: Optional[str] = Field(default=None, index=True)
    buyer_accepted_at: Optional[datetime] = None
    buyer_accepted_ip: Optional[str] = None
    vendor_accepted_at: Optional[datetime] = None
    vendor_accepted_ip: Optional[str] = None

    # Email tracking
    buyer_email_sent_at: Optional[datetime] = None
    seller_email_sent_at: Optional[datetime] = None
    buyer_email_opened_at: Optional[datetime] = None
    seller_email_opened_at: Optional[datetime] = None

    # Status
    status: str = "introduced"  # introduced, pending_acceptance, accepted, completed, disputed, cancelled
    closed_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Contract(SQLModel, table=True):
    """
    DocuSign contract for B2B transactions.
    """
    __tablename__ = "contract"

    id: Optional[int] = Field(default=None, primary_key=True)

    # What this contract is for
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    row_id: Optional[int] = Field(default=None, foreign_key="row.id", index=True)
    quote_id: Optional[int] = Field(default=None, foreign_key="seller_quote.id")

    # Parties
    buyer_user_id: int = Field(foreign_key="user.id")
    buyer_email: str
    seller_email: str
    seller_company: Optional[str] = None

    # DocuSign
    docusign_envelope_id: Optional[str] = Field(default=None, index=True)
    template_id: Optional[str] = None

    # Contract details
    deal_value: Optional[float] = None
    currency: str = "USD"

    # Status tracking
    status: str = "draft"  # draft, sent, viewed, signed, completed, declined, voided
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)



# SellerBookmark table was dropped in s02_unify_vendor migration.
# Alias kept for backward compatibility in imports.
SellerBookmark = None  # type: ignore
