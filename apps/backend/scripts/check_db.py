"""Quick DB connectivity check. Exits 0 if reachable, 1 if not."""
import asyncio
import sys

async def check():
    from database import engine
    async with engine.connect() as conn:
        from sqlalchemy import text
        await conn.execute(text("SELECT 1"))

try:
    asyncio.run(asyncio.wait_for(check(), timeout=5))
    sys.exit(0)
except Exception as e:
    print(f"DB check failed: {type(e).__name__}: {str(e)}", file=sys.stderr)
    sys.exit(1)
