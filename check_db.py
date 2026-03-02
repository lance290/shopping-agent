import sys
from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

import asyncio
import os
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))
from sqlalchemy import text
from apps.backend.database import engine

async def main():
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT id, row_id, item_title, price, image_url FROM "bid" WHERE row_id IN (112, 113) ORDER BY id DESC LIMIT 10'))
        print("BIDS FOR 112, 113:")
        for b in res.fetchall():
            print(dict(b._mapping))

asyncio.run(main())
