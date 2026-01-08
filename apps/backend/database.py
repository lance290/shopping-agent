from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import os
import ssl

# Default to a local postgres if not set
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/shopping_agent")

# Configure connection args for production (Railway) to handle SSL correctly
connect_args = {}
if os.getenv("RAILWAY_ENVIRONMENT"):
    # Disable hostname check for Railway internal connections to avoid TargetServerAttributeNotMatched
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

# Async Engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True, connect_args=connect_args)

async def init_db():
    async with engine.begin() as conn:
        # This creates tables if they don't exist
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
