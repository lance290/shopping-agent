import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import models/database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DATABASE_URL
from models import BugReport

async def verify_models():
    print(f"Verifying models at {DATABASE_URL}")
    
    # Configure connection args for production (Railway) if needed
    connect_args = {}
    if os.getenv("RAILWAY_ENVIRONMENT"):
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    engine = create_async_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create a test bug report with new fields
        bug = BugReport(
            notes="Verification Test Bug",
            classification="bug",
            classification_confidence=0.95,
            status="captured"
        )
        session.add(bug)
        await session.commit()
        await session.refresh(bug)
        
        print(f"Created bug report {bug.id}")
        
        # Read it back
        stmt = select(BugReport).where(BugReport.id == bug.id)
        result = await session.exec(stmt)
        fetched_bug = result.first()
        
        if fetched_bug:
            print(f"Fetched bug: {fetched_bug.notes}")
            print(f"Classification: {fetched_bug.classification}")
            print(f"Confidence: {fetched_bug.classification_confidence}")
            
            if fetched_bug.classification == "bug" and fetched_bug.classification_confidence == 0.95:
                print("✅ Verification SUCCESS: Fields are persisted correctly.")
            else:
                print("❌ Verification FAILED: Fields mismatch.")
        else:
            print("❌ Verification FAILED: Could not fetch bug.")
            
        # Cleanup
        await session.delete(bug)
        await session.commit()
        print("Test data cleaned up.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_models())
