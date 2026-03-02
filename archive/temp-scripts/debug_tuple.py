import sys, os, asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

from apps.backend.database import get_session
from sqlmodel import select
from apps.backend.models import Seller, Vendor

async def main():
    print(f"Seller type: {type(Seller)}")
    print(f"Vendor type: {type(Vendor)}")
    
    stmt = select(Seller)
    print("Type of stmt:", type(stmt))
    print("Stmt string:", str(stmt))

asyncio.run(main())
