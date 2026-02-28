"""alter_embedding_type

Revision ID: alter_embedding_type
Revises: 5fe382b0c1b3
Create Date: 2026-02-26 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = 'alter_embedding_type'
down_revision: Union[str, Sequence[str], None] = '5fe382b0c1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # First ensure we have vector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Change the type of embedding from jsonb to vector(1536)
    op.execute("ALTER TABLE vendor ALTER COLUMN embedding TYPE vector(1536) USING (embedding::text::vector);")

def downgrade() -> None:
    op.execute("ALTER TABLE vendor ALTER COLUMN embedding TYPE jsonb USING (embedding::text::jsonb);")
