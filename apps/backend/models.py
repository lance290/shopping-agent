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

class RequestSpecBase(SQLModel):
    item_name: str
    constraints: str  # JSON string for MVP simplicity
    preferences: Optional[str] = None # JSON string

class RowCreate(RowBase):
    request_spec: RequestSpecBase

class Row(RowBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    
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


class User(SQLModel, table=True):
    """Registered users."""
    __tablename__ = "user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
