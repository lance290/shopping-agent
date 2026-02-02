"""add_clickout_event_table

Revision ID: ddc57c9ac3c9
Revises: 
Create Date: 2026-01-18 18:15:20.558971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ddc57c9ac3c9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'user' not in tables:
        op.create_table(
            'user',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('phone_number', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        )
        op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
        tables = inspector.get_table_names()

    if 'seller' not in tables:
        op.create_table(
            'seller',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('domain', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        )
        tables = inspector.get_table_names()

    if 'row' not in tables:
        op.create_table(
            'row',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='sourcing'),
            sa.Column('budget_max', sa.Float(), nullable=True),
            sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='USD'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('choice_factors', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('choice_answers', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        )
        op.create_index(op.f('ix_row_user_id'), 'row', ['user_id'], unique=False)
        tables = inspector.get_table_names()

    if 'request_spec' not in tables:
        op.create_table(
            'request_spec',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('row_id', sa.Integer(), nullable=False),
            sa.Column('item_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('constraints', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('preferences', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.ForeignKeyConstraint(['row_id'], ['row.id']),
        )
        tables = inspector.get_table_names()

    if 'bid' not in tables:
        op.create_table(
            'bid',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('row_id', sa.Integer(), nullable=False),
            sa.Column('seller_id', sa.Integer(), nullable=True),
            sa.Column('price', sa.Float(), nullable=False),
            sa.Column('shipping_cost', sa.Float(), nullable=False, server_default='0'),
            sa.Column('total_cost', sa.Float(), nullable=False),
            sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='USD'),
            sa.Column('item_title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('item_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('eta_days', sa.Integer(), nullable=True),
            sa.Column('return_policy', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('condition', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='new'),
            sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='manual'),
            sa.Column('is_selected', sa.Boolean(), nullable=False, server_default='false'),
            sa.ForeignKeyConstraint(['row_id'], ['row.id']),
            sa.ForeignKeyConstraint(['seller_id'], ['seller.id']),
        )
        tables = inspector.get_table_names()

    if 'auth_login_code' not in tables:
        op.create_table(
            'auth_login_code',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('code_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('locked_until', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index(op.f('ix_auth_login_code_email'), 'auth_login_code', ['email'], unique=False)
        tables = inspector.get_table_names()

    if 'auth_session' not in tables:
        op.create_table(
            'auth_session',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('session_token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        )
        op.create_index(op.f('ix_auth_session_email'), 'auth_session', ['email'], unique=False)
        op.create_index(op.f('ix_auth_session_user_id'), 'auth_session', ['user_id'], unique=False)
        op.create_index(op.f('ix_auth_session_session_token_hash'), 'auth_session', ['session_token_hash'], unique=False)
        tables = inspector.get_table_names()

    if 'bug_report' not in tables:
        op.create_table(
            'bug_report',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('expected', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('actual', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('severity', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='low'),
            sa.Column('category', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='ui'),
            sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='captured'),
            sa.Column('attachments', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('diagnostics', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('github_issue_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('github_pr_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('preview_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        )
        op.create_index(op.f('ix_bug_report_user_id'), 'bug_report', ['user_id'], unique=False)
        tables = inspector.get_table_names()

    if 'clickout_event' not in tables:
        # ### commands auto generated by Alembic - please adjust! ###
        op.create_table('clickout_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('row_id', sa.Integer(), nullable=True),
        sa.Column('offer_index', sa.Integer(), nullable=False),
        sa.Column('canonical_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('final_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('merchant_domain', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('handler_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('affiliate_tag', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_clickout_event_merchant_domain'), 'clickout_event', ['merchant_domain'], unique=False)
        op.create_index(op.f('ix_clickout_event_row_id'), 'clickout_event', ['row_id'], unique=False)
        op.create_index(op.f('ix_clickout_event_user_id'), 'clickout_event', ['user_id'], unique=False)
        # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_clickout_event_user_id'), table_name='clickout_event')
    op.drop_index(op.f('ix_clickout_event_row_id'), table_name='clickout_event')
    op.drop_index(op.f('ix_clickout_event_merchant_domain'), table_name='clickout_event')
    op.drop_table('clickout_event')
    # ### end Alembic commands ###
