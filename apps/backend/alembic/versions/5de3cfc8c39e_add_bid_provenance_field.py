"""add_bid_provenance_field

Revision ID: 5de3cfc8c39e
Revises: a6b8420ffc92
Create Date: 2026-02-01 10:26:30.157459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5de3cfc8c39e'
down_revision: Union[str, Sequence[str], None] = 'a6b8420ffc92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE bid ADD COLUMN IF NOT EXISTS provenance TEXT")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bid', 'provenance')
