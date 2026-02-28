"""Row and project models: core search and organization entities."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import uuid
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from models.bids import Bid


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

    # Desire classification (PRD: Desire Classification)
    desire_tier: Optional[str] = None  # commodity, considered, service, bespoke, high_value, advisory
    structured_constraints: Optional[str] = None  # JSON of extracted structured constraints

    # Per-row provider selection (JSON object: {"amazon": true, "serpapi": false, ...})
    selected_providers: Optional[str] = None


class RequestSpecBase(SQLModel):
    item_name: str
    constraints: str  # JSON string for MVP simplicity
    preferences: Optional[str] = None # JSON string


class RowCreate(RowBase):
    request_spec: RequestSpecBase
    project_id: Optional[int] = None


class ProjectBase(SQLModel):
    title: str
    status: str = "active"  # active, archived


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    rows: List["Row"] = Relationship(back_populates="project")

class ProjectMember(SQLModel, table=True):
    """Maps multiple users to a shared Project (family shopping list)."""
    __tablename__ = "project_member"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = "member"  # "owner", "member"
    channel: str = "email"  # "email", "sms", "whatsapp" — how this member talks to Bob
    invited_by: Optional[int] = Field(default=None, foreign_key="user.id")
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectInvite(SQLModel, table=True):
    """Opaque invite token for sharing a Pop shopping list."""
    __tablename__ = "project_invite"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    invited_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)


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
