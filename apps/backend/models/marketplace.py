"""Marketplace models: merchants, quotes, contracts, and seller interactions."""

from datetime import datetime
from typing import List, Optional

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

try:
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:  # pragma: no cover - environment-dependent optional dependency
    Vector = None

# Use pgvector column type only when both the Python package AND the DB extension
# are expected to be available.  Set USE_PGVECTOR=false (or omit) to fall back to JSON
# (e.g. local dev without the Postgres extension installed).
import os as _os
_USE_PGVECTOR = _os.getenv("USE_PGVECTOR", "false").lower() == "true" and Vector is not None

EMBEDDING_COLUMN = (
    sa.Column(Vector(1536), nullable=True) if _USE_PGVECTOR else sa.Column(sa.JSON, nullable=True)
)


class VendorProfile(SQLModel, table=True):
    """
    Directory vendor record.

    This is the canonical representation of a vendor in the world (seeded/crawled).
    If the vendor onboards as a preferred network seller, it can be linked to a
    Merchant record via merchant_id.
    """

    __tablename__ = "vendor_profile"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Optional link to onboarded merchant
    merchant_id: Optional[int] = Field(default=None, foreign_key="merchant.id", index=True)

    # Basic identity
    category: str = Field(index=True)
    company: str = Field(index=True)
    website: Optional[str] = None
    contact_email: Optional[str] = Field(default=None, index=True)
    contact_phone: Optional[str] = None

    # Coverage / metadata (JSON strings for MVP consistency with existing models)
    service_areas: Optional[str] = None  # JSON array, e.g. ["US-TN", "US-NY", "nationwide"]
    specialties: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    image_url: Optional[str] = None

    # Retrieval
    profile_text: Optional[str] = None
    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=EMBEDDING_COLUMN,
    )
    embedding_model: Optional[str] = None
    embedded_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
    quote_id: int = Field(foreign_key="seller_quote.id", index=True)

    # Buyer info (for email)
    buyer_user_id: int = Field(foreign_key="user.id")
    buyer_email: str
    buyer_name: Optional[str] = None
    buyer_phone: Optional[str] = None

    # Deal value (for tracking)
    deal_value: Optional[float] = None
    currency: str = "USD"

    # Email tracking
    buyer_email_sent_at: Optional[datetime] = None
    seller_email_sent_at: Optional[datetime] = None
    buyer_email_opened_at: Optional[datetime] = None
    seller_email_opened_at: Optional[datetime] = None

    # Status
    status: str = "introduced"  # introduced, closed, cancelled
    closed_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Merchant(SQLModel, table=True):
    """
    Registered merchant in the preferred seller network.
    Self-registered via /merchants/register.
    """
    __tablename__ = "merchant"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Business profile
    business_name: str = Field(index=True)
    contact_name: str
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = None
    website: Optional[str] = None

    # Categories (JSON array of category slugs)
    categories: Optional[str] = None  # JSON: ["electronics", "private_aviation"]

    # Service areas (JSON array of regions/states)
    service_areas: Optional[str] = None  # JSON: ["US-CA", "US-NY", "nationwide"]

    # Verification
    status: str = "pending"  # pending, verified, suspended
    verified_at: Optional[datetime] = None

    # Linked user account (optional)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    # Linked seller record (for bid attribution)
    seller_id: Optional[int] = Field(default=None, foreign_key="seller.id")

    # Stripe Connect (Phase 4 — marketplace fee collection)
    stripe_account_id: Optional[str] = Field(default=None, index=True)
    stripe_onboarding_complete: bool = False
    default_commission_rate: float = 0.05  # 5% default platform fee

    # Anti-Fraud & Reputation (PRD 10)
    verification_level: str = "unverified"  # "unverified", "email_verified", "identity_verified", "premium"
    reputation_score: float = 0.0  # 0.0-5.0 based on deal history

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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


class SellerBookmark(SQLModel, table=True):
    """
    Seller bookmarks for buyer RFPs they're interested in.
    """
    __tablename__ = "seller_bookmark"

    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: int = Field(foreign_key="merchant.id", index=True)
    row_id: int = Field(foreign_key="row.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
