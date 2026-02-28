"""Authentication models: login codes, sessions, and user management."""

from typing import Optional
from datetime import datetime, timedelta
import hashlib
import secrets
from sqlmodel import Field, SQLModel


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


class User(SQLModel, table=True):
    """Registered users."""
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    phone_number: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    company: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_admin: bool = Field(default=False)

    # Referral attribution for share links
    referral_share_token: Optional[str] = Field(default=None, index=True)
    signup_source: Optional[str] = Field(default=None)  # "share", "direct", etc.

    # Anti-Fraud & Reputation (PRD 10)
    trust_level: str = "standard"  # "new", "standard", "trusted"

    # Pop wallet (V2)
    wallet_balance_cents: int = Field(default=0)

    # Referral code — auto-generated, used to build invite/referral links
    ref_code: Optional[str] = Field(default=None, index=True)


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
    """Stores active user sessions with expiration."""
    __tablename__ = "auth_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(default=None, index=True)
    phone_number: Optional[str] = Field(default=None, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    session_token_hash: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)
    revoked_at: Optional[datetime] = None


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
