import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv("apps/backend/.env")
sys.path.append(os.path.join(os.getcwd(), 'apps/backend'))

from sqlalchemy import text
from apps.backend.database import engine

async def main():
    async with engine.connect() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.commit()
            print("Vector extension created successfully")
        except Exception as e:
            print("Error:", e)

asyncio.run(main())
