"""Pop savings agent models: wallet, receipts, referrals."""

from typing import Optional
from datetime import datetime
import uuid
import secrets
from sqlmodel import Field, SQLModel


def _gen_ref_code() -> str:
    """Generate a short, URL-safe referral code (8 chars)."""
    return secrets.token_urlsafe(6)[:8].upper()


class WalletTransaction(SQLModel, table=True):
    """
    Immutable ledger entry for a Pop wallet credit or debit.
    Credits are always positive; adjustments/reversals are negative.
    """
    __tablename__ = "wallet_transaction"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount_cents: int
    description: str
    source: str = "receipt_scan"  # "receipt_scan", "referral_bonus", "adjustment"
    receipt_id: Optional[str] = Field(default=None, foreign_key="receipt.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Receipt(SQLModel, table=True):
    """
    Receipt submission record.
    image_hash (SHA-256 of base64 payload) enables deduplication.
    """
    __tablename__ = "receipt"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    image_hash: str = Field(index=True)
    status: str = "processed"  # "processed", "duplicate", "failed"
    credits_earned_cents: int = 0
    items_matched: int = 0
    raw_items_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Referral(SQLModel, table=True):
    """
    Attribution record for a user who signed up via a referral link.
    """
    __tablename__ = "referral"

    id: Optional[int] = Field(default=None, primary_key=True)
    referrer_user_id: int = Field(foreign_key="user.id", index=True)
    referred_user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    ref_code: str = Field(index=True)
    status: str = "pending"  # "pending", "activated", "paid"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
