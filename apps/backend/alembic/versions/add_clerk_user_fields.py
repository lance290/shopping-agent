"""Add Clerk user fields to User table

Revision ID: add_clerk_fields
Revises: bfa9d8fedf7a
Create Date: 2026-01-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_clerk_fields'
down_revision: Union[str, Sequence[str], None] = 'bfa9d8fedf7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('user')]
    
    # Add clerk_user_id column if not exists
    if 'clerk_user_id' not in columns:
        op.add_column('user', sa.Column('clerk_user_id', sa.String(), nullable=True))
        op.create_index('ix_user_clerk_user_id', 'user', ['clerk_user_id'], unique=True)
    
    # Add phone_number column if not exists
    if 'phone_number' not in columns:
        op.add_column('user', sa.Column('phone_number', sa.String(), nullable=True))
    
    # Make email nullable - skip if already nullable or if it would fail
    # This is a no-op if already nullable
    try:
        op.alter_column('user', 'email', existing_type=sa.String(), nullable=True)
    except Exception:
        pass  # Column might already be nullable


def downgrade():
    op.alter_column('user', 'email', existing_type=sa.String(), nullable=False)
    op.drop_column('user', 'phone_number')
    op.drop_index('ix_user_clerk_user_id', table_name='user')
    op.drop_column('user', 'clerk_user_id')
