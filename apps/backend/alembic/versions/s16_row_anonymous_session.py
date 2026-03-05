"""Add anonymous_session_id column to row table.

Revision ID: s16_row_anonymous_session
Revises: s15_add_store_geo_location
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

revision = "s16_row_anonymous_session"
down_revision = "s15_add_store_geo_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("row")}
    if "anonymous_session_id" not in existing_cols:
        op.add_column("row", sa.Column("anonymous_session_id", sa.String, nullable=True))
        op.create_index("ix_row_anonymous_session_id", "row", ["anonymous_session_id"])


def downgrade() -> None:
    op.drop_index("ix_row_anonymous_session_id", table_name="row")
    op.drop_column("row", "anonymous_session_id")
