"""s17_cpg_network

Revision ID: 5c3816aecf94
Revises: s12_vendor_search_vector
Create Date: 2026-03-05 21:36:00.142395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '5c3816aecf94'
down_revision: Union[str, Sequence[str], None] = 's12_vendor_search_vector'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('row', sa.Column('retailer_sku', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('row', sa.Column('brand_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('row', 'brand_name')
    op.drop_column('row', 'retailer_sku')
