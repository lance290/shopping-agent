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
# Use tuple (old_name, new_name) for renamed tables
MIGRATE_TABLES = [
    "user",
    "seller",
    "project",
    "row",
    ("requestspec", "request_spec"),  # renamed table
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

    # Skip if migration fully completed (user 1 has phone AND request_spec has data)
    async with target_engine.begin() as tconn:
        row = await tconn.execute(text(
            "SELECT phone_number FROM \"user\" WHERE id = 1"
        ))
        u1 = row.first()
        rs = await tconn.execute(text("SELECT COUNT(*) FROM request_spec"))
        rs_count = rs.scalar() or 0
        if u1 and u1[0] == "+16503398297" and rs_count > 0:
            print(f"[MIGRATE] Migration already complete (user 1 has phone, {rs_count} request_specs). Skipping.")
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

    # Migrate each table in its own transaction to avoid one failure killing all
    for entry in MIGRATE_TABLES:
        # Support tuple (old_name, new_name) for renamed tables
        if isinstance(entry, tuple):
            src_table, dst_table = entry
        else:
            src_table = dst_table = entry

        try:
            # Read from old DB
            async with old_engine.begin() as oconn:
                cols_result = await oconn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t ORDER BY ordinal_position"
                ), {"t": src_table})
                old_cols = [r[0] for r in cols_result.fetchall()]
                if not old_cols:
                    continue

                # Read target columns in separate connection
                async with target_engine.begin() as tconn:
                    tcols_result = await tconn.execute(text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t ORDER BY ordinal_position"
                    ), {"t": dst_table})
                    target_cols = set(r[0] for r in tcols_result.fetchall())

                if not target_cols:
                    print(f"[MIGRATE] Table {dst_table} doesn't exist in target, skipping.")
                    continue

                common_cols = [c for c in old_cols if c in target_cols]
                if not common_cols:
                    continue

                col_list = ", ".join(f'"{c}"' for c in common_cols)

                # Fetch all data from old DB
                rows = await oconn.execute(text(f'SELECT {col_list} FROM "{src_table}"'))
                all_rows = rows.fetchall()

            # Write to target DB — NEVER delete existing data
            async with target_engine.begin() as tconn:
                await tconn.execute(text("SET session_replication_role = 'replica'"))

                inserted = 0
                if all_rows:
                    placeholders = ", ".join(f":c{i}" for i in range(len(common_cols)))
                    insert_sql = (
                        f'INSERT INTO "{dst_table}" ({col_list}) VALUES ({placeholders}) '
                        f'ON CONFLICT DO NOTHING'
                    )
                    for row_data in all_rows:
                        params = {f"c{i}": v for i, v in enumerate(row_data)}
                        res = await tconn.execute(text(insert_sql), params)
                        inserted += res.rowcount

                # Fix sequence for this table
                try:
                    await tconn.execute(text(f"""
                        SELECT setval(pg_get_serial_sequence('"{dst_table}"', 'id'),
                               COALESCE((SELECT MAX(id) FROM "{dst_table}"), 1))
                    """))
                except Exception:
                    pass

                await tconn.execute(text("SET session_replication_role = 'origin'"))

            label = f"{src_table}->{dst_table}" if src_table != dst_table else dst_table
            skipped = len(all_rows) - inserted if all_rows else 0
            print(f"[MIGRATE] {label}: {inserted} inserted, {skipped} already existed")

        except Exception as e:
            print(f"[MIGRATE] {dst_table}: ERROR - {e}")

    await old_engine.dispose()
    print("[MIGRATE] Data migration complete!")


async def merge_phone_to_user1():
    """Ensure phone +16503398297 is on user 1 (lance@xcor-cto.com), not user 6."""
    from database import engine
    async with engine.begin() as conn:
        # Log current state
        row = await conn.execute(text(
            "SELECT id, email, phone_number FROM \"user\" WHERE id IN (1, 6) ORDER BY id"
        ))
        users = row.fetchall()
        for u in users:
            print(f"[MERGE] User {u[0]}: email={u[1]}, phone={u[2]}")

        # Always force: clear phone from ALL users except user 1
        await conn.execute(text(
            "UPDATE \"user\" SET phone_number = NULL WHERE phone_number = '+16503398297' AND id != 1"
        ))
        # Set phone on user 1
        await conn.execute(text(
            "UPDATE \"user\" SET phone_number = '+16503398297' WHERE id = 1"
        ))

        # Reassign user 6's rows, projects, sessions to user 1
        for tbl in ["row", "project", "auth_session", "auth_login_code"]:
            try:
                res = await conn.execute(text(
                    f'UPDATE "{tbl}" SET user_id = 1 WHERE user_id = 6'
                ))
                if res.rowcount > 0:
                    print(f"[MERGE] Reassigned {res.rowcount} {tbl} rows from user 6 -> 1")
            except Exception as e:
                print(f"[MERGE] {tbl}: {e}")

        # Verify
        row = await conn.execute(text(
            "SELECT phone_number FROM \"user\" WHERE id = 1"
        ))
        u1 = row.first()
        print(f"[MERGE] Done. User 1 phone = {u1[0] if u1 else 'NOT FOUND'}")


async def main():
    from database import engine
    async with engine.begin() as conn:
        await fix_schema(conn)
    await migrate_data()
    await merge_phone_to_user1()


if __name__ == "__main__":
    asyncio.run(main())
