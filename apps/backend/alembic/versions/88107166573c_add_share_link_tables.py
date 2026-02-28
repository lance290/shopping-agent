"""add_share_link_tables

Revision ID: 88107166573c
Revises: 5de3cfc8c39e
Create Date: 2026-02-01 10:34:43.092246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88107166573c'
down_revision: Union[str, Sequence[str], None] = '5de3cfc8c39e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if 'share_link' not in existing:
        op.create_table(
            'share_link',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('resource_type', sa.String(), nullable=False),
            sa.Column('resource_id', sa.Integer(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('unique_visitors', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('search_initiated_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('search_success_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('signup_conversion_count', sa.Integer(), nullable=False, server_default='0'),
            sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('token')
        )
        op.create_index(op.f('ix_share_link_token'), 'share_link', ['token'], unique=False)
        op.create_index(op.f('ix_share_link_resource_type'), 'share_link', ['resource_type'], unique=False)
        op.create_index(op.f('ix_share_link_resource_id'), 'share_link', ['resource_id'], unique=False)
        op.create_index(op.f('ix_share_link_created_by'), 'share_link', ['created_by'], unique=False)

    if 'share_search_event' not in existing:
        op.create_table(
            'share_search_event',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('share_token', sa.String(), nullable=False),
            sa.Column('session_id', sa.String(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('search_query', sa.String(), nullable=False),
            sa.Column('search_success', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['share_token'], ['share_link.token'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_share_search_event_share_token'), 'share_search_event', ['share_token'], unique=False)
        op.create_index(op.f('ix_share_search_event_session_id'), 'share_search_event', ['session_id'], unique=False)
        op.create_index(op.f('ix_share_search_event_user_id'), 'share_search_event', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_share_search_event_user_id'), table_name='share_search_event')
    op.drop_index(op.f('ix_share_search_event_session_id'), table_name='share_search_event')
    op.drop_index(op.f('ix_share_search_event_share_token'), table_name='share_search_event')
    op.drop_table('share_search_event')

    op.drop_index(op.f('ix_share_link_created_by'), table_name='share_link')
    op.drop_index(op.f('ix_share_link_resource_id'), table_name='share_link')
    op.drop_index(op.f('ix_share_link_resource_type'), table_name='share_link')
    op.drop_index(op.f('ix_share_link_token'), table_name='share_link')
    op.drop_table('share_link')
