import sys, os, asyncio

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from apps.backend.database import get_session
from sqlmodel import select
from apps.backend.models.bids import Vendor

async def main():
    async for session in get_session():
        try:
            stmt = select(Vendor).limit(1)
            res = await session.exec(stmt)
            print("OK", res.all())
        except Exception as e:
            print("ERROR:", e)

asyncio.run(main())
