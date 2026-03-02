import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))
from sqlalchemy import text
from apps.backend.database import engine

async def main():
    async with engine.connect() as conn:
        print("Checking tables...")
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        tables = [r[0] for r in res.fetchall()]
        print("TABLES:", tables)
        
        if 'vendor' in tables:
            res = await conn.execute(text("SELECT count(*) FROM vendor"))
            print("Vendors:", res.scalar())
            
        if 'pop_swap' in tables:
            res = await conn.execute(text("SELECT id, swap_product_name, swap_product_image FROM pop_swap LIMIT 5"))
            print("SWAPS:")
            for s in res.fetchall():
                print(dict(s._mapping))
                
asyncio.run(main())
