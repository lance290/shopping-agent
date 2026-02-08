"""add is_liked and liked_at to bid table

Revision ID: a7b8c9d0e1f2
Revises: e5f6a7b8c9d0
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'bid' in inspector.get_table_names():
        existing = [c['name'] for c in inspector.get_columns('bid')]
        if 'is_liked' not in existing:
            op.add_column('bid', sa.Column('is_liked', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        if 'liked_at' not in existing:
            op.add_column('bid', sa.Column('liked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('bid', 'liked_at')
    op.drop_column('bid', 'is_liked')
