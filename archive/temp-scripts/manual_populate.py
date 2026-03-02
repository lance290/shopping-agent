import sys, os, asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from apps.backend.database import get_session
from apps.backend.sourcing.service import SourcingService
from apps.backend.routes.rows_search import get_sourcing_repo
from apps.backend.models import Row

async def main():
    async for session in get_session():
        for row_id in [112, 113]:
            row = await session.get(Row, row_id)
            if row:
                print(f"Populating row {row_id} ({row.title})...")
                row.status = "bids_arriving"
                session.add(row)
                await session.commit()
                
                svc = SourcingService(session, get_sourcing_repo())
                try:
                    bids, statuses, msg = await svc.search_and_persist(row.id, row.title)
                    print(f"Row {row_id}: Saved {len(bids)} bids")
                except Exception as e:
                    print(f"Row {row_id}: Error: {e}")
            else:
                print(f"Row {row_id} not found.")

asyncio.run(main())
