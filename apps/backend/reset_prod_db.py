"""
⚠️  DESTRUCTIVE — drops ALL tables and recreates them empty.
This will permanently delete all user data, vendor data, and outreach history.

Usage:
    python reset_prod_db.py --confirm-destroy-all-data

Safety:
    - Blocked entirely in production (RAILWAY_ENVIRONMENT / ENVIRONMENT=production).
    - Requires explicit --confirm-destroy-all-data flag.
    - Prints row counts before proceeding so you can see what you're about to lose.
"""
import asyncio
import os
import sys

from sqlmodel import SQLModel
from sqlalchemy import text
from database import engine


async def _count_rows(conn, table: str) -> int:
    try:
        result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
        return result.scalar() or 0
    except Exception:
        return -1  # table doesn't exist


async def reset_db():
    # ── Hard block in production ──
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production":
        print("❌  BLOCKED: reset_prod_db.py cannot run in production.")
        print("   If you truly need this, SSH in and run SQL manually with a backup first.")
        sys.exit(1)

    # ── Require explicit flag ──
    if "--confirm-destroy-all-data" not in sys.argv:
        print("⚠️  This script DESTROYS ALL DATA (users, vendors, rows, bids, everything).")
        print("   Run with:  python reset_prod_db.py --confirm-destroy-all-data")
        sys.exit(1)

    # ── Show what's about to be lost ──
    print("\n📊  Current data that will be PERMANENTLY DELETED:")
    key_tables = ["user", "seller", "row", "bid", "outreach_event", "seller_quote"]
    async with engine.begin() as conn:
        for table in key_tables:
            count = await _count_rows(conn, table)
            label = f"  {table}:"
            if count > 0:
                print(f"  ⚠️  {table}: {count} rows")
            elif count == 0:
                print(f"  ✓  {table}: empty")
            else:
                print(f"  -  {table}: (table not found)")

    # ── Final confirmation ──
    answer = input("\n🔴  Type 'DELETE EVERYTHING' to proceed: ")
    if answer.strip() != "DELETE EVERYTHING":
        print("Aborted.")
        sys.exit(0)

    print("\nResetting database...")
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(SQLModel.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Database reset complete. Run seed_vendors.py to restore vendor data.")


if __name__ == "__main__":
    asyncio.run(reset_db())
