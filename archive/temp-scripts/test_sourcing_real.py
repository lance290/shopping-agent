import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from sqlalchemy import text
from apps.backend.database import get_session
from apps.backend.sourcing.service import SourcingService
from apps.backend.routes.rows_search import get_sourcing_repo

async def main():
    async for session in get_session():
        print("Checking SourcingService")
        
        # Test finding a row
        res = await session.execute(text("SELECT id, title FROM row ORDER BY id DESC LIMIT 1"))
        row = res.first()
        if not row:
            print("No rows found")
            return
            
        print(f"Sourcing for row {row.id} - {row.title}")
        svc = SourcingService(session, get_sourcing_repo())
        bids, statuses, msg = await svc.search_and_persist(row.id, row.title)
        
        print(f"Found {len(bids)} bids")
        for b in bids:
            print(f"- {b.item_title} / {b.price}")

asyncio.run(main())
