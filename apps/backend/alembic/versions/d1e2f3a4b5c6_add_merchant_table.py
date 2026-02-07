"""add merchant table

Revision ID: d1e2f3a4b5c6
Revises: c9f8e7d6b5a4, a1b2c3d4e5f6
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = ('c9f8e7d6b5a4', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create merchant table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'merchant' not in inspector.get_table_names():
        op.create_table(
            'merchant',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('business_name', sa.String(), nullable=False, index=True),
            sa.Column('contact_name', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
            sa.Column('phone', sa.String(), nullable=True),
            sa.Column('website', sa.String(), nullable=True),
            sa.Column('categories', sa.String(), nullable=True),
            sa.Column('service_areas', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True, index=True),
            sa.Column('seller_id', sa.Integer(), sa.ForeignKey('seller.id'), nullable=True),
            sa.Column('stripe_account_id', sa.String(), nullable=True, index=True),
            sa.Column('stripe_onboarding_complete', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('default_commission_rate', sa.Float(), nullable=False, server_default='0.05'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # Also create contract table if missing
    if 'contract' not in inspector.get_table_names():
        op.create_table(
            'contract',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchant.id'), nullable=True),
            sa.Column('bid_id', sa.Integer(), sa.ForeignKey('bid.id'), nullable=True),
            sa.Column('row_id', sa.Integer(), sa.ForeignKey('row.id'), nullable=True),
            sa.Column('docusign_envelope_id', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='draft'),
            sa.Column('amount', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
            sa.Column('signed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # Also create purchaseevent table if missing
    if 'purchaseevent' not in inspector.get_table_names():
        op.create_table(
            'purchaseevent',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('bid_id', sa.Integer(), sa.ForeignKey('bid.id'), nullable=True, index=True),
            sa.Column('row_id', sa.Integer(), sa.ForeignKey('row.id'), nullable=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
            sa.Column('seller_id', sa.Integer(), sa.ForeignKey('seller.id'), nullable=True),
            sa.Column('amount', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(), nullable=False, server_default='USD'),
            sa.Column('affiliate_network', sa.String(), nullable=True),
            sa.Column('affiliate_commission', sa.Float(), nullable=True),
            sa.Column('stripe_checkout_session_id', sa.String(), nullable=True),
            sa.Column('stripe_payment_intent_id', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='pending'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table('purchaseevent')
    op.drop_table('contract')
    op.drop_table('merchant')
