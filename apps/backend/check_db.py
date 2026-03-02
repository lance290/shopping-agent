import asyncio
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from database import engine
from sqlmodel import select
from models import Row

async def main():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.exec(select(Row).order_by(Row.created_at.desc()).limit(5))
        for row in result.all():
            print(f"Row {row.id}: {row.title}")
            print(f"  choice_answers: {row.choice_answers}")
            print(f"  provider_query: {row.provider_query}")
            from routes.rows_search import _extract_filters
            filters = _extract_filters(row, None)
            print(f"  extracted filters: {filters}")

asyncio.run(main())
