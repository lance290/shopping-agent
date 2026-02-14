"""Row and project models: core search and organization entities."""

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
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
