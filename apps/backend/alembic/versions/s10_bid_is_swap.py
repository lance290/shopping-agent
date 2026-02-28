"""Add is_swap column to bid table.

Revision ID: s10_bid_is_swap
Revises: s09_pop_v2
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "s10_bid_is_swap"
down_revision = "s09_pop_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("bid")}
    if "is_swap" not in existing_cols:
        op.add_column("bid", sa.Column("is_swap", sa.Boolean, nullable=True))
    else:
        # Change from NOT NULL default=false to nullable (LLM-classified)
        op.alter_column("bid", "is_swap", nullable=True, server_default=None)


def downgrade() -> None:
    op.drop_column("bid", "is_swap")
