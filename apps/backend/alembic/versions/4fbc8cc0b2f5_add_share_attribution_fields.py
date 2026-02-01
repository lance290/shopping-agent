"""add_share_attribution_fields

Revision ID: 4fbc8cc0b2f5
Revises: 88107166573c
Create Date: 2026-02-01 10:35:05.338696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fbc8cc0b2f5'
down_revision: Union[str, Sequence[str], None] = '88107166573c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add referral fields to user table
    op.add_column('user', sa.Column('referral_share_token', sa.String(), nullable=True))
    op.add_column('user', sa.Column('signup_source', sa.String(), nullable=True))
    op.create_index(op.f('ix_user_referral_share_token'), 'user', ['referral_share_token'], unique=False)

    # Add share attribution fields to clickout_event table
    op.add_column('clickout_event', sa.Column('share_token', sa.String(), nullable=True))
    op.add_column('clickout_event', sa.Column('referral_user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_clickout_event_share_token'), 'clickout_event', ['share_token'], unique=False)
    op.create_foreign_key('fk_clickout_event_referral_user', 'clickout_event', 'user', ['referral_user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove clickout_event share attribution fields
    op.drop_constraint('fk_clickout_event_referral_user', 'clickout_event', type_='foreignkey')
    op.drop_index(op.f('ix_clickout_event_share_token'), table_name='clickout_event')
    op.drop_column('clickout_event', 'referral_user_id')
    op.drop_column('clickout_event', 'share_token')

    # Remove user referral fields
    op.drop_index(op.f('ix_user_referral_share_token'), table_name='user')
    op.drop_column('user', 'signup_source')
    op.drop_column('user', 'referral_share_token')
