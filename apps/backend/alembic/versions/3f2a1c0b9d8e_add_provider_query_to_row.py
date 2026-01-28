"""add_provider_query_to_row

Revision ID: 3f2a1c0b9d8e
Revises: e01f187cef03
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '3f2a1c0b9d8e'
down_revision: Union[str, Sequence[str], None] = 'e01f187cef03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('row')]

    if 'provider_query' not in columns:
        op.add_column('row', sa.Column('provider_query', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('row', 'provider_query')
