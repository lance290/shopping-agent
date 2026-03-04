"""DB cleanup script — free disk space by trimming old audit logs, clickout events, etc.

Usage:
    python scripts/cleanup_db.py              # dry-run (shows what would be deleted)
    python scripts/cleanup_db.py --execute    # actually delete
    python scripts/cleanup_db.py --days 30    # keep last 30 days (default: 90)
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DRY_RUN = "--execute" not in sys.argv
KEEP_DAYS = 90
for i, arg in enumerate(sys.argv):
    if arg == "--days" and i + 1 < len(sys.argv):
        KEEP_DAYS = int(sys.argv[i + 1])

CUTOFF = datetime.utcnow() - timedelta(days=KEEP_DAYS)


async def main():
    from database import engine
    from sqlalchemy import text

    mode = "DRY RUN" if DRY_RUN else "EXECUTING"
    print(f"[CLEANUP] Mode: {mode}")
    print(f"[CLEANUP] Keeping data newer than {CUTOFF.isoformat()} ({KEEP_DAYS} days)")
    print()

    # Tables to clean, ordered by expected size
    tables = [
        ("audit_log", "created_at"),
        ("clickout_event", "created_at"),
        ("outreach_event", "created_at"),
        ("auth_login_code", "created_at"),
    ]

    total_freed = 0

    async with engine.begin() as conn:
        # Show current DB size
        result = await conn.execute(text(
            "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size"
        ))
        db_size = result.scalar()
        print(f"[CLEANUP] Current database size: {db_size}")
        print()

        # Show table sizes
        print("[CLEANUP] Table sizes:")
        for table_name, _ in tables:
            try:
                result = await conn.execute(text(
                    f"SELECT pg_size_pretty(pg_total_relation_size('{table_name}')) AS size, "
                    f"(SELECT COUNT(*) FROM \"{table_name}\") AS row_count"
                ))
                row = result.first()
                if row:
                    print(f"  {table_name}: {row[0]} ({row[1]:,} rows)")
            except Exception as e:
                print(f"  {table_name}: error — {e}")
        print()

        # Also check for large tables we might not know about
        result = await conn.execute(text("""
            SELECT relname AS table_name,
                   pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                   pg_total_relation_size(relid) AS size_bytes
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC
            LIMIT 15
        """))
        print("[CLEANUP] Top 15 tables by size:")
        for row in result.fetchall():
            print(f"  {row[0]}: {row[1]}")
        print()

        # Check vendor embedding stats
        try:
            result = await conn.execute(text(
                "SELECT COUNT(*) AS total, "
                "COUNT(embedding) AS with_embedding, "
                "COUNT(*) - COUNT(embedding) AS without_embedding "
                "FROM vendor"
            ))
            row = result.first()
            if row:
                print(f"[CLEANUP] Vendor embedding stats: {row[0]} total, {row[1]} with embeddings, {row[2]} without")
        except Exception as e:
            print(f"[CLEANUP] Vendor embedding check failed: {e}")
        print()

        # Cleanup old rows
        for table_name, date_col in tables:
            try:
                # Count rows to delete
                result = await conn.execute(text(
                    f'SELECT COUNT(*) FROM "{table_name}" WHERE {date_col} < :cutoff'
                ), {"cutoff": CUTOFF})
                count = result.scalar() or 0

                if count == 0:
                    print(f"[CLEANUP] {table_name}: nothing to clean (0 rows before cutoff)")
                    continue

                if DRY_RUN:
                    print(f"[CLEANUP] {table_name}: would delete {count:,} rows older than {KEEP_DAYS} days")
                else:
                    await conn.execute(text(
                        f'DELETE FROM "{table_name}" WHERE {date_col} < :cutoff'
                    ), {"cutoff": CUTOFF})
                    print(f"[CLEANUP] {table_name}: deleted {count:,} rows")
                    total_freed += count

            except Exception as e:
                print(f"[CLEANUP] {table_name}: error — {e}")

        if not DRY_RUN and total_freed > 0:
            # VACUUM to actually reclaim disk space
            print()
            print(f"[CLEANUP] Deleted {total_freed:,} total rows. Running VACUUM...")

    # VACUUM must run outside a transaction
    if not DRY_RUN and total_freed > 0:
        async with engine.connect() as conn:
            await conn.execute(text("COMMIT"))
            for table_name, _ in tables:
                try:
                    await conn.execute(text(f'VACUUM "{table_name}"'))
                    print(f"[CLEANUP] VACUUM {table_name} done")
                except Exception as e:
                    print(f"[CLEANUP] VACUUM {table_name} failed: {e}")

        # Show new size
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size"
            ))
            new_size = result.scalar()
            print(f"\n[CLEANUP] Database size after cleanup: {new_size} (was {db_size})")

    if DRY_RUN:
        print("\n[CLEANUP] Dry run complete. Use --execute to actually delete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
