from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from pydantic import ConfigDict

# Shared properties
class RowBase(SQLModel):
    title: str
    status: str = "sourcing"  # sourcing, inviting, bids_arriving, shortlisting, closed
    budget_max: Optional[float] = None
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RequestSpecBase(SQLModel):
    item_name: str
    constraints: str  # JSON string for MVP simplicity
    preferences: Optional[str] = None # JSON string

class RowCreate(RowBase):
    request_spec: RequestSpecBase

class Row(RowBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    bids: List["Bid"] = Relationship(back_populates="row")
    request_spec: Optional["RequestSpec"] = Relationship(back_populates="row")

class RequestSpec(RequestSpecBase, table=True):
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
