"""Add search_vector tsvector column + GIN index to vendor table for hybrid search.

Revision ID: s12_vendor_search_vector
Revises: 1c757a15f7b5, s16_row_anonymous_session
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

revision = "s12_vendor_search_vector"
down_revision = ("1c757a15f7b5", "s16_row_anonymous_session")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add a generated tsvector column combining all searchable text fields
    op.execute("""
        ALTER TABLE vendor
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(tagline, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(category, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(specialties, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'C') ||
            setweight(to_tsvector('english', coalesce(profile_text, '')), 'D')
        ) STORED;
    """)

    # 2. GIN index for fast full-text lookup
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_vendor_search_vector
        ON vendor USING GIN (search_vector);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_vendor_search_vector;")
    op.execute("ALTER TABLE vendor DROP COLUMN IF EXISTS search_vector;")
