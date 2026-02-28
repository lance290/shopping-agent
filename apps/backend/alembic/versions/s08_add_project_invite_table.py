"""Add project_invite table for Pop list sharing.

Revision ID: s08_project_invite
Revises: s07_project_member
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "s08_project_invite"
down_revision = "s07_project_member"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "project_invite" in inspector.get_table_names():
        return
    op.create_table(
        "project_invite",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("project.id"), nullable=False, index=True),
        sa.Column("invited_by", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("project_invite")
