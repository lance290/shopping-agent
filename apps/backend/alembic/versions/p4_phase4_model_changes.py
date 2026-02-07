"""Phase 4 model changes — scoring, fraud, timeout, signals, bookmarks

Revision ID: p4_phase4_models
Revises: 923cedba39d9
Create Date: 2025-01-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'p4_phase4_models'
down_revision = '923cedba39d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bid — created_at timestamp (was missing)
    op.add_column('bid', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # Bid — Personalized Ranking (PRD 11)
    op.add_column('bid', sa.Column('combined_score', sa.Float(), nullable=True))
    op.add_column('bid', sa.Column('relevance_score', sa.Float(), nullable=True))
    op.add_column('bid', sa.Column('price_score', sa.Float(), nullable=True))
    op.add_column('bid', sa.Column('quality_score', sa.Float(), nullable=True))
    op.add_column('bid', sa.Column('diversity_bonus', sa.Float(), nullable=True))
    op.add_column('bid', sa.Column('source_tier', sa.String(), nullable=True))

    # ClickoutEvent — Anti-Fraud (PRD 10)
    op.add_column('clickout_event', sa.Column('is_suspicious', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('clickout_event', sa.Column('ip_address', sa.String(), nullable=True))
    op.add_column('clickout_event', sa.Column('user_agent', sa.String(), nullable=True))

    # User — Anti-Fraud (PRD 10)
    op.add_column('user', sa.Column('trust_level', sa.String(), server_default='standard', nullable=False))

    # Merchant — Anti-Fraud (PRD 10)
    op.add_column('merchant', sa.Column('verification_level', sa.String(), server_default='unverified', nullable=False))
    op.add_column('merchant', sa.Column('reputation_score', sa.Float(), server_default='0.0', nullable=False))

    # OutreachEvent — Vendor Unresponsiveness (PRD 12)
    op.add_column('outreach_event', sa.Column('status', sa.String(), server_default='pending', nullable=False))
    op.add_column('outreach_event', sa.Column('timeout_hours', sa.Integer(), server_default='48', nullable=False))
    op.add_column('outreach_event', sa.Column('expired_at', sa.DateTime(), nullable=True))
    op.add_column('outreach_event', sa.Column('followup_sent_at', sa.DateTime(), nullable=True))

    # UserSignal (PRD 11)
    op.create_table(
        'user_signal',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False, index=True),
        sa.Column('bid_id', sa.Integer(), sa.ForeignKey('bid.id'), nullable=True, index=True),
        sa.Column('row_id', sa.Integer(), sa.ForeignKey('row.id'), nullable=True, index=True),
        sa.Column('signal_type', sa.String(), nullable=False, index=True),
        sa.Column('value', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # UserPreference (PRD 11)
    op.create_table(
        'user_preference',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=False, index=True),
        sa.Column('preference_key', sa.String(), nullable=False, index=True),
        sa.Column('preference_value', sa.String(), nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # SellerBookmark (PRD 04)
    op.create_table(
        'seller_bookmark',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchant.id'), nullable=False, index=True),
        sa.Column('row_id', sa.Integer(), sa.ForeignKey('row.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('seller_bookmark')
    op.drop_table('user_preference')
    op.drop_table('user_signal')

    op.drop_column('outreach_event', 'followup_sent_at')
    op.drop_column('outreach_event', 'expired_at')
    op.drop_column('outreach_event', 'timeout_hours')
    op.drop_column('outreach_event', 'status')

    op.drop_column('merchant', 'reputation_score')
    op.drop_column('merchant', 'verification_level')

    op.drop_column('user', 'trust_level')

    op.drop_column('clickout_event', 'user_agent')
    op.drop_column('clickout_event', 'ip_address')
    op.drop_column('clickout_event', 'is_suspicious')

    op.drop_column('bid', 'source_tier')
    op.drop_column('bid', 'diversity_bonus')
    op.drop_column('bid', 'quality_score')
    op.drop_column('bid', 'price_score')
    op.drop_column('bid', 'relevance_score')
    op.drop_column('bid', 'combined_score')
    op.drop_column('bid', 'created_at')
