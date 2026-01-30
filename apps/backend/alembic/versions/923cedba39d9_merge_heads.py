"""merge_heads

Revision ID: 923cedba39d9
Revises: 3f2a1c0b9d8e, f4a8d2c1e5b7
Create Date: 2026-01-29 23:24:51.678560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '923cedba39d9'
down_revision: Union[str, Sequence[str], None] = ('3f2a1c0b9d8e', 'f4a8d2c1e5b7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
