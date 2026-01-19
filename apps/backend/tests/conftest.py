import pytest
import sys
import os
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path to allow importing models and main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, init_db
from main import app, get_session

@pytest_asyncio.fixture(name="session", scope="function")
async def session_fixture():
    # Use NullPool for tests to avoid asyncpg InterfaceError: cannot perform operation: another operation is in progress
    # This ensures each test gets a fresh connection that is closed at the end
    # Pass the URL object directly to avoid password masking in string representation
    
    test_engine = create_async_engine(
        engine.url, 
        echo=False, 
        future=True, 
        poolclass=NullPool
    )
    
    # Re-init DB on the test engine to ensure schema
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    
    await test_engine.dispose()

@pytest_asyncio.fixture(name="client")
async def client_fixture(session: AsyncSession):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
