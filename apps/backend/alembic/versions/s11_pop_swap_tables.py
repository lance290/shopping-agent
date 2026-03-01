"""Create pop_swap and pop_swap_claim tables.

Revision ID: s11_pop_swap_tables
Revises: s10_bid_is_swap
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa

revision = "s11_pop_swap_tables"
down_revision = "s10_bid_is_swap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "pop_swap" not in existing_tables:
        op.create_table(
            "pop_swap",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("category", sa.String, nullable=False, index=True),
            sa.Column("target_product", sa.String, nullable=True),
            sa.Column("swap_product_name", sa.String, nullable=False),
            sa.Column("swap_product_image", sa.String, nullable=True),
            sa.Column("swap_product_url", sa.String, nullable=True),
            sa.Column("offer_type", sa.String, nullable=False, server_default="coupon"),
            sa.Column("savings_cents", sa.Integer, nullable=False, server_default="0"),
            sa.Column("discount_percent", sa.Float, nullable=True),
            sa.Column("offer_description", sa.String, nullable=True),
            sa.Column("terms", sa.String, nullable=True),
            sa.Column("brand_name", sa.String, nullable=True),
            sa.Column("brand_user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=True),
            sa.Column("brand_contact_email", sa.String, nullable=True),
            sa.Column("provider", sa.String, nullable=False, server_default="manual"),
            sa.Column("provider_offer_id", sa.String, nullable=True),
            sa.Column("provider_payout_cents", sa.Integer, nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
            sa.Column("expires_at", sa.DateTime, nullable=True),
            sa.Column("max_redemptions", sa.Integer, nullable=True),
            sa.Column("current_redemptions", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=True),
        )

    if "pop_swap_claim" not in existing_tables:
        op.create_table(
            "pop_swap_claim",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("swap_id", sa.Integer, sa.ForeignKey("pop_swap.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True),
            sa.Column("row_id", sa.Integer, sa.ForeignKey("row.id"), nullable=True),
            sa.Column("status", sa.String, nullable=False, server_default="claimed"),
            sa.Column("claimed_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("verified_at", sa.DateTime, nullable=True),
            sa.Column("paid_at", sa.DateTime, nullable=True),
            sa.Column("receipt_id", sa.String, sa.ForeignKey("receipt.id"), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("pop_swap_claim")
    op.drop_table("pop_swap")
