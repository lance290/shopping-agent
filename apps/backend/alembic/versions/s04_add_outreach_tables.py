"""Add outreach_campaign, outreach_message, outreach_quote tables.

Revision ID: s04_outreach_tables
Revises: s03_desire_tier
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = "s04_outreach_tables"
down_revision = "s03_desire_tier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if "outreach_campaign" in existing_tables:
        return  # Tables already exist (created by init_db)

    op.create_table(
        "outreach_campaign",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("row_id", sa.Integer(), sa.ForeignKey("row.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("request_summary", sa.Text(), nullable=False),
        sa.Column("structured_constraints", sa.Text(), nullable=True),
        sa.Column("action_budget", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("actions_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "outreach_message",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("outreach_campaign.id"), nullable=False, index=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendor.id"), nullable=False, index=True),
        sa.Column("bid_id", sa.Integer(), sa.ForeignKey("bid.id"), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("from_address", sa.String(length=255), nullable=True),
        sa.Column("to_address", sa.String(length=255), nullable=True),
        sa.Column("reply_to_address", sa.String(length=255), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "outreach_quote",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("outreach_campaign.id"), nullable=False, index=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendor.id"), nullable=False, index=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("outreach_message.id"), nullable=True),
        sa.Column("entry_method", sa.String(length=20), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("availability", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("expiration_date", sa.String(length=20), nullable=True),
        sa.Column("structured_data", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_finalist", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("outreach_quote")
    op.drop_table("outreach_message")
    op.drop_table("outreach_campaign")
