"""Add vendor_profile directory table (HNWI vendor directory)

Revision ID: f2c1a9d3e7b4
Revises: a7b8c9d0e1f2, add_performance_indexes
Create Date: 2026-02-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


class VectorType(sa.types.UserDefinedType):
    """Postgres pgvector column type.

    Defined inline to avoid requiring the `pgvector` Python package in the Alembic
    runtime environment.
    """

    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def get_col_spec(self, **kw):
        return f"vector({self.dimensions})"


# revision identifiers, used by Alembic.
revision: str = "f2c1a9d3e7b4"
down_revision: Union[str, Sequence[str], None] = ("a7b8c9d0e1f2", "add_performance_indexes", "p4_phase4_models")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "vendor_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.Integer(), sa.ForeignKey("merchant.id"), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("contact_phone", sa.String(), nullable=True),
        sa.Column("service_areas", sa.Text(), nullable=True),
        sa.Column("specialties", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tagline", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("profile_text", sa.Text(), nullable=True),
        sa.Column("embedding", VectorType(1536), nullable=True),
        sa.Column("embedding_model", sa.String(), nullable=True),
        sa.Column("embedded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_vendor_profile_category", "vendor_profile", ["category"])
    op.create_index("ix_vendor_profile_company", "vendor_profile", ["company"])
    op.create_index("ix_vendor_profile_contact_email", "vendor_profile", ["contact_email"])
    op.create_index("ix_vendor_profile_merchant_id", "vendor_profile", ["merchant_id"])


def downgrade() -> None:
    op.drop_index("ix_vendor_profile_merchant_id", table_name="vendor_profile")
    op.drop_index("ix_vendor_profile_contact_email", table_name="vendor_profile")
    op.drop_index("ix_vendor_profile_company", table_name="vendor_profile")
    op.drop_index("ix_vendor_profile_category", table_name="vendor_profile")
    op.drop_table("vendor_profile")

    # Note: we intentionally do not drop the `vector` extension.
