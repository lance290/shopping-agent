import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from apps.backend.database import get_session
from apps.backend.models import Seller
from sqlmodel import select

async def main():
    print(f"Seller is {Seller} of type {type(Seller)}")
    async for session in get_session():
        stmt = select(Seller).where(Seller.name == "test")
        print(f"Statement: {stmt}")
        try:
            res = await session.exec(stmt)
            print("Exec OK", res.first())
        except Exception as e:
            print("Error:", e)

asyncio.run(main())
