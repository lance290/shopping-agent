"""Add zip_code column to user table.

Revision ID: s12_user_zip_code
Revises: s11_pop_swap_tables
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "s12_user_zip_code"
down_revision = "s11_pop_swap_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("user")]
    if "zip_code" not in columns:
        op.add_column("user", sa.Column("zip_code", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "zip_code")
