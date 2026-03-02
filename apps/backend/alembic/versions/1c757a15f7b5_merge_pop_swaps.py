"""merge_pop_swaps

Revision ID: 1c757a15f7b5
Revises: add_seo_fields_to_vendor, s12_user_zip_code
Create Date: 2026-03-01 10:22:04.135589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c757a15f7b5'
down_revision: Union[str, Sequence[str], None] = ('add_seo_fields_to_vendor', 's12_user_zip_code')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
