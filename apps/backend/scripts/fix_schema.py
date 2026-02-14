"""One-shot schema sync: add all missing columns to the production DB.

Run during startup (start.sh) to patch any columns the code expects
but that Alembic migrations failed to create.  Idempotent — safe to
run on every boot.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

# (table, column, pg_type, default_expr_or_None)
EXPECTED = [
    ("bid", "liked_at", "TIMESTAMP", None),
    ("row", "last_engaged_at", "TIMESTAMP", None),
    ("auth_session", "expires_at", "TIMESTAMP", None),
    ("auth_session", "last_activity_at", "TIMESTAMP", "NOW()"),
    ("outreach_event", "status", "VARCHAR", "'pending'"),
    ("outreach_event", "timeout_hours", "INTEGER", "48"),
    ("outreach_event", "expired_at", "TIMESTAMP", None),
    ("outreach_event", "followup_sent_at", "TIMESTAMP", None),
    ("merchant", "verification_level", "VARCHAR", "'pending'"),
    ("merchant", "reputation_score", "FLOAT", "0.0"),
]


async def fix():
    added = 0
    async with engine.begin() as conn:
        for table, col, pgtype, default in EXPECTED:
            row = await conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ), {"t": table, "c": col})
            if row.first() is None:
                defstr = f" DEFAULT {default}" if default else ""
                await conn.execute(text(
                    f'ALTER TABLE "{table}" ADD COLUMN "{col}" {pgtype}{defstr}'
                ))
                print(f"[SCHEMA-FIX] + {table}.{col} ({pgtype})")
                added += 1
    if added:
        print(f"[SCHEMA-FIX] Added {added} missing column(s).")
    else:
        print("[SCHEMA-FIX] Schema is up to date.")


if __name__ == "__main__":
    asyncio.run(fix())
