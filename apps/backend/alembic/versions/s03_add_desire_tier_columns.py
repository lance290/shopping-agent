"""Add desire_tier and structured_constraints columns to row table.

Revision ID: s03_desire_tier
Revises: s02_unify_vendor_model
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = "s03_desire_tier"
down_revision = "s02_unify_vendor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE row ADD COLUMN IF NOT EXISTS desire_tier VARCHAR(20)")
    op.execute("ALTER TABLE row ADD COLUMN IF NOT EXISTS structured_constraints TEXT")


def downgrade() -> None:
    op.drop_column("row", "structured_constraints")
    op.drop_column("row", "desire_tier")
