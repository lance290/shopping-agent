import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

import asyncio
from sqlmodel import select
from apps.backend.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from apps.backend.models.coupons import PopSwap

async def main():
    async with AsyncSession(engine) as session:
        result = await session.execute(select(PopSwap))
        swaps = result.scalars().all()
        for s in swaps:
            print(f"ID: {s.id}, Title: {s.swap_product_name}, Img: {s.swap_product_image}, Savings: {s.savings_cents}, Provider: {s.provider}, Target: {s.target_product}")

if __name__ == "__main__":
    asyncio.run(main())
