import sys, os, asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from apps.backend.database import get_session
from sqlmodel import select
from apps.backend.models import Seller, Bid

async def main():
    async for session in get_session():
        stmt = select(Seller).where(Seller.name == "test")
        print("Stmt generated:", stmt)
        try:
            res = await session.exec(stmt)
            print("Result:", res.first())
        except Exception as e:
            print("Error executing stmt:", e)

asyncio.run(main())
