import sys
import os
import asyncio
from dotenv import load_dotenv

# Load env before anything else
load_dotenv("apps/backend/.env")

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))
from sqlalchemy import text
from apps.backend.database import engine

async def main():
    async with engine.connect() as conn:
        print("Checking actual tables...")
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [r[0] for r in res.fetchall()]
        print("TABLES:", tables)
        
        if 'row' in tables:
            res = await conn.execute(text("SELECT id, title, status FROM row ORDER BY id DESC LIMIT 5"))
            print("\nROWS:")
            for r in res.fetchall():
                print(dict(r._mapping))
                
        if 'bid' in tables:
            res = await conn.execute(text("SELECT id, row_id, item_title, price FROM bid ORDER BY id DESC LIMIT 5"))
            print("\nBIDS:")
            for b in res.fetchall():
                print(dict(b._mapping))

asyncio.run(main())
