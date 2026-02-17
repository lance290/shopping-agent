
import asyncio
import gzip
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from models.bids import Vendor

# Prod DB URL from env
DATABASE_URL = os.getenv("DATABASE_URL")

async def restore_vendors_logic(session: AsyncSession):
    # Path to gzipped dump
    dump_path = Path(__file__).parent.parent / "data/vendors_prod_dump.json.gz"
    if not dump_path.exists():
        # Try uncompressed
        dump_path = Path(__file__).parent.parent / "data/vendors_prod_dump.json"
        
    if not dump_path.exists():
        print(f"❌ Dump file not found at {dump_path}")
        raise FileNotFoundError(f"Dump file not found at {dump_path}")

    print(f"Reading dump from {dump_path}...")
    
    try:
        if str(dump_path).endswith(".gz"):
            with gzip.open(dump_path, "rt", encoding="utf-8") as f:
                vendors_data = json.load(f)
        else:
            with open(dump_path, "r", encoding="utf-8") as f:
                vendors_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read dump: {e}")
        raise

    print(f"Loaded {len(vendors_data)} vendors. Starting import...")

    # Let's clean data for insertion
    cleaned_vendors = []
    for v in vendors_data:
        # Fix datetimes
        for field in ["created_at", "updated_at", "embedded_at"]:
            if v.get(field):
                try:
                    v[field] = datetime.fromisoformat(v[field])
                except (ValueError, TypeError):
                    v[field] = None
        
        # Remove keys that might not match model exactly if schema changed, but here schema is same.
        # Handle embedding: ensure it's a list or None
        if v.get("embedding"):
            # if it came from dump as list, it's fine.
            pass
        
        cleaned_vendors.append(v)

    # Chunking
    batch_size = 100
    total = len(cleaned_vendors)
    
    for i in range(0, total, batch_size):
        batch = cleaned_vendors[i:i+batch_size]
        
        # Using Core INSERT for ON CONFLICT support
        stmt = insert(Vendor).values(batch)
        
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ["id", "created_at"]}
        
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=['id'], # Assuming we are syncing by ID
            set_=update_dict
        )
        
        await session.execute(do_update_stmt)
        await session.commit()
        print(f"Processed {min(i+batch_size, total)}/{total}")

    print("✅ Restore complete.")
    return total

async def restore_vendors():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return

    print(f"Connecting to DB...")
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        await restore_vendors_logic(session)

if __name__ == "__main__":
    asyncio.run(restore_vendors())
