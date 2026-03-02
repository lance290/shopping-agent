"""Add ui_schema and ui_schema_version columns to project, row, and bid tables.

Revision ID: s13_sdui_schema
Revises: s12_user_zip_code
Create Date: 2026-03-02
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "s13_sdui_schema"
down_revision: Union[str, Sequence[str], None] = "s12_user_zip_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Project
    project_cols = {c["name"] for c in inspector.get_columns("project")}
    if "ui_schema" not in project_cols:
        op.add_column("project", sa.Column("ui_schema", sa.JSON, nullable=True))
    if "ui_schema_version" not in project_cols:
        op.add_column("project", sa.Column("ui_schema_version", sa.Integer, server_default="0", nullable=False))

    # Row
    row_cols = {c["name"] for c in inspector.get_columns("row")}
    if "ui_schema" not in row_cols:
        op.add_column("row", sa.Column("ui_schema", sa.JSON, nullable=True))
    if "ui_schema_version" not in row_cols:
        op.add_column("row", sa.Column("ui_schema_version", sa.Integer, server_default="0", nullable=False))

    # Bid
    bid_cols = {c["name"] for c in inspector.get_columns("bid")}
    if "bid_ui_schema" not in bid_cols:
        op.add_column("bid", sa.Column("bid_ui_schema", sa.JSON, nullable=True))
    if "ui_schema_version" not in bid_cols:
        op.add_column("bid", sa.Column("ui_schema_version", sa.Integer, server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("bid", "ui_schema_version")
    op.drop_column("bid", "bid_ui_schema")
    op.drop_column("row", "ui_schema_version")
    op.drop_column("row", "ui_schema")
    op.drop_column("project", "ui_schema_version")
    op.drop_column("project", "ui_schema")
