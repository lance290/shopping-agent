"""add_revenue_tracking_fields

Revision ID: a1b2c3d4e5f6
Revises: 0d5ad283564a
Create Date: 2026-02-06 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0d5ad283564a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add revenue tracking fields to purchase_event and Stripe Connect fields to merchant."""
    # PurchaseEvent revenue tracking
    op.add_column('purchase_event', sa.Column('platform_fee_amount', sa.Float(), nullable=True))
    op.add_column('purchase_event', sa.Column('commission_rate', sa.Float(), nullable=True))
    op.add_column('purchase_event', sa.Column('revenue_type', sa.String(), server_default='affiliate', nullable=False))

    # Notification table (Phase 4 — shared component)
    op.create_table(
        'notification',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False, index=True),
        sa.Column('type', sa.String(), nullable=False, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('body', sa.String(), nullable=True),
        sa.Column('action_url', sa.String(), nullable=True),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # ShareLink collaboration permissions
    op.add_column('share_link', sa.Column('permission', sa.String(), server_default='view_only', nullable=False))

    # Bid closing status (Unified Closing Layer)
    op.add_column('bid', sa.Column('closing_status', sa.String(), nullable=True))

    # Merchant Stripe Connect
    op.add_column('merchant', sa.Column('stripe_account_id', sa.String(), nullable=True))
    op.add_column('merchant', sa.Column('stripe_onboarding_complete', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('merchant', sa.Column('default_commission_rate', sa.Float(), server_default='0.05', nullable=False))
    op.create_index(op.f('ix_merchant_stripe_account_id'), 'merchant', ['stripe_account_id'], unique=False)


def downgrade() -> None:
    """Remove revenue tracking and Stripe Connect fields."""
    op.drop_index(op.f('ix_merchant_stripe_account_id'), table_name='merchant')
    op.drop_column('merchant', 'default_commission_rate')
    op.drop_column('merchant', 'stripe_onboarding_complete')
    op.drop_column('merchant', 'stripe_account_id')
    op.drop_column('bid', 'closing_status')
    op.drop_column('share_link', 'permission')
    op.drop_table('notification')
    op.drop_column('purchase_event', 'revenue_type')
    op.drop_column('purchase_event', 'commission_rate')
    op.drop_column('purchase_event', 'platform_fee_amount')
