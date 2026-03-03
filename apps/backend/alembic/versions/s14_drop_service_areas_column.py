"""Drop dead-weight service_areas column from vendor table.

This column was never queried and caused production INSERT failures
due to JSONB vs VARCHAR type mismatch.

Revision ID: s14_drop_service_areas
Revises: s13_sdui_schema
Create Date: 2026-03-02
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "s14_drop_service_areas"
down_revision: Union[str, Sequence[str], None] = "s13_sdui_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Only drop if column exists (idempotent)
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'vendor' AND column_name = 'service_areas'"
    ))
    if result.first() is not None:
        op.drop_column("vendor", "service_areas")


def downgrade() -> None:
    op.add_column("vendor", sa.Column("service_areas", sa.JSON(), nullable=True))
