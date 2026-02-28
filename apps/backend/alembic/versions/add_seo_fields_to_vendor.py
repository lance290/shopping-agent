"""add_seo_fields_to_vendor

Revision ID: add_seo_fields_to_vendor
Revises: alter_embedding_type
Create Date: 2026-02-26 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_seo_fields_to_vendor'
down_revision: Union[str, Sequence[str], None] = 'alter_embedding_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely add the columns as requested in PRD
    op.execute("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS slug VARCHAR;")
    op.execute("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS seo_content JSONB;")
    op.execute("ALTER TABLE vendor ADD COLUMN IF NOT EXISTS schema_markup JSONB;")
    
    # Create an index on the slug for fast lookups by the frontend
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS vendor_slug_idx ON vendor (slug);")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS vendor_slug_idx;")
    op.execute("ALTER TABLE vendor DROP COLUMN IF EXISTS schema_markup;")
    op.execute("ALTER TABLE vendor DROP COLUMN IF EXISTS seo_content;")
    op.execute("ALTER TABLE vendor DROP COLUMN IF EXISTS slug;")
