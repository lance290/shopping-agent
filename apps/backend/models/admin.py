"""Admin and system models: bug reports, notifications, signals, and preferences."""

from typing import Any, Optional
from datetime import datetime
import sqlalchemy as sa
from sqlmodel import Field, SQLModel, Column


class BugReport(SQLModel, table=True):
    """User submitted bug reports."""
    __tablename__ = "bug_report"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Reporter info
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    # Content
    notes: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    severity: str = "low"  # low, medium, high, blocking
    category: str = "ui"   # ui, data, auth, payments, performance, other

    # Metadata
    status: str = "captured"  # captured, processing, sent, closed

    # Classification (Phase 2 - Triage)
    classification: Optional[str] = None  # "bug" | "feature_request"
    classification_confidence: Optional[float] = None  # 0.0-1.0

    # JSON fields
    attachments: Optional[str] = None  # JSON list of stored file paths/urls
    diagnostics: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))  # JSONB object with captured context

    # External Links
    github_issue_url: Optional[str] = None
    github_pr_url: Optional[str] = None
    preview_url: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(SQLModel, table=True):
    """
    In-app notifications for buyers and sellers.
    Used by: seller RFP alerts, quote updates, viral referrals, purchase confirmations.
    """
    __tablename__ = "notification"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    # Notification type
    type: str = Field(index=True)  # "rfp_match", "quote_received", "quote_accepted", "referral", "purchase"

    # Content
    title: str
    body: Optional[str] = None
    action_url: Optional[str] = None  # Deep link for click-through

    # Related resource
    resource_type: Optional[str] = None  # "row", "bid", "quote", "share"
    resource_id: Optional[int] = None

    # State
    read: bool = False
    read_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserSignal(SQLModel, table=True):
    """
    Tracks user interaction signals for ranking personalization.
    Signals: thumbs_up, thumbs_down, click, select, skip, dwell.
    """
    __tablename__ = "user_signal"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    row_id: Optional[int] = Field(default=None, foreign_key="row.id", index=True)

    signal_type: str = Field(index=True)  # "thumbs_up", "thumbs_down", "click", "select", "skip"
    value: float = 1.0  # Signal strength (e.g., 1.0 for positive, -1.0 for negative)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserPreference(SQLModel, table=True):
    """
    Learned user preferences from signal aggregation.
    E.g., preference for certain brands, price ranges, merchants.
    """
    __tablename__ = "user_preference"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    preference_key: str = Field(index=True)  # "brand", "merchant", "price_range", "category"
    preference_value: str  # The specific value (e.g., "Nike", "amazon.com", "50-200")
    weight: float = 1.0  # Learned weight for this preference

    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VendorCoverageGap(SQLModel, table=True):
    """Actionable unmet vendor coverage signals derived from real searches."""
    __tablename__ = "vendor_coverage_gap"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: Optional[int] = Field(default=None, foreign_key="row.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    row_title: str
    canonical_need: str = Field(index=True)
    search_query: Optional[str] = None
    vendor_query: Optional[str] = None
    geo_hint: Optional[str] = Field(default=None, index=True)
    desire_tier: Optional[str] = Field(default=None, index=True)
    service_type: Optional[str] = Field(default=None, index=True)

    summary: str
    rationale: Optional[str] = None
    suggested_queries: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    assessment: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    supporting_context: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))

    confidence: float = 0.0
    times_seen: int = 1
    status: str = Field(default="new", index=True)
    emailed_count: int = 0
    email_sent_at: Optional[datetime] = None

    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


class LocationGeocodeCache(SQLModel, table=True):
    """Durable forward geocode cache for location-aware search."""
    __tablename__ = "location_geocode_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(index=True, unique=True)
    query_text: str
    normalized_query: str = Field(index=True)
    country_hint: Optional[str] = None

    normalized_label: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    precision: Optional[str] = None
    status: str = Field(default="unresolved", index=True)
    provider: Optional[str] = None

    hit_count: int = 0
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DiscoveredVendorCandidate(SQLModel, table=True):
    """Row-linked vendor candidates discovered live outside the canonical vendor DB."""
    __tablename__ = "discovered_vendor_candidate"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id", index=True)

    discovery_session_id: str = Field(index=True)
    adapter_id: str = Field(index=True)
    discovery_mode: str = Field(index=True)
    source_type: str = Field(index=True)
    source_query: str

    vendor_name: str
    website_url: Optional[str] = None
    canonical_domain: Optional[str] = Field(default=None, index=True)
    source_url: Optional[str] = None
    snippet: Optional[str] = None
    image_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location_hint: Optional[str] = None

    official_site: bool = False
    first_party_contact: bool = False
    confidence: float = 0.0
    completeness_score: float = 0.0
    trust_score: float = 0.0
    status: str = Field(default="discovered", index=True)

    raw_payload: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    extraction_payload: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    provenance: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VendorEnrichmentQueueItem(SQLModel, table=True):
    """Queue item for asynchronous enrichment/promotion of discovered vendors."""
    __tablename__ = "vendor_enrichment_queue_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="discovered_vendor_candidate.id", index=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id", index=True)

    discovery_session_id: str = Field(index=True)
    canonical_domain: Optional[str] = Field(default=None, index=True)
    discovery_mode: str = Field(index=True)
    source_provider: str = Field(index=True)

    confidence: float = 0.0
    completeness_score: float = 0.0
    trust_score: float = 0.0
    status: str = Field(default="queued", index=True)
    retry_count: int = 0
    next_attempt_at: Optional[datetime] = None

    payload: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
