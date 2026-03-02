import sys, os, asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

# Mock pgvector before loading models
from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

from apps.backend.database import get_session
from sqlmodel import select
from apps.backend.models import Seller, Vendor

async def main():
    print(f"Seller type: {type(Seller)}")
    print(f"Vendor type: {type(Vendor)}")
    
    async for session in get_session():
        try:
            stmt = select(Seller).where(Seller.name == "Kroger")
            print("Stmt:", stmt)
            res = await session.exec(stmt)
            print("Result:", res.first())
        except Exception as e:
            print(f"Error type: {type(e)}")
            print(f"Error: {e}")

asyncio.run(main())
