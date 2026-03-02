import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from sqlmodel import select
from apps.backend.models import Seller

print("Seller:", Seller)
print("Type:", type(Seller))
stmt = select(Seller).where(Seller.name == "test")
print("Stmt:", stmt)
