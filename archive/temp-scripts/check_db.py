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
        res = await conn.execute(text("SELECT id, row_id, item_title, price, image_url, source FROM bid ORDER BY id DESC LIMIT 20"))
        print("BIDS:")
        for b in res.fetchall():
            print(dict(b._mapping))
            
        res = await conn.execute(text("SELECT id, title, status, provider_query FROM row ORDER BY id DESC LIMIT 10"))
        print("\nROWS:")
        for r in res.fetchall():
            print(dict(r._mapping))

asyncio.run(main())
