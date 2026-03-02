import sys
import os
import asyncio

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))
from sqlmodel import select
from apps.backend.database import engine, get_session
from apps.backend.models.bids import Vendor, Seller, Bid
from apps.backend.models.rows import Row

async def main():
    async for session in get_session():
        print("Testing select(Seller)...")
        try:
            stmt = select(Seller).where(Seller.name == "test")
            res = await session.exec(stmt)
            print("Seller ok")
        except Exception as e:
            print("Seller error:", e)
            
        print("Testing select(Bid)...")
        try:
            stmt = select(Bid).where(Bid.row_id == 1)
            res = await session.exec(stmt)
            print("Bid ok")
        except Exception as e:
            print("Bid error:", e)

asyncio.run(main())
