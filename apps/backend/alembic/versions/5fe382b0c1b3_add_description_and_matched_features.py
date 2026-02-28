"""add_description_and_matched_features

Revision ID: 5fe382b0c1b3
Revises: s06_selected_providers
Create Date: 2026-02-26 15:27:44.704013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fe382b0c1b3'
down_revision: Union[str, Sequence[str], None] = 's06_selected_providers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pg_trgm extension exists for fast text search on vendor/bids
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    
    # Text indexes for vendor search
    op.execute("CREATE INDEX IF NOT EXISTS vendor_name_trgm_idx ON vendor USING gin (name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS vendor_desc_trgm_idx ON vendor USING gin (description gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS vendor_cat_trgm_idx ON vendor USING gin (category gin_trgm_ops);")
    
    # Text index for bid/product search
    op.execute("CREATE INDEX IF NOT EXISTS bid_title_trgm_idx ON bid USING gin (item_title gin_trgm_ops);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS bid_title_trgm_idx;")
    op.execute("DROP INDEX IF EXISTS vendor_cat_trgm_idx;")
    op.execute("DROP INDEX IF EXISTS vendor_desc_trgm_idx;")
    op.execute("DROP INDEX IF EXISTS vendor_name_trgm_idx;")
