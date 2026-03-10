from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class VendorBookmark(SQLModel, table=True):
    """
    Global vendor favorites for EAs/users (Replaces old SellerBookmark).
    Allows EAs to save a vendor to their 'Rolodex' across searches.
    """
    __tablename__ = "vendor_bookmark"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    
    # Optional context on where they saved it from
    source_row_id: Optional[int] = Field(default=None, foreign_key="row.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ItemBookmark(SQLModel, table=True):
    __tablename__ = "item_bookmark"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    canonical_url: str = Field(index=True)
    source_row_id: Optional[int] = Field(default=None, foreign_key="row.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
