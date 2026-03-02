import asyncio
from sqlmodel import select
from database import get_session, engine
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Row, Bid

async def main():
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Row).order_by(Row.id.desc()).limit(1))
        row = result.first()
        if not row:
            print("No rows found")
            return
        
        print(f"Latest Row ID: {row.id}, Title: {row.title}")
        
        result = await session.exec(select(Bid).where(Bid.row_id == row.id, Bid.is_superseded == False))
        bids = result.all()
        
        print(f"Total active bids: {len(bids)}")
        for b in bids:
            print(f" - {b.source}: {b.item_title[:30]}... ({b.item_url})")

asyncio.run(main())
