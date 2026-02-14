"""One-shot schema sync + data migration.

1. Add missing columns to the current (pgvector) DB.
2. Ensure request_spec table exists (model uses snake_case).
3. If OLD_DATABASE_URL is set, migrate data from the old managed Postgres.

Idempotent — safe to run on every boot.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")
# One-time migration: old managed Postgres on Railway internal network
OLD_DATABASE_URL = os.environ.get(
    "OLD_DATABASE_URL",
    "postgresql://postgres:fWObfWzOKVFUIIuxSwqsfJlRFsCozCSi@postgres.railway.internal:5432/railway"
)

# (table, column, pg_type, default_expr_or_None)
EXPECTED_COLS = [
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

# Tables to migrate (order matters for FK constraints)
MIGRATE_TABLES = [
    "user",
    "seller",
    "project",
    "row",
    "requestspec",
    "bid",
    "auth_login_code",
    "auth_session",
    "audit_log",
    "bug_report",
    "clickout_event",
    "comment",
    "contract",
    "deal_handoff",
    "like",
    "merchant",
    "notification",
    "outreach_event",
    "purchase_event",
    "purchaseevent",
    "seller_bookmark",
    "seller_quote",
    "share_link",
    "share_search_event",
    "user_preference",
    "user_signal",
]


async def fix_schema(conn):
    """Add missing columns."""
    added = 0
    for table, col, pgtype, default in EXPECTED_COLS:
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

    # Ensure request_spec table exists (model uses __tablename__='request_spec')
    row = await conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'request_spec'"
    ))
    if row.first() is None:
        # Check if requestspec exists (old naming)
        row2 = await conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'requestspec'"
        ))
        if row2.first() is not None:
            await conn.execute(text('ALTER TABLE "requestspec" RENAME TO "request_spec"'))
            print("[SCHEMA-FIX] Renamed requestspec -> request_spec")
            added += 1
        else:
            await conn.execute(text("""
                CREATE TABLE request_spec (
                    id SERIAL PRIMARY KEY,
                    item_name VARCHAR NOT NULL,
                    constraints VARCHAR NOT NULL,
                    preferences VARCHAR,
                    row_id INTEGER REFERENCES "row"(id)
                )
            """))
            print("[SCHEMA-FIX] Created request_spec table")
            added += 1

    if added:
        print(f"[SCHEMA-FIX] Fixed {added} schema issue(s).")
    else:
        print("[SCHEMA-FIX] Schema is up to date.")


async def migrate_data():
    """Copy data from old managed Postgres to current pgvector DB."""
    if not OLD_DATABASE_URL:
        print("[MIGRATE] OLD_DATABASE_URL not set, skipping migration.")
        return

    from database import engine as target_engine

    # Check if migration already happened (old DB has user with phone, new doesn't yet)
    async with target_engine.begin() as tconn:
        row = await tconn.execute(text(
            "SELECT COUNT(*) FROM \"row\" WHERE title LIKE '%private jet%' OR title LIKE '%Private jet%'"
        ))
        count = row.scalar()
        if count and count > 0:
            # Check if it's the old local data or real production data
            row2 = await tconn.execute(text("SELECT COUNT(*) FROM \"row\""))
            total = row2.scalar()
            if total and total >= 20:
                print(f"[MIGRATE] Already have {total} rows including production data. Skipping.")
                return

    # Normalize old URL for asyncpg
    old_url = OLD_DATABASE_URL
    if old_url.startswith("postgresql://"):
        old_url = old_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    old_engine = create_async_engine(old_url, pool_size=5)

    print("[MIGRATE] Connecting to old database...")
    try:
        async with old_engine.begin() as oconn:
            row = await oconn.execute(text('SELECT COUNT(*) FROM "row"'))
            old_count = row.scalar()
            print(f"[MIGRATE] Old DB has {old_count} rows.")
    except Exception as e:
        print(f"[MIGRATE] ERROR connecting to old DB: {e}")
        await old_engine.dispose()
        return

    async with target_engine.begin() as tconn:
        # Disable FK checks during migration
        await tconn.execute(text("SET session_replication_role = 'replica'"))

        for table in MIGRATE_TABLES:
            try:
                # Get columns from old DB
                async with old_engine.begin() as oconn:
                    cols_result = await oconn.execute(text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t ORDER BY ordinal_position"
                    ), {"t": table})
                    old_cols = [r[0] for r in cols_result.fetchall()]

                    if not old_cols:
                        continue

                    # Get columns from target DB
                    tcols_result = await tconn.execute(text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t ORDER BY ordinal_position"
                    ), {"t": table})
                    target_cols = set(r[0] for r in tcols_result.fetchall())

                    if not target_cols:
                        print(f"[MIGRATE] Table {table} doesn't exist in target, skipping.")
                        continue

                    # Only copy columns that exist in both
                    common_cols = [c for c in old_cols if c in target_cols]
                    if not common_cols:
                        continue

                    col_list = ", ".join(f'"{c}"' for c in common_cols)

                    # Truncate target table
                    await tconn.execute(text(f'DELETE FROM "{table}"'))

                    # Fetch all rows from old DB
                    rows = await oconn.execute(text(f'SELECT {col_list} FROM "{table}"'))
                    all_rows = rows.fetchall()

                    if not all_rows:
                        print(f"[MIGRATE] {table}: 0 rows (empty)")
                        continue

                    # Insert in batches
                    placeholders = ", ".join(f":c{i}" for i in range(len(common_cols)))
                    insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

                    for row_data in all_rows:
                        params = {f"c{i}": v for i, v in enumerate(row_data)}
                        await tconn.execute(text(insert_sql), params)

                    print(f"[MIGRATE] {table}: {len(all_rows)} rows copied")

            except Exception as e:
                print(f"[MIGRATE] {table}: ERROR - {e}")

        # Fix sequences
        for table in MIGRATE_TABLES:
            try:
                await tconn.execute(text(f"""
                    SELECT setval(pg_get_serial_sequence('"{table}"', 'id'),
                           COALESCE((SELECT MAX(id) FROM "{table}"), 1))
                """))
            except Exception:
                pass  # Table may not have id column

        # Re-enable FK checks
        await tconn.execute(text("SET session_replication_role = 'origin'"))

    await old_engine.dispose()
    print("[MIGRATE] Data migration complete!")


async def merge_phone_to_user1():
    """Merge phone +16503398297 from user 6 to user 1 (lance@xcor-cto.com)."""
    from database import engine
    async with engine.begin() as conn:
        # Check if user 1 already has the phone
        row = await conn.execute(text(
            "SELECT phone_number FROM \"user\" WHERE id = 1"
        ))
        u1 = row.first()
        if u1 and u1[0] == "+16503398297":
            print("[MERGE] User 1 already has phone. Skipping.")
            return

        # Check user 6 has the phone
        row = await conn.execute(text(
            "SELECT phone_number FROM \"user\" WHERE id = 6"
        ))
        u6 = row.first()
        if not u6 or u6[0] != "+16503398297":
            print("[MERGE] User 6 doesn't have expected phone. Skipping.")
            return

        # Move phone to user 1
        await conn.execute(text(
            "UPDATE \"user\" SET phone_number = '+16503398297' WHERE id = 1"
        ))
        await conn.execute(text(
            "UPDATE \"user\" SET phone_number = NULL WHERE id = 6"
        ))

        # Reassign user 6's rows, projects, sessions to user 1
        for tbl in ["row", "project", "auth_session", "auth_login_code"]:
            try:
                await conn.execute(text(
                    f'UPDATE "{tbl}" SET user_id = 1 WHERE user_id = 6'
                ))
            except Exception:
                pass

        print("[MERGE] Merged phone +16503398297 from user 6 -> user 1")


async def main():
    from database import engine
    async with engine.begin() as conn:
        await fix_schema(conn)
    await migrate_data()
    await merge_phone_to_user1()


if __name__ == "__main__":
    asyncio.run(main())
