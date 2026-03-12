"""Bid and vendor models: marketplace results and vendors."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
import json
from datetime import datetime
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlmodel import Field, SQLModel, Relationship, Column
from pydantic import ConfigDict, computed_field
from typing import Literal

if TYPE_CHECKING:
    from models.rows import Row


class Vendor(SQLModel, table=True):
    """Unified vendor entity — merged from seller + vendor_profile + merchant."""
    __tablename__ = "vendor"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Identity
    name: str = Field(index=True)
    email: Optional[str] = Field(default=None, index=True)
    domain: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    # Classification
    category: Optional[str] = Field(default=None, index=True)
    store_geo_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    specialties: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    image_url: Optional[str] = None
    # Search / embeddings
    profile_text: Optional[str] = None
    embedding: Optional[Any] = Field(default=None, sa_column=Column(Vector(1536), nullable=True))
    embedding_model: Optional[str] = None
    embedded_at: Optional[datetime] = None
    # Contact
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None
    contact_form_url: Optional[str] = None
    booking_url: Optional[str] = None
    # Classification (extended)
    vendor_type: Optional[str] = None  # retailer, reseller, broker, service_provider, advisor, marketplace, aggregator
    secondary_categories: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    service_regions: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    # Status & trust
    is_verified: bool = False
    status: str = "unverified"
    # Merchant fields
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    stripe_account_id: Optional[str] = Field(default=None, index=True)
    stripe_onboarding_complete: bool = False
    default_commission_rate: float = 0.00
    verification_level: str = "unverified"
    reputation_score: float = 0.0
    # Tier affinity for scorer matching (commodity, considered, luxury, enterprise)
    tier_affinity: Optional[str] = None
    price_range_min: Optional[float] = None  # Typical minimum order/price
    price_range_max: Optional[float] = None  # Typical maximum order/price
    # Trust & provenance
    source_provenance: Optional[str] = None  # ea_submitted, google_maps, web_search, manual_research, marketplace
    trust_score: Optional[float] = None  # blended: verification + contact quality + reputation + freshness
    last_verified_at: Optional[datetime] = None
    last_contact_validated_at: Optional[datetime] = None
    # Programmatic SEO / GEO
    slug: Optional[str] = Field(default=None, index=True, unique=True)
    seo_content: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    schema_markup: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    bids: List["Bid"] = Relationship(back_populates="seller")

    @property
    def contact_quality_score(self) -> float:
        """Computed score (0.0-1.0) based on contact field completeness.

        Weights: phone=0.25, email=0.20, website=0.20, contact_name=0.15,
        contact_form/booking=0.10, description=0.10
        """
        score = 0.0
        if self.phone:
            score += 0.25
        if self.email:
            score += 0.20
        if self.website:
            score += 0.20
        if self.contact_name:
            score += 0.15
        if self.contact_form_url or self.booking_url:
            score += 0.10
        if self.description:
            score += 0.10
        return round(score, 2)


class VendorEndorsement(SQLModel, table=True):
    """User-attributed trust and rating for a vendor."""
    __tablename__ = "vendor_endorsement"

    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    trust_rating: Optional[int] = None  # 1-5 scale
    recommended_for_categories: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    recommended_for_regions: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))
    notes: Optional[str] = None
    is_personal_contact: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


# Backward-compatible alias during migration
Seller = Vendor


class Bid(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id")
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id")

    price: Optional[float] = None  # None = quote-based (no fixed price). 0.0 = actually free.
    shipping_cost: float = 0.0
    total_cost: Optional[float] = None
    currency: str = "USD"

    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None

    # Search Architecture v2
    canonical_url: Optional[str] = None
    source_payload: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))  # JSONB of raw provider data
    search_intent_version: Optional[str] = None
    normalized_at: Optional[datetime] = None

    # Tile Provenance - structured provenance data (JSONB in DB)
    provenance: Optional[Any] = Field(default=None, sa_column=Column("provenance", sa.JSON, nullable=True))

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

    # Like status — stored directly on the bid for reliable persistence
    is_liked: bool = False
    liked_at: Optional[datetime] = None

    # Swap classification (Pop V2) — None=unclassified, True=swap, False=direct match
    is_swap: Optional[bool] = Field(default=None)

    # Soft-delete for bid reset — superseded bids are hidden, not deleted
    is_superseded: bool = Field(default=False)
    superseded_at: Optional[datetime] = None

    # SDUI schema (Phase 0.2) — lazy: generated on-expand only, not on creation
    ui_schema: Optional[Any] = Field(default=None, sa_column=Column("bid_ui_schema", sa.JSON, nullable=True))
    ui_schema_version: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    row: "Row" = Relationship(back_populates="bids")
    seller: Optional[Vendor] = Relationship(back_populates="bids")


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
    vendor_id: Optional[int] = None

    price: float
    shipping_cost: float = 0.0
    total_cost: float
    currency: str = "USD"

    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None

    # Search Architecture v2
    canonical_url: Optional[str] = None
    source_payload: Optional[Any] = None  # JSONB
    search_intent_version: Optional[str] = None
    normalized_at: Optional[datetime] = None

    # Tile Provenance - structured provenance data (JSONB)
    provenance: Optional[Any] = None

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
