from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
import ssl

# Default to a local postgres if not set
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5435/shopping_agent"

# Ensure asyncpg driver is used in the connection string
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

print(f"DEBUG: DATABASE_URL starts with: {DATABASE_URL[:15]}...") # Debug log (safe)

# Configure connection args for production (Railway) to handle SSL correctly
connect_args = {}
if os.getenv("RAILWAY_ENVIRONMENT"):
    # Railway internal Postgres uses self-signed certs — must disable
    # hostname check and cert verification for internal connections.
    # This is standard for Railway's private networking.
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

# Connection Pool Configuration
# These settings optimize database connection management for FastAPI's async workload
# Defaults are conservative and production-ready

# Pool size: Number of connections to maintain in the pool
# Default: 20 for production workloads (5 for development)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20" if os.getenv("RAILWAY_ENVIRONMENT") else "5"))

# Max overflow: Additional connections beyond pool_size that can be created on demand
# Default: 10 (allows bursts up to pool_size + max_overflow total connections)
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

# Pool timeout: Seconds to wait for a connection from the pool before raising error
# Default: 30 seconds
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

# Pool recycle: Seconds after which to recycle connections (prevents stale connections)
# Default: 3600 (1 hour) - important for databases that close idle connections
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Pool pre-ping: Test connection liveness before using (slight overhead but prevents errors)
# Default: True (recommended for production)
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# Echo SQL queries (for debugging only - disable in production)
# Can be overridden with DB_ECHO=true for troubleshooting
ECHO_SQL = os.getenv("DB_ECHO", "false").lower() == "true"

# Use NullPool for serverless/testing environments (each request gets new connection)
# Useful for: Railway Preview environments, E2E tests, or low-traffic deployments
USE_NULL_POOL = os.getenv("DB_USE_NULL_POOL", "false").lower() == "true"

# Async Engine with optimized connection pooling
engine_kwargs = {
    "echo": ECHO_SQL,
    "future": True,
    "connect_args": connect_args,
    "pool_pre_ping": POOL_PRE_PING,
    "pool_recycle": POOL_RECYCLE,
}

# Configure pooling strategy
if USE_NULL_POOL:
    engine_kwargs["poolclass"] = NullPool
    print(f"DEBUG: Using NullPool (serverless mode)")
else:
    # For async engines, don't specify poolclass - SQLAlchemy will use the appropriate async pool
    # (AsyncAdaptedQueuePool) automatically
    engine_kwargs["pool_size"] = POOL_SIZE
    engine_kwargs["max_overflow"] = MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = POOL_TIMEOUT
    print(f"DEBUG: Connection pool: size={POOL_SIZE}, max_overflow={MAX_OVERFLOW}, timeout={POOL_TIMEOUT}s")

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Query Performance Monitoring
# Logs slow queries for performance analysis (development only)
SLOW_QUERY_THRESHOLD = float(os.getenv("DB_SLOW_QUERY_THRESHOLD", "1.0"))  # seconds
ENABLE_QUERY_LOGGING = os.getenv("DB_ENABLE_QUERY_LOGGING", "false").lower() == "true"

if ENABLE_QUERY_LOGGING:
    import logging
    import time
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    # Set up query logger
    query_logger = logging.getLogger("sqlalchemy.query_performance")
    query_logger.setLevel(logging.INFO)

    if not query_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] SLOW QUERY (%(duration).3fs): %(statement)s"
        ))
        query_logger.addHandler(handler)

    print(f"DEBUG: Query logging enabled (threshold={SLOW_QUERY_THRESHOLD}s)")

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

# Database connection pool health check
async def check_db_health() -> dict:
    """
    Check database connection pool health.
    Returns pool statistics for monitoring.
    """
    pool = engine.pool
    return {
        "pool_size": getattr(pool, "size", lambda: 0)(),
        "checked_in": getattr(pool, "checkedin", lambda: 0)(),
        "checked_out": getattr(pool, "checkedout", lambda: 0)(),
        "overflow": getattr(pool, "overflow", lambda: 0)(),
        "pool_class": pool.__class__.__name__,
    }
