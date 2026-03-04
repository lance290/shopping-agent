"""Add store_geo_location column to vendor table.

Revision ID: s15_add_store_geo_location
Revises: s14_drop_service_areas
Create Date: 2026-03-04
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "s15_add_store_geo_location"
down_revision: Union[str, Sequence[str], None] = "s14_drop_service_areas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'vendor' AND column_name = 'store_geo_location'"
    ))
    if result.first() is None:
        op.add_column("vendor", sa.Column("store_geo_location", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("vendor", "store_geo_location")
