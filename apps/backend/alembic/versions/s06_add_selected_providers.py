"""Add selected_providers to row for per-row provider memory.

Revision ID: s06_selected_providers
Revises: s05_search_display
Create Date: 2026-02-20
"""
from alembic import op
import sqlalchemy as sa

revision = "s06_selected_providers"
down_revision = "s05_search_display"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE row ADD COLUMN IF NOT EXISTS selected_providers TEXT")


def downgrade() -> None:
    op.drop_column("row", "selected_providers")
