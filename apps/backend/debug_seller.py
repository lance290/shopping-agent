import asyncio
from database import get_session
from models import Seller
from sqlmodel import select

async def main():
    async for session in get_session():
        stmt = select(Seller).where(Seller.name == "test")
        print("Stmt:", stmt)
        try:
            res = await session.exec(stmt)
            print("OK")
        except Exception as e:
            print("ERROR:", e)

asyncio.run(main())
