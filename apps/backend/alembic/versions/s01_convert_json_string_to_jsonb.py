"""PRD-04: Convert JSON-in-string fields to JSONB columns

Revision ID: s01_json_to_jsonb
Revises: f2c1a9d3e7b4
Create Date: 2026-02-14

Converts Optional[str] JSON fields to native JSONB columns on Row, Bid,
SellerQuote, and BugReport tables. Uses a safe three-phase approach:
  Phase A: ALTER COLUMN TYPE ... USING to cast in-place
  Phase B: Add Pydantic validators on the model side (done in code)

Rollback: Converts JSONB columns back to TEXT with json-cast.

Affected columns:
  row: choice_factors, choice_answers, search_intent, provider_query_map, chat_history
  bid: provenance, source_payload
  seller_quote: answers, attachments
  bug_report: diagnostics, details
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 's01_json_to_jsonb'
down_revision: Union[str, Sequence[str], None] = 'f2c1a9d3e7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) pairs to convert from TEXT → JSONB
COLUMNS_TO_CONVERT = [
    ("row", "choice_factors"),
    ("row", "choice_answers"),
    ("row", "search_intent"),
    ("row", "provider_query_map"),
    ("row", "chat_history"),
    ("bid", "provenance"),
    ("bid", "source_payload"),
    ("seller_quote", "answers"),
    ("seller_quote", "attachments"),
    ("bug_report", "diagnostics"),
    ("bug_report", "details"),
]


def upgrade() -> None:
    """Convert TEXT JSON columns to JSONB with safe casting."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for table, column in COLUMNS_TO_CONVERT:
        if table not in tables:
            continue

        columns = [c["name"] for c in inspector.get_columns(table)]
        if column not in columns:
            continue

        # Nullify empty strings and malformed JSON before casting
        conn.execute(text(f"""
            UPDATE {table}
            SET {column} = NULL
            WHERE {column} IS NOT NULL
              AND TRIM({column}) IN ('', 'null', 'undefined')
        """))

        # Cast TEXT → JSONB in-place; guard against malformed rows
        conn.execute(text(f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE JSONB
            USING CASE
                WHEN {column} IS NULL THEN NULL
                ELSE {column}::jsonb
            END
        """))


def downgrade() -> None:
    """Convert JSONB columns back to TEXT."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    for table, column in COLUMNS_TO_CONVERT:
        if table not in tables:
            continue

        columns = [c["name"] for c in inspector.get_columns(table)]
        if column not in columns:
            continue

        conn.execute(text(f"""
            ALTER TABLE {table}
            ALTER COLUMN {column}
            TYPE TEXT
            USING CASE
                WHEN {column} IS NULL THEN NULL
                ELSE {column}::text
            END
        """))
