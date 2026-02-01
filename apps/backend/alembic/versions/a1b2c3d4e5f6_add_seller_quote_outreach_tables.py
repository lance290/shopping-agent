"""add seller quote and outreach tables

Revision ID: a1b2c3d4e5f6
Revises: 923cedba39d9
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4fbc8cc0b2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create seller_quote table
    op.create_table(
        'seller_quote',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('row_id', sa.Integer(), nullable=False),
        sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('seller_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('seller_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('seller_company', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('seller_phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='USD'),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('answers', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('attachments', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='pending'),
        sa.Column('bid_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['row_id'], ['row.id'], ),
        sa.ForeignKeyConstraint(['bid_id'], ['bid.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_seller_quote_row_id'), 'seller_quote', ['row_id'], unique=False)
    op.create_index(op.f('ix_seller_quote_token'), 'seller_quote', ['token'], unique=True)

    # Create outreach_event table
    op.create_table(
        'outreach_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('row_id', sa.Integer(), nullable=False),
        sa.Column('vendor_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('vendor_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('vendor_company', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('vendor_source', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='llm'),
        sa.Column('message_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('quote_token', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('clicked_at', sa.DateTime(), nullable=True),
        sa.Column('quote_submitted_at', sa.DateTime(), nullable=True),
        sa.Column('opt_out', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['row_id'], ['row.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outreach_event_row_id'), 'outreach_event', ['row_id'], unique=False)
    op.create_index(op.f('ix_outreach_event_quote_token'), 'outreach_event', ['quote_token'], unique=False)

    # Create deal_handoff table
    op.create_table(
        'deal_handoff',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('row_id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('buyer_user_id', sa.Integer(), nullable=False),
        sa.Column('buyer_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('buyer_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('buyer_phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('deal_value', sa.Float(), nullable=True),
        sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='USD'),
        sa.Column('buyer_email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('seller_email_sent_at', sa.DateTime(), nullable=True),
        sa.Column('buyer_email_opened_at', sa.DateTime(), nullable=True),
        sa.Column('seller_email_opened_at', sa.DateTime(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='introduced'),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['row_id'], ['row.id'], ),
        sa.ForeignKeyConstraint(['quote_id'], ['seller_quote.id'], ),
        sa.ForeignKeyConstraint(['buyer_user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_deal_handoff_row_id'), 'deal_handoff', ['row_id'], unique=False)
    op.create_index(op.f('ix_deal_handoff_quote_id'), 'deal_handoff', ['quote_id'], unique=False)

    # Add outreach_status to row table
    op.add_column('row', sa.Column('outreach_status', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('row', sa.Column('outreach_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('row', 'outreach_count')
    op.drop_column('row', 'outreach_status')
    
    op.drop_index(op.f('ix_deal_handoff_quote_id'), table_name='deal_handoff')
    op.drop_index(op.f('ix_deal_handoff_row_id'), table_name='deal_handoff')
    op.drop_table('deal_handoff')
    
    op.drop_index(op.f('ix_outreach_event_quote_token'), table_name='outreach_event')
    op.drop_index(op.f('ix_outreach_event_row_id'), table_name='outreach_event')
    op.drop_table('outreach_event')
    
    op.drop_index(op.f('ix_seller_quote_token'), table_name='seller_quote')
    op.drop_index(op.f('ix_seller_quote_row_id'), table_name='seller_quote')
    op.drop_table('seller_quote')
