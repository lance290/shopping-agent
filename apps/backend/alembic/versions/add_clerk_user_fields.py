"""Add Clerk user fields to User table

Revision ID: add_clerk_fields
Revises: 
Create Date: 2026-01-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_clerk_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add clerk_user_id column
    op.add_column('user', sa.Column('clerk_user_id', sa.String(), nullable=True))
    op.create_index('ix_user_clerk_user_id', 'user', ['clerk_user_id'], unique=True)
    
    # Add phone_number column
    op.add_column('user', sa.Column('phone_number', sa.String(), nullable=True))
    
    # Make email nullable (it was required before)
    op.alter_column('user', 'email', existing_type=sa.String(), nullable=True)


def downgrade():
    op.alter_column('user', 'email', existing_type=sa.String(), nullable=False)
    op.drop_column('user', 'phone_number')
    op.drop_index('ix_user_clerk_user_id', table_name='user')
    op.drop_column('user', 'clerk_user_id')
