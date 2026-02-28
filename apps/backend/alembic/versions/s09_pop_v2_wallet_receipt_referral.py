"""Pop V2: wallet_transaction, receipt, referral tables + User wallet/ref_code columns.

Revision ID: s09_pop_v2
Revises: s08_project_invite
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "s09_pop_v2"
down_revision = "s08_project_invite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # ── User: add wallet_balance_cents + ref_code ──────────────────────────
    existing_user_cols = {c["name"] for c in inspector.get_columns("user")}
    if "wallet_balance_cents" not in existing_user_cols:
        op.add_column("user", sa.Column("wallet_balance_cents", sa.Integer, nullable=False, server_default="0"))
    if "ref_code" not in existing_user_cols:
        op.add_column("user", sa.Column("ref_code", sa.String, nullable=True))
        op.create_index("ix_user_ref_code", "user", ["ref_code"])

    # ── receipt table ──────────────────────────────────────────────────────
    if "receipt" not in existing_tables:
        op.create_table(
            "receipt",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True),
            sa.Column("project_id", sa.Integer, sa.ForeignKey("project.id"), nullable=True),
            sa.Column("image_hash", sa.String, nullable=False, index=True),
            sa.Column("status", sa.String, nullable=False, server_default="processed"),
            sa.Column("credits_earned_cents", sa.Integer, nullable=False, server_default="0"),
            sa.Column("items_matched", sa.Integer, nullable=False, server_default="0"),
            sa.Column("raw_items_json", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    # ── wallet_transaction table ───────────────────────────────────────────
    if "wallet_transaction" not in existing_tables:
        op.create_table(
            "wallet_transaction",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True),
            sa.Column("amount_cents", sa.Integer, nullable=False),
            sa.Column("description", sa.String, nullable=False),
            sa.Column("source", sa.String, nullable=False, server_default="receipt_scan"),
            sa.Column("receipt_id", sa.String, sa.ForeignKey("receipt.id"), nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )

    # ── referral table ─────────────────────────────────────────────────────
    if "referral" not in existing_tables:
        op.create_table(
            "referral",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("referrer_user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True),
            sa.Column("referred_user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, unique=True),
            sa.Column("ref_code", sa.String, nullable=False, index=True),
            sa.Column("status", sa.String, nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("activated_at", sa.DateTime, nullable=True),
        )


def downgrade() -> None:
    op.drop_table("referral")
    op.drop_table("wallet_transaction")
    op.drop_table("receipt")
    op.drop_index("ix_user_ref_code", "user")
    op.drop_column("user", "ref_code")
    op.drop_column("user", "wallet_balance_cents")
