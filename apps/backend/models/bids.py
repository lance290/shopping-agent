"""Bid and seller models: marketplace results and vendors."""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
import json
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from pydantic import ConfigDict, computed_field

if TYPE_CHECKING:
    from models.rows import Row


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

    # Like status — stored directly on the bid for reliable persistence
    is_liked: bool = False
    liked_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    row: "Row" = Relationship(back_populates="bids")
    seller: Optional[Seller] = Relationship(back_populates="bids")


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
