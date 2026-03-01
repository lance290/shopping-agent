import asyncio
from sqlmodel import select
import sys
import os

# Ensure backend is in pythonpath
sys.path.append(os.path.dirname(__file__))

from database import get_session
from models.coupons import PopSwap
import contextlib

async def main():
    async for session in get_session():
        result = await session.execute(select(PopSwap))
        swaps = result.scalars().all()
        for s in swaps:
            print(f"ID: {s.id}, Title: {s.swap_product_name}, Img: {s.swap_product_image}, Savings: {s.savings_cents}, Provider: {s.provider}, Target: {s.target_product}")

if __name__ == "__main__":
    asyncio.run(main())
