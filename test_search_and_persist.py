import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")

from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))
from sqlalchemy import text
from apps.backend.database import get_session, engine
from apps.backend.sourcing.service import SourcingService
from apps.backend.routes.rows_search import get_sourcing_repo
from apps.backend.models import Row

async def main():
    async for session in get_session():
        # Create a test row
        row = Row(user_id=1, title="Ice Cream", status="sourcing")
        session.add(row)
        await session.commit()
        await session.refresh(row)
        print("Created row", row.id)
        
        svc = SourcingService(session, get_sourcing_repo())
        bids, statuses, msg = await svc.search_and_persist(row.id, "Ice Cream")
        print(f"Found {len(bids)} bids")
        for b in bids:
            print(f"- {b.item_title} / {b.price}")

asyncio.run(main())
