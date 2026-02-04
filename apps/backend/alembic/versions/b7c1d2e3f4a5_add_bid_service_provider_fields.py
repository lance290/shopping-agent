"""add bid service provider fields

Revision ID: b7c1d2e3f4a5
Revises: ae820ac5eef6
Create Date: 2026-02-04 14:18:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'ae820ac5eef6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    bid_columns = [c['name'] for c in inspector.get_columns('bid')]

    if 'is_service_provider' not in bid_columns:
        op.add_column('bid', sa.Column('is_service_provider', sa.Boolean(), nullable=True, server_default='false'))
        op.execute("UPDATE bid SET is_service_provider = false WHERE is_service_provider IS NULL")
        op.alter_column('bid', 'is_service_provider', nullable=False)
    if 'contact_name' not in bid_columns:
        op.add_column('bid', sa.Column('contact_name', sa.String(), nullable=True))
    if 'contact_email' not in bid_columns:
        op.add_column('bid', sa.Column('contact_email', sa.String(), nullable=True))
    if 'contact_phone' not in bid_columns:
        op.add_column('bid', sa.Column('contact_phone', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    bid_columns = [c['name'] for c in inspector.get_columns('bid')]

    if 'contact_phone' in bid_columns:
        op.drop_column('bid', 'contact_phone')
    if 'contact_email' in bid_columns:
        op.drop_column('bid', 'contact_email')
    if 'contact_name' in bid_columns:
        op.drop_column('bid', 'contact_name')
    if 'is_service_provider' in bid_columns:
        op.drop_column('bid', 'is_service_provider')
