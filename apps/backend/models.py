from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import secrets
import json
from sqlmodel import Field, SQLModel, Relationship
from pydantic import ConfigDict, computed_field


def hash_token(token: str) -> str:
    """Hash a token (code or session) using SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_verification_code() -> str:
    """Generate a 6-digit verification code."""
    return f"{secrets.randbelow(1000000):06d}"


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def generate_magic_link_token() -> str:
    """Generate a token for magic links (quote submission, etc.)."""
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
    provider_query: Optional[str] = None

    # Search Architecture v2
    search_intent: Optional[str] = None  # JSON of SearchIntent
    provider_query_map: Optional[str] = None  # JSON of ProviderQueryMap

    # Outreach tracking (Phase 2)
    outreach_status: Optional[str] = None  # none, in_progress, complete
    outreach_count: int = 0
    
    # Chat history for this row (JSON array of messages)
    chat_history: Optional[str] = None
    
    # Service detection - set by LLM, persisted on row
    is_service: bool = False
    service_category: Optional[str] = None  # e.g., "private_aviation", "catering"

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
    name: str = Field(index=True)
    email: Optional[str] = Field(default=None, index=True)
    domain: Optional[str] = None
    is_verified: bool = False
    
    # Enhanced vendor fields
    image_url: Optional[str] = None
    category: Optional[str] = Field(default=None, index=True)
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    
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
    
    # Search Architecture v2
    canonical_url: Optional[str] = None
    source_payload: Optional[str] = None  # JSON of raw provider data
    search_intent_version: Optional[str] = None
    normalized_at: Optional[datetime] = None

    # Tile Provenance - structured provenance data
    provenance: Optional[str] = None  # JSON of structured provenance data

    eta_days: Optional[int] = None
    return_policy: Optional[str] = None
    condition: str = "new"
    
    source: str = "manual" # manual, searchapi, feed
    is_selected: bool = False
    is_service_provider: bool = False

    # Personalized Ranking (PRD 11) — score dimensions persisted from scorer
    combined_score: Optional[float] = None
    relevance_score: Optional[float] = None
    price_score: Optional[float] = None
    quality_score: Optional[float] = None
    diversity_bonus: Optional[float] = None
    source_tier: Optional[str] = None  # "registered", "outreach", "marketplace"

    # Unified Closing Layer (Phase 4)
    closing_status: Optional[str] = None  # None, "pending", "payment_initiated", "paid", "shipped", "delivered", "contract_sent", "contract_signed", "refunded"
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    row: Row = Relationship(back_populates="bids")
    seller: Optional[Seller] = Relationship(back_populates="bids")


class User(SQLModel, table=True):
    """Registered users."""
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    phone_number: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_admin: bool = Field(default=False)

    # Referral attribution for share links
    referral_share_token: Optional[str] = Field(default=None, index=True)
    signup_source: Optional[str] = Field(default=None)  # "share", "direct", etc.

    # Anti-Fraud & Reputation (PRD 10)
    trust_level: str = "standard"  # "new", "standard", "trusted"


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
    email: Optional[str] = Field(default=None, index=True)
    phone_number: Optional[str] = Field(default=None, index=True)
    code_hash: str
    is_active: bool = True
    attempt_count: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuthSession(SQLModel, table=True):
    """Stores active user sessions."""
    __tablename__ = "auth_session"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    phone_number: Optional[str] = Field(default=None, index=True)
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


class BidWithProvenance(SQLModel):
    """
    Extended Bid model that includes parsed provenance data.
    Used for detailed tile view endpoints.
    Not a table model - used for API responses only.
    """
    model_config = ConfigDict(from_attributes=True)

    # Copy all Bid fields except relationships
    id: Optional[int] = None
    row_id: int
    seller_id: Optional[int] = None

    price: float
    shipping_cost: float = 0.0
    total_cost: float
    currency: str = "USD"

    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None

    # Search Architecture v2
    canonical_url: Optional[str] = None
    source_payload: Optional[str] = None
    search_intent_version: Optional[str] = None
    normalized_at: Optional[datetime] = None

    # Tile Provenance - structured provenance data
    provenance: Optional[str] = None

    eta_days: Optional[int] = None
    return_policy: Optional[str] = None
    condition: str = "new"

    source: str = "manual"
    is_selected: bool = False
    is_service_provider: bool = False
    closing_status: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    @computed_field
    @property
    def provenance_data(self) -> Optional[Dict[str, Any]]:
        """Parse and return structured provenance data."""
        if not self.provenance:
            return None

        try:
            data = json.loads(self.provenance) if isinstance(self.provenance, str) else self.provenance
            return data
        except (json.JSONDecodeError, TypeError):
            return None

    @computed_field
    @property
    def product_info(self) -> Optional[Dict[str, Any]]:
        """Extract product info from provenance data."""
        prov = self.provenance_data
        if not prov:
            return None
        return prov.get("product_info")

    @computed_field
    @property
    def matched_features(self) -> Optional[List[str]]:
        """Extract matched features from provenance data."""
        prov = self.provenance_data
        if not prov:
            return None
        return prov.get("matched_features", [])

    @computed_field
    @property
    def chat_excerpts(self) -> Optional[List[Dict[str, str]]]:
        """Extract chat excerpts from provenance data."""
        prov = self.provenance_data
        if not prov:
            return None
        return prov.get("chat_excerpts", [])


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


class ShareSearchEvent(SQLModel, table=True):
    """
    Tracks search events initiated from shared content.
    Measures share-driven search success rates.
    """
    __tablename__ = "share_search_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    share_token: str = Field(foreign_key="share_link.token", index=True)
    session_id: Optional[str] = Field(default=None, index=True)  # Anonymous tracking
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    search_query: str
    search_success: bool = Field(default=False)  # Determined by existing search success criteria

    created_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# NOTIFICATION MODEL (Phase 4 — shared component)
# =============================================================================

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


# =============================================================================
# SELLER QUOTE & OUTREACH MODELS (Phase 2 - Private Jet Demo)
# =============================================================================

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


# =============================================================================
# PERSONALIZED RANKING MODELS (PRD 11)
# =============================================================================

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


# =============================================================================
# SELLER BOOKMARK MODEL (PRD 04)
# =============================================================================

class SellerBookmark(SQLModel, table=True):
    """
    Seller bookmarks for buyer RFPs they're interested in.
    """
    __tablename__ = "seller_bookmark"

    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: int = Field(foreign_key="merchant.id", index=True)
    row_id: int = Field(foreign_key="row.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
