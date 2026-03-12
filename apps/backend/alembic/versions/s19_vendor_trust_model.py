"""Add vendor trust columns + vendor_endorsement table

Revision ID: s19_vendor_trust
Revises: s18_project_anon
Create Date: 2026-03-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "s19_vendor_trust"
down_revision: Union[str, Sequence[str], None] = "s18_project_anon"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(inspector: sa.Inspector, table: str, col: str) -> bool:
    try:
        return col in {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return False


def _table_exists(inspector: sa.Inspector, table: str) -> bool:
    return table in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table: str, index: str) -> bool:
    try:
        return index in {idx["name"] for idx in inspector.get_indexes(table)}
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --- Vendor trust columns ---
    new_vendor_cols = [
        ("vendor_type", sa.String(), True),
        ("contact_title", sa.String(), True),
        ("contact_form_url", sa.String(), True),
        ("booking_url", sa.String(), True),
        ("secondary_categories", sa.JSON(), True),
        ("service_regions", sa.JSON(), True),
        ("source_provenance", sa.String(), True),
        ("trust_score", sa.Float(), True),
        ("last_verified_at", sa.DateTime(), True),
        ("last_contact_validated_at", sa.DateTime(), True),
    ]

    for col_name, col_type, nullable in new_vendor_cols:
        if not _col_exists(inspector, "vendor", col_name):
            op.add_column("vendor", sa.Column(col_name, col_type, nullable=nullable))

    # Index on vendor_type for filtering
    if not _index_exists(inspector, "vendor", "ix_vendor_vendor_type"):
        op.create_index("ix_vendor_vendor_type", "vendor", ["vendor_type"])

    # Index on trust_score for ranking
    if not _index_exists(inspector, "vendor", "ix_vendor_trust_score"):
        op.create_index("ix_vendor_trust_score", "vendor", ["trust_score"])

    # --- VendorEndorsement table ---
    if not _table_exists(inspector, "vendor_endorsement"):
        op.create_table(
            "vendor_endorsement",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendor.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
            sa.Column("trust_rating", sa.Integer(), nullable=True),
            sa.Column("recommended_for_categories", sa.JSON(), nullable=True),
            sa.Column("recommended_for_regions", sa.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_personal_contact", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_vendor_endorsement_vendor_id", "vendor_endorsement", ["vendor_id"])
        op.create_index("ix_vendor_endorsement_user_id", "vendor_endorsement", ["user_id"])
        op.create_index(
            "uq_vendor_endorsement_vendor_user",
            "vendor_endorsement",
            ["vendor_id", "user_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "vendor_endorsement"):
        op.drop_table("vendor_endorsement")

    drop_cols = [
        "vendor_type", "contact_title", "contact_form_url", "booking_url",
        "secondary_categories", "service_regions", "source_provenance",
        "trust_score", "last_verified_at", "last_contact_validated_at",
    ]
    for col_name in drop_cols:
        if _col_exists(inspector, "vendor", col_name):
            op.drop_column("vendor", col_name)
