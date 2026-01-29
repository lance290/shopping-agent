"""add_like_and_comment_tables

Revision ID: f4a8d2c1e5b7
Revises: e01f187cef03
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f4a8d2c1e5b7'
down_revision: Union[str, Sequence[str], None] = 'e01f187cef03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create 'like' table
    if 'like' not in tables:
        op.create_table(
            'like',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('bid_id', sa.Integer(), nullable=True),
            sa.Column('offer_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('row_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['bid_id'], ['bid.id']),
            sa.ForeignKeyConstraint(['row_id'], ['row.id']),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_like_user_id'), 'like', ['user_id'], unique=False)
        op.create_index(op.f('ix_like_bid_id'), 'like', ['bid_id'], unique=False)
        op.create_index(op.f('ix_like_offer_url'), 'like', ['offer_url'], unique=False)
        op.create_index(op.f('ix_like_row_id'), 'like', ['row_id'], unique=False)

    # Create 'comment' table
    if 'comment' not in tables:
        op.create_table(
            'comment',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('bid_id', sa.Integer(), nullable=True),
            sa.Column('offer_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('row_id', sa.Integer(), nullable=True),
            sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('visibility', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='private'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['bid_id'], ['bid.id']),
            sa.ForeignKeyConstraint(['row_id'], ['row.id']),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_comment_user_id'), 'comment', ['user_id'], unique=False)
        op.create_index(op.f('ix_comment_bid_id'), 'comment', ['bid_id'], unique=False)
        op.create_index(op.f('ix_comment_offer_url'), 'comment', ['offer_url'], unique=False)
        op.create_index(op.f('ix_comment_row_id'), 'comment', ['row_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop comment table
    op.drop_index(op.f('ix_comment_row_id'), table_name='comment')
    op.drop_index(op.f('ix_comment_offer_url'), table_name='comment')
    op.drop_index(op.f('ix_comment_bid_id'), table_name='comment')
    op.drop_index(op.f('ix_comment_user_id'), table_name='comment')
    op.drop_table('comment')

    # Drop like table
    op.drop_index(op.f('ix_like_row_id'), table_name='like')
    op.drop_index(op.f('ix_like_offer_url'), table_name='like')
    op.drop_index(op.f('ix_like_bid_id'), table_name='like')
    op.drop_index(op.f('ix_like_user_id'), table_name='like')
    op.drop_table('like')
