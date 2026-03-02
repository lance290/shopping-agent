import os
import re

path = "apps/backend/models/bids.py"
with open(path, "r") as f:
    content = f.read()

# Fix Vendor.service_areas
content = content.replace(
    "service_areas: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))",
    "service_areas: Optional[dict] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))"
)

# Fix Vendor.embedding
content = content.replace(
    "embedding: Optional[Any] = Field(default=None, sa_column=Column(Vector(1536), nullable=True))",
    "embedding: Optional[list] = Field(default=None, sa_column=Column(Vector(1536), nullable=True))"
)

# Fix Bid.source_payload
content = content.replace(
    "source_payload: Optional[Any] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))",
    "source_payload: Optional[dict] = Field(default=None, sa_column=Column(sa.JSON, nullable=True))"
)

# Fix BidWithProvenance
content = content.replace(
    "source_payload: Optional[Any] = None",
    "source_payload: Optional[dict] = None"
)

with open(path, "w") as f:
    f.write(content)
