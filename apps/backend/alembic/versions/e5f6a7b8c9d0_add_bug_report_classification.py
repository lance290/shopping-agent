"""add bug_report classification columns

Revision ID: e5f6a7b8c9d0
Revises: d1e2f3a4b5c6, p4_phase4_models
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = ('d1e2f3a4b5c6', 'p4_phase4_models')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'bug_report' in inspector.get_table_names():
        existing = [c['name'] for c in inspector.get_columns('bug_report')]
        if 'classification' not in existing:
            op.add_column('bug_report', sa.Column('classification', sa.String(), nullable=True))
        if 'classification_confidence' not in existing:
            op.add_column('bug_report', sa.Column('classification_confidence', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('bug_report', 'classification_confidence')
    op.drop_column('bug_report', 'classification')
