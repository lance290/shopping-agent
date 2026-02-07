"""add_revenue_tracking_fields

Revision ID: c9f8e7d6b5a4
Revises: b7c1d2e3f4a5
Create Date: 2026-02-06 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f8e7d6b5a4'
down_revision: Union[str, Sequence[str], None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return any(c['name'] == column for c in insp.get_columns(table))


def upgrade() -> None:
    """Add revenue tracking fields to purchase_event and Stripe Connect fields to merchant."""

    # --- PurchaseEvent: create table if missing, then add new columns ---
    if not _table_exists('purchase_event'):
        op.create_table(
            'purchase_event',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True, index=True),
            sa.Column('bid_id', sa.Integer(), sa.ForeignKey('bid.id'), nullable=True, index=True),
            sa.Column('row_id', sa.Integer(), sa.ForeignKey('row.id'), nullable=True, index=True),
            sa.Column('amount', sa.Float(), nullable=False, server_default='0'),
            sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
            sa.Column('merchant_domain', sa.String(), nullable=True, index=True),
            sa.Column('payment_method', sa.String(), nullable=False, server_default='affiliate'),
            sa.Column('stripe_session_id', sa.String(), nullable=True, index=True),
            sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
            sa.Column('clickout_event_id', sa.Integer(), sa.ForeignKey('clickout_event.id'), nullable=True),
            sa.Column('share_token', sa.String(), nullable=True, index=True),
            sa.Column('status', sa.String(), nullable=False, server_default='completed'),
            sa.Column('platform_fee_amount', sa.Float(), nullable=True),
            sa.Column('commission_rate', sa.Float(), nullable=True),
            sa.Column('revenue_type', sa.String(), server_default='affiliate', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
    else:
        if not _column_exists('purchase_event', 'platform_fee_amount'):
            op.add_column('purchase_event', sa.Column('platform_fee_amount', sa.Float(), nullable=True))
        if not _column_exists('purchase_event', 'commission_rate'):
            op.add_column('purchase_event', sa.Column('commission_rate', sa.Float(), nullable=True))
        if not _column_exists('purchase_event', 'revenue_type'):
            op.add_column('purchase_event', sa.Column('revenue_type', sa.String(), server_default='affiliate', nullable=False))

    # --- Notification table (Phase 4 — shared component) ---
    if not _table_exists('notification'):
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

    # --- ShareLink collaboration permissions ---
    if _table_exists('share_link') and not _column_exists('share_link', 'permission'):
        op.add_column('share_link', sa.Column('permission', sa.String(), server_default='view_only', nullable=False))

    # --- Bid closing status (Unified Closing Layer) ---
    if _table_exists('bid') and not _column_exists('bid', 'closing_status'):
        op.add_column('bid', sa.Column('closing_status', sa.String(), nullable=True))

    # --- Merchant Stripe Connect ---
    if _table_exists('merchant'):
        if not _column_exists('merchant', 'stripe_account_id'):
            op.add_column('merchant', sa.Column('stripe_account_id', sa.String(), nullable=True))
        if not _column_exists('merchant', 'stripe_onboarding_complete'):
            op.add_column('merchant', sa.Column('stripe_onboarding_complete', sa.Boolean(), server_default='false', nullable=False))
        if not _column_exists('merchant', 'default_commission_rate'):
            op.add_column('merchant', sa.Column('default_commission_rate', sa.Float(), server_default='0.05', nullable=False))
        # Index — safe to attempt; Postgres will error if duplicate, so guard with try
        try:
            op.create_index(op.f('ix_merchant_stripe_account_id'), 'merchant', ['stripe_account_id'], unique=False)
        except Exception:
            pass


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
