"""add_row_origin_columns

Revision ID: 8b1e4a6c2d91
Revises: 7d2c4e1f9ab3
Create Date: 2026-03-05 22:44:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b1e4a6c2d91"
down_revision: Union[str, Sequence[str], None] = "7d2c4e1f9ab3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("row")}

    if "origin_channel" not in existing_cols:
        op.add_column("row", sa.Column("origin_channel", sa.String(), nullable=True))
    if "origin_message_id" not in existing_cols:
        op.add_column("row", sa.Column("origin_message_id", sa.String(), nullable=True))
    if "origin_user_id" not in existing_cols:
        op.add_column("row", sa.Column("origin_user_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("row")}

    if "origin_user_id" in existing_cols:
        op.drop_column("row", "origin_user_id")
    if "origin_message_id" in existing_cols:
        op.drop_column("row", "origin_message_id")
    if "origin_channel" in existing_cols:
        op.drop_column("row", "origin_channel")
