"""Outreach models: campaigns, messages, and quotes for autonomous vendor outreach."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from models.rows import Row
    from models.bids import Vendor


class OutreachCampaign(SQLModel, table=True):
    """A campaign to contact vendors for a specific row/request."""
    __tablename__ = "outreach_campaign"

    id: Optional[int] = Field(default=None, primary_key=True)
    row_id: int = Field(foreign_key="row.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    status: str = Field(default="draft")  # draft, active, paused, completed, cancelled
    request_summary: str  # LLM-generated summary of what the user wants
    structured_constraints: Optional[str] = None  # JSON of constraints from desire classification
    action_budget: int = Field(default=20)  # max vendor contacts
    actions_used: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    messages: List["OutreachMessage"] = Relationship(back_populates="campaign")
    quotes: List["OutreachQuote"] = Relationship(back_populates="campaign")


class OutreachMessage(SQLModel, table=True):
    """A single outreach message (outbound or inbound) within a campaign."""
    __tablename__ = "outreach_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="outreach_campaign.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    bid_id: Optional[int] = Field(default=None, foreign_key="bid.id")
    direction: str  # outbound, inbound
    channel: str  # email, web_form, whatsapp, phone, manual
    status: str = Field(default="draft")  # draft, ea_review, approved, sent, delivered, replied, bounced, failed
    subject: Optional[str] = None
    body: str
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    reply_to_address: Optional[str] = None  # campaign-specific reply address
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    metadata_json: Optional[str] = None  # delivery IDs, tracking, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)

    campaign: OutreachCampaign = Relationship(back_populates="messages")


class OutreachQuote(SQLModel, table=True):
    """A quote extracted from a vendor reply or manually entered by the EA."""
    __tablename__ = "outreach_quote"

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="outreach_campaign.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    message_id: Optional[int] = Field(default=None, foreign_key="outreach_message.id")
    entry_method: str  # auto_extracted, ea_manual
    price: Optional[float] = None
    currency: str = Field(default="USD")
    availability: Optional[str] = None
    terms: Optional[str] = None
    expiration_date: Optional[str] = None
    structured_data: Optional[str] = None  # JSON: category-specific fields
    confidence: Optional[float] = None  # LLM extraction confidence (auto only)
    is_finalist: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    campaign: OutreachCampaign = Relationship(back_populates="quotes")
