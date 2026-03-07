"""add_veryfi_and_campaign_schema

Revision ID: c7e4d2a1b9f0
Revises: 8b1e4a6c2d91
Create Date: 2026-03-07 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7e4d2a1b9f0"
down_revision: Union[str, Sequence[str], None] = "8b1e4a6c2d91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    try:
        return {idx["name"] for idx in inspector.get_indexes(table_name)}
    except Exception:
        return set()


def _fk_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    try:
        return {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "campaign" not in existing_tables:
        op.create_table(
            "campaign",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendor.id"), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("swap_product_name", sa.String(), nullable=False),
            sa.Column("swap_product_image", sa.String(), nullable=True),
            sa.Column("swap_product_url", sa.String(), nullable=True),
            sa.Column("budget_total_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("budget_remaining_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payout_per_swap_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("target_categories", sa.String(), nullable=True),
            sa.Column("target_competitors", sa.String(), nullable=True),
            sa.Column("start_date", sa.DateTime(), nullable=True),
            sa.Column("end_date", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="active"),
            sa.Column("stripe_payment_intent_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        existing_tables = inspector.get_table_names()

    campaign_indexes = _index_names(inspector, "campaign") if "campaign" in existing_tables else set()
    if "campaign" in existing_tables and "ix_campaign_vendor_id" not in campaign_indexes:
        op.create_index("ix_campaign_vendor_id", "campaign", ["vendor_id"])

    receipt_cols = {c["name"] for c in inspector.get_columns("receipt")} if "receipt" in existing_tables else set()
    receipt_indexes = _index_names(inspector, "receipt") if "receipt" in existing_tables else set()

    if "receipt" in existing_tables:
        if "veryfi_document_id" not in receipt_cols:
            op.add_column("receipt", sa.Column("veryfi_document_id", sa.Integer(), nullable=True))
        if "store_name" not in receipt_cols:
            op.add_column("receipt", sa.Column("store_name", sa.String(), nullable=True))
        if "transaction_date" not in receipt_cols:
            op.add_column("receipt", sa.Column("transaction_date", sa.DateTime(), nullable=True))
        if "total_amount" not in receipt_cols:
            op.add_column("receipt", sa.Column("total_amount", sa.Float(), nullable=True))
        if "fraud_score" not in receipt_cols:
            op.add_column("receipt", sa.Column("fraud_score", sa.Float(), nullable=False, server_default="0"))
        if "fraud_flags" not in receipt_cols:
            op.add_column("receipt", sa.Column("fraud_flags", sa.JSON(), nullable=True))
        if "raw_veryfi_json" not in receipt_cols:
            op.add_column("receipt", sa.Column("raw_veryfi_json", sa.Text(), nullable=True))
        if "receipt_content_hash" not in receipt_cols:
            op.add_column("receipt", sa.Column("receipt_content_hash", sa.String(), nullable=True))
        if "ix_receipt_receipt_content_hash" not in receipt_indexes:
            op.create_index("ix_receipt_receipt_content_hash", "receipt", ["receipt_content_hash"])

    wallet_cols = {c["name"] for c in inspector.get_columns("wallet_transaction")} if "wallet_transaction" in existing_tables else set()
    wallet_indexes = _index_names(inspector, "wallet_transaction") if "wallet_transaction" in existing_tables else set()
    wallet_fks = _fk_names(inspector, "wallet_transaction") if "wallet_transaction" in existing_tables else set()

    if "wallet_transaction" in existing_tables:
        if "campaign_id" not in wallet_cols:
            op.add_column("wallet_transaction", sa.Column("campaign_id", sa.Integer(), nullable=True))
        if "ix_wallet_transaction_campaign_id" not in wallet_indexes:
            op.create_index("ix_wallet_transaction_campaign_id", "wallet_transaction", ["campaign_id"])
        if "fk_wallet_transaction_campaign_id_campaign" not in wallet_fks:
            op.create_foreign_key(
                "fk_wallet_transaction_campaign_id_campaign",
                "wallet_transaction",
                "campaign",
                ["campaign_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "wallet_transaction" in existing_tables:
        wallet_cols = {c["name"] for c in inspector.get_columns("wallet_transaction")}
        wallet_indexes = _index_names(inspector, "wallet_transaction")
        wallet_fks = _fk_names(inspector, "wallet_transaction")
        if "fk_wallet_transaction_campaign_id_campaign" in wallet_fks:
            op.drop_constraint("fk_wallet_transaction_campaign_id_campaign", "wallet_transaction", type_="foreignkey")
        if "ix_wallet_transaction_campaign_id" in wallet_indexes:
            op.drop_index("ix_wallet_transaction_campaign_id", table_name="wallet_transaction")
        if "campaign_id" in wallet_cols:
            op.drop_column("wallet_transaction", "campaign_id")

    if "receipt" in existing_tables:
        receipt_cols = {c["name"] for c in inspector.get_columns("receipt")}
        receipt_indexes = _index_names(inspector, "receipt")
        if "ix_receipt_receipt_content_hash" in receipt_indexes:
            op.drop_index("ix_receipt_receipt_content_hash", table_name="receipt")
        for col in [
            "receipt_content_hash",
            "raw_veryfi_json",
            "fraud_flags",
            "fraud_score",
            "total_amount",
            "transaction_date",
            "store_name",
            "veryfi_document_id",
        ]:
            if col in receipt_cols:
                op.drop_column("receipt", col)

    if "campaign" in existing_tables:
        campaign_indexes = _index_names(inspector, "campaign")
        if "ix_campaign_vendor_id" in campaign_indexes:
            op.drop_index("ix_campaign_vendor_id", table_name="campaign")
        op.drop_table("campaign")
