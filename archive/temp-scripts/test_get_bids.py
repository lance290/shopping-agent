import sys
import os
import asyncio

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
        for r in res.fetchall():
            print(r[0])
            
asyncio.run(main())
