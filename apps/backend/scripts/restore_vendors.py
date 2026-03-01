
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
from sqlalchemy import text
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

    # Check DB state
    try:
        await session.exec(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✅ Checked 'vector' extension.")
        
        # Check table columns
        result = await session.exec(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'vendor'"))
        db_cols = result.fetchall()
        print(f"DB Columns: {db_cols}")
    except Exception as e:
        print(f"⚠️ Error checking DB state: {e}")

    # Get valid columns from model
    valid_columns = set(Vendor.__table__.columns.keys())
    print(f"Model Columns: {valid_columns}")
    
    # Identify text fields that need stringification if they contain dicts/lists
    # NOTE: service_areas is sa.JSON (jsonb) in DB — do NOT stringify it
    text_fields = ["specialties", "provenance"]

    # Let's clean data for insertion
    cleaned_vendors = []
    for i, v in enumerate(vendors_data):
        clean_v = {}
        
        # Only keep valid columns
        for key, val in v.items():
            if key in valid_columns:
                clean_v[key] = val
        
        # service_areas is dead weight and causing JSONB vs VARCHAR cast issues
        # Clear it to None
        if "service_areas" in clean_v:
            clean_v["service_areas"] = None
        
        # Fix datetimes
        for field in ["created_at", "updated_at", "embedded_at"]:
            if clean_v.get(field):
                try:
                    if isinstance(clean_v[field], str):
                        clean_v[field] = datetime.fromisoformat(clean_v[field])
                except (ValueError, TypeError):
                    clean_v[field] = None
        
        # Stringify structured data for text fields
        for field in text_fields:
            if clean_v.get(field) and not isinstance(clean_v[field], str):
                try:
                    clean_v[field] = json.dumps(clean_v[field])
                except Exception:
                    pass # Leave as is if fail
        
        # Handle embedding
        if clean_v.get("embedding"):
            if isinstance(clean_v["embedding"], str):
                try:
                    clean_v["embedding"] = json.loads(clean_v["embedding"])
                except Exception:
                    clean_v["embedding"] = None
            
            if isinstance(clean_v["embedding"], list):
                if len(clean_v["embedding"]) != 1536:
                    if i < 5:
                        print(f"⚠️ Vendor {clean_v.get('id')} embedding length {len(clean_v['embedding'])} != 1536")
                    clean_v["embedding"] = None
            else:
                clean_v["embedding"] = None

        cleaned_vendors.append(clean_v)

    # Chunking
    batch_size = 10
    total = len(cleaned_vendors)
    
    for i in range(0, total, batch_size):
        batch = cleaned_vendors[i:i+batch_size]
        
        stmt = insert(Vendor).values(batch)
        
        update_dict = {
            c.name: c 
            for c in stmt.excluded 
            if c.name in valid_columns and c.name not in ["id", "created_at"]
        }
        
        do_update_stmt = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_=update_dict
        )
        
        try:
            await session.execute(do_update_stmt)
            await session.commit()
            if i % 100 == 0:
                print(f"Processed {min(i+batch_size, total)}/{total}")
        except Exception as e:
            # Print concise error
            err_str = str(e)
            if len(err_str) > 500:
                err_str = err_str[:500] + "... [truncated]"
            print(f"❌ Error batch {i} (first item id={batch[0].get('id')}): {err_str}")
            await session.rollback()

    # Reset the sequence so new inserts don't conflict with restored IDs
    try:
        async with session.bind.connect() as conn:
            await conn.execute(text(
                "SELECT setval(pg_get_serial_sequence('vendor', 'id'), "
                "(SELECT MAX(id) FROM vendor))"
            ))
            await conn.commit()
        print("✅ Sequence reset to MAX(id).")
    except Exception as e:
        print(f"⚠️  Sequence reset failed (non-fatal): {e}")

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
