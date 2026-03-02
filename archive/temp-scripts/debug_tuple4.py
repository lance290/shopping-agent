import sys, os, asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from apps.backend.database import get_session
from sqlmodel import select
from apps.backend.models import Seller, Vendor

async def main():
    async for session in get_session():
        stmt = select(Seller)
        try:
            res = await session.exec(stmt)
            print("OK")
        except Exception as e:
            print("ERROR:", e)

asyncio.run(main())
