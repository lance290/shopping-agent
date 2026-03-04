import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine
from sqlmodel import text

async def migrate_data():
    """Copy data from old managed Postgres to current pgvector DB."""
    if not OLD_DATABASE_URL:
        print("[MIGRATE] OLD_DATABASE_URL not set, skipping migration.")
        return

    if not RUN_LEGACY_MIGRATION:
        print("[MIGRATE] RUN_LEGACY_MIGRATION is disabled, skipping migration.")
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


async def reset_vendor_sequence():
    """Reset vendor id sequence to MAX(id) to prevent UniqueViolationError after restore."""
    from database import engine
    async with engine.begin() as conn:
        await conn.execute(text(
            "SELECT setval(pg_get_serial_sequence('vendor','id'), "
            "COALESCE((SELECT MAX(id) FROM vendor), 1))"
        ))
    print("[FIX] vendor id sequence reset to MAX(id).")


async def main():
    from database import engine
    # Fast-fail: try to connect with a short timeout so we don't block startup
    import asyncio as _aio
    try:
        async with _aio.timeout(30):
            async with engine.begin() as conn:
                await fix_schema(conn)
    except (TimeoutError, Exception) as e:
        print(f"[SCHEMA-FIX] ERROR: DB connection failed ({type(e).__name__}: {e}). Skipping schema fix.")
        return
    try:
        async with _aio.timeout(15):
            await reset_vendor_sequence()
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: vendor sequence reset failed: {e}")
    try:
        async with _aio.timeout(15):
            await migrate_data()
    except Exception as e:
        print(f"[SCHEMA-FIX] WARNING: data migration failed: {e}")
    if RUN_USER_PHONE_MERGE:
        try:
            async with _aio.timeout(15):
                await merge_phone_to_user1()
        except Exception as e:
            print(f"[SCHEMA-FIX] WARNING: phone merge failed: {e}")
    else:
        print("[MERGE] RUN_USER_PHONE_MERGE is disabled, skipping phone merge step.")


if __name__ == "__main__":
    asyncio.run(main())
