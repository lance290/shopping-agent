"""Admin and system models: bug reports, notifications, signals, and preferences."""

from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


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
    diagnostics: Optional[str] = None  # JSON object with captured context

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
