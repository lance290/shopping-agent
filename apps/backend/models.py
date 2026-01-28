from typing import Optional, List
from datetime import datetime
import hashlib
import secrets
from sqlmodel import Field, SQLModel, Relationship
from pydantic import ConfigDict


def hash_token(token: str) -> str:
    """Hash a token (code or session) using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return f"{secrets.randbelow(1000000):06d}"


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)

# Shared properties
class RowBase(SQLModel):
    title: str
    status: str = "sourcing"  # sourcing, inviting, bids_arriving, shortlisting, closed
    budget_max: Optional[float] = None
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Choice factors as JSON strings for MVP simplicity
    choice_factors: Optional[str] = None  # JSON array of ChoiceFactor objects
    choice_answers: Optional[str] = None  # JSON object of factor_name -> answer

class RequestSpecBase(SQLModel):
    item_name: str
    constraints: str  # JSON string for MVP simplicity
    preferences: Optional[str] = None # JSON string

class RowCreate(RowBase):
    request_spec: RequestSpecBase
    project_id: Optional[int] = None

class ProjectBase(SQLModel):
    title: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    rows: List["Row"] = Relationship(back_populates="project")

class Row(RowBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", index=True)
    
    # Relationships
    bids: List["Bid"] = Relationship(back_populates="row")
    request_spec: Optional["RequestSpec"] = Relationship(back_populates="row")
    project: Optional[Project] = Relationship(back_populates="rows")

class RequestSpec(RequestSpecBase, table=True):
    __tablename__ = "request_spec"
    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id")
    
    row: Row = Relationship(back_populates="request_spec")

class Seller(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = None
    domain: Optional[str] = None
    is_verified: bool = False
    
    bids: List["Bid"] = Relationship(back_populates="seller")

class Bid(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id")
    seller_id: Optional[int] = Field(default=None, foreign_key="seller.id")
    
    price: float
    shipping_cost: float = 0.0
    total_cost: float
    currency: str = "USD"
    
    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None
    
    eta_days: Optional[int] = None
    return_policy: Optional[str] = None
    condition: str = "new"
    
    source: str = "manual" # manual, searchapi, feed
    is_selected: bool = False
    
    row: Row = Relationship(back_populates="bids")
    seller: Optional[Seller] = Relationship(back_populates="bids")


class User(SQLModel, table=True):
    """Registered users."""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    clerk_user_id: Optional[str] = Field(default=None, index=True, unique=True)
    phone_number: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_admin: bool = Field(default=False)


class AuditLog(SQLModel, table=True):
    """
    Immutable audit log for all significant system events.
    
    This is append-only. No UPDATE or DELETE operations allowed.
    """
    __tablename__ = "audit_log"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # When
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Who
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_id: Optional[int] = Field(default=None)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # What
    action: str = Field(index=True)  # e.g., "row.create", "clickout", "auth.login"
    resource_type: Optional[str] = None  # e.g., "row", "user", "clickout"
    resource_id: Optional[str] = None  # e.g., "123"
    
    # Details
    details: Optional[str] = None  # JSON string with action-specific data
    
    # Outcome
    success: bool = True
    error_message: Optional[str] = None


class AuthLoginCode(SQLModel, table=True):
    """Stores verification codes for email login. Only one active code per email."""
    __tablename__ = "auth_login_code"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    code_hash: str
    is_active: bool = True
    attempt_count: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuthSession(SQLModel, table=True):
    """Stores active user sessions."""
    __tablename__ = "auth_session"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_token_hash: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None


class ClickoutEvent(SQLModel, table=True):
    """Logs every outbound click for affiliate tracking and auditing."""
    __tablename__ = "clickout_event"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who clicked
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_id: Optional[int] = Field(default=None)  # For anonymous tracking
    
    # What they clicked
    row_id: Optional[int] = Field(default=None, index=True)
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
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Like(SQLModel, table=True):
    """
    Persisted user likes for offers/bids.
    """
    __tablename__ = "like"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who liked
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    
    # What they liked (either a specific Bid ID or a raw URL if not yet a bid)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id", index=True)
    offer_url: Optional[str] = Field(default=None, index=True) 
    
    # Context
    row_id: Optional[int] = Field(default=None, foreign_key="row.id", index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


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

    created_at: datetime = Field(default_factory=datetime.utcnow)


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
    
    # JSON fields
    attachments: Optional[str] = None  # JSON list of stored file paths/urls
    diagnostics: Optional[str] = None  # JSON object with captured context
    
    # External Links
    github_issue_url: Optional[str] = None
    github_pr_url: Optional[str] = None
    preview_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
