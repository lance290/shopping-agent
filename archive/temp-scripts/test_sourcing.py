import sys
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime

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

import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

async def main():
    async for session in get_session():
        # Insert a user if missing to avoid foreign key error
        await session.execute(text("INSERT INTO \"user\" (id, email, created_at) VALUES (999, 'test999@example.com', :now) ON CONFLICT DO NOTHING"), {"now": datetime.utcnow()})
        await session.commit()
        
        row = Row(user_id=999, title="Ice Cream", status="sourcing")
        session.add(row)
        await session.commit()
        await session.refresh(row)
        
        print("Created row", row.id)
        
        svc = SourcingService(session, get_sourcing_repo())
        bids, statuses, msg = await svc.search_and_persist(row.id, "Ice Cream")
        print(f"Found {len(bids)} bids")

asyncio.run(main())
