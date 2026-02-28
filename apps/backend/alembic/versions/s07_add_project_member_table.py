"""Add project_member table for Bob family group sharing.

Revision ID: s07_project_member
Revises: s06_selected_providers
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = "s07_project_member"
down_revision = "s06_selected_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "project_member" in inspector.get_table_names():
        return
    op.create_table(
        "project_member",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("project.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True),
        sa.Column("role", sa.String, nullable=False, server_default="member"),
        sa.Column("channel", sa.String, nullable=False, server_default="email"),
        sa.Column("invited_by", sa.Integer, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("joined_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_project_member_project_user",
        "project_member",
        ["project_id", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_project_member_project_user", table_name="project_member")
    op.drop_table("project_member")
