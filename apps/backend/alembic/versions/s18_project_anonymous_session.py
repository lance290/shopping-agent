"""Add anonymous_session_id to Project

Revision ID: s18_project_anon
Revises: c7e4d2a1b9f0
Create Date: 2026-03-07 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "s18_project_anon"
down_revision: Union[str, Sequence[str], None] = "c7e4d2a1b9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    try:
        return {idx["name"] for idx in inspector.get_indexes(table_name)}
    except Exception:
        return set()

def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "project" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("project")}
        if "anonymous_session_id" not in existing_cols:
            op.add_column("project", sa.Column("anonymous_session_id", sa.String(), nullable=True))
        
        project_indexes = _index_names(inspector, "project")
        if "ix_project_anonymous_session_id" not in project_indexes:
            op.create_index("ix_project_anonymous_session_id", "project", ["anonymous_session_id"])

def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "project" in existing_tables:
        existing_cols = {c["name"] for c in inspector.get_columns("project")}
        project_indexes = _index_names(inspector, "project")
        
        if "ix_project_anonymous_session_id" in project_indexes:
            op.drop_index("ix_project_anonymous_session_id", table_name="project")
            
        if "anonymous_session_id" in existing_cols:
            op.drop_column("project", "anonymous_session_id")
