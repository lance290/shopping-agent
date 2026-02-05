import asyncio
import os
import sys
from sqlalchemy import text
from sqlmodel import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path to import models/database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DATABASE_URL

async def migrate():
    print(f"Migrating database at {DATABASE_URL}")
    
    # Configure connection args for production (Railway) if needed
    connect_args = {}
    if os.getenv("RAILWAY_ENVIRONMENT"):
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    engine = create_async_engine(DATABASE_URL, echo=True, future=True, connect_args=connect_args)

    async with engine.begin() as conn:
        print("Checking for existing columns...")
        
        # Check if classification column exists
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'bug_report' AND column_name = 'classification'"
        ))
        if result.scalar():
            print("Column 'classification' already exists.")
        else:
            print("Adding column 'classification'...")
            await conn.execute(text("ALTER TABLE bug_report ADD COLUMN classification VARCHAR"))

        # Check if classification_confidence column exists
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'bug_report' AND column_name = 'classification_confidence'"
        ))
        if result.scalar():
            print("Column 'classification_confidence' already exists.")
        else:
            print("Adding column 'classification_confidence'...")
            await conn.execute(text("ALTER TABLE bug_report ADD COLUMN classification_confidence FLOAT"))

    print("Migration complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
