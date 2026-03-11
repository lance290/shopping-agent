"""Social features: likes, comments, shares, and clickout tracking."""

from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class Comment(SQLModel, table=True):
    """
    Persisted user comments for offers/bids.
    """
    __tablename__ = "comment"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Who commented
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    # Context
    row_id: Optional[int] = Field(default=None, foreign_key="row.id", index=True)

    # What they commented on (either a specific Bid ID or a raw URL)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    offer_url: Optional[str] = Field(default=None, index=True)

    body: str
    visibility: str = Field(default="private")
    status: str = Field(default="active")  # active, archived

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ShareLink(SQLModel, table=True):
    """
    Shareable links for projects, rows, and tiles to enhance search discovery.
    Enables shared content to guide users to successful searches.
    """
    __tablename__ = "share_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)  # 32-char random string

    # Polymorphic resource reference
    resource_type: str = Field(index=True)  # "project", "row", "tile"
    resource_id: int = Field(index=True)

    created_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Collaboration permissions (Phase 4)
    permission: str = "view_only"  # "view_only", "can_comment", "can_select"

    # Engagement metrics
    access_count: int = Field(default=0)  # Total times accessed
    unique_visitors: int = Field(default=0)  # Unique viewers
    search_initiated_count: int = Field(default=0)  # Users who searched after viewing share
    search_success_count: int = Field(default=0)  # Successful searches from this share
    signup_conversion_count: int = Field(default=0)  # Signups attributed to this share


class RowReaction(SQLModel, table=True):
    """Per-item like/reaction on a Pop shopping list item (PRD-07)."""
    __tablename__ = "row_reaction"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    reaction_type: str = Field(default="like")  # "like" for now; extensible later
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RowComment(SQLModel, table=True):
    """Per-item comment on a Pop shopping list item (PRD-07)."""
    __tablename__ = "row_comment"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    text: str
    status: str = Field(default="active")  # "active", "deleted"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClickoutEvent(SQLModel, table=True):
    """Logs every outbound click for affiliate tracking and auditing."""
    __tablename__ = "clickout_event"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Who clicked
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_id: Optional[int] = Field(default=None)  # For anonymous tracking

    # What they clicked
    row_id: Optional[int] = Field(default=None, index=True)
    bid_id: Optional[int] = Field(default=None, index=True)  # Added for SDUI attribution
    offer_index: int = 0  # Position in results (for ranking analysis)

    # URL info
    canonical_url: str  # Original URL from provider
    final_url: str  # URL after affiliate transformation (may be same)
    merchant_domain: str = Field(index=True)  # e.g., "amazon.com"

    # Affiliate info
    handler_name: str = "none"  # Which handler processed this
    affiliate_tag: Optional[str] = None  # e.g., "buyanything-20"

    # Provenance
    source: str = "unknown"  # e.g., "serpapi_google_shopping"

    # Share attribution
    share_token: Optional[str] = Field(default=None, index=True)  # tracks share attribution
    referral_user_id: Optional[int] = Field(default=None, foreign_key="user.id")  # creator of the share link

    # Anti-Fraud (PRD 10)
    is_suspicious: bool = False
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PurchaseEvent(SQLModel, table=True):
    """Tracks completed purchases via Stripe Checkout or affiliate conversion."""
    __tablename__ = "purchase_event"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Who purchased
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    # What they purchased
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    row_id: Optional[int] = Field(default=None, foreign_key="row.id", index=True)

    # Purchase details
    amount: float = 0.0
    currency: str = "USD"
    merchant_domain: Optional[str] = Field(default=None, index=True)

    # Payment method
    payment_method: str = "affiliate"  # "affiliate", "stripe_checkout", "external"
    stripe_session_id: Optional[str] = Field(default=None, index=True)
    stripe_payment_intent_id: Optional[str] = None

    # Attribution
    clickout_event_id: Optional[int] = Field(default=None, foreign_key="clickout_event.id")
    share_token: Optional[str] = Field(default=None, index=True)

    # Status
    status: str = "completed"  # "pending", "completed", "refunded", "failed"

    # Revenue tracking (Phase 4)
    platform_fee_amount: Optional[float] = None  # Amount BuyAnything.ai earns from this transaction
    commission_rate: Optional[float] = None       # e.g., 0.05 for 5%
    revenue_type: str = "affiliate"               # "affiliate", "stripe_connect", "transaction_fee"

    created_at: datetime = Field(default_factory=datetime.utcnow)


class RequestFeedback(SQLModel, table=True):
    __tablename__ = "request_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    feedback_type: str = Field(index=True)
    score: Optional[float] = None
    comment: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RequestEvent(SQLModel, table=True):
    __tablename__ = "request_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    event_type: str = Field(index=True)
    event_value: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SourceMemory(SQLModel, table=True):
    """Persistent memory about domains and sources (Tech Spec §8.1, PRD §11.3)."""
    __tablename__ = "source_memory"

    id: Optional[int] = Field(default=None, primary_key=True)
    domain: str = Field(index=True)
    source_name: Optional[str] = None
    source_type: Optional[str] = None  # e.g., vendor_directory, amazon, serpapi
    source_subtype: Optional[str] = None
    trust_score: float = 0.0
    prestige_score: float = 0.0
    success_count: int = 0
    surface_count: int = 0
    shortlist_count: int = 0
    contact_success_count: int = 0
    negative_count: int = 0
    last_seen_at: Optional[datetime] = None
    notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
