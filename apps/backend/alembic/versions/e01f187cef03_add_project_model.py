"""add_project_model

Revision ID: e01f187cef03
Revises: add_clerk_fields
Create Date: 2026-01-23 13:41:45.690440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e01f187cef03'
down_revision: Union[str, Sequence[str], None] = 'add_clerk_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = inspector.get_table_names()

    if 'project' not in tables:
        op.create_table(
            'project',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_project_user_id'), 'project', ['user_id'], unique=False)

    row_columns = [c['name'] for c in inspector.get_columns('row')]
    if 'project_id' not in row_columns:
        op.add_column('row', sa.Column('project_id', sa.Integer(), nullable=True))

    existing_indexes = {ix.get('name') for ix in inspector.get_indexes('row')}
    if op.f('ix_row_project_id') not in existing_indexes:
        op.create_index(op.f('ix_row_project_id'), 'row', ['project_id'], unique=False)

    existing_fks = {fk.get('name') for fk in inspector.get_foreign_keys('row')}
    fk_name = 'fk_row_project_id_project'
    if fk_name not in existing_fks:
        op.create_foreign_key(fk_name, 'row', 'project', ['project_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_row_project_id_project', 'row', type_='foreignkey')
    op.drop_index(op.f('ix_row_project_id'), table_name='row')
    op.drop_column('row', 'project_id')

    op.drop_index(op.f('ix_project_user_id'), table_name='project')
    op.drop_table('project')
