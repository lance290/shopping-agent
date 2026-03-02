import sys, os, asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

from apps.backend.database import engine
from sqlmodel import select
from apps.backend.models import Seller, Vendor

print(type(Seller), Seller)

stmt = select(Seller)
print(stmt.compile(engine))

