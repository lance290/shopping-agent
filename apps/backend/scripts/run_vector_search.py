
import asyncio
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load env
sys.path.append(str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")

async def get_embedding(text: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": [text],
            },
        )
        return resp.json()["data"][0]["embedding"]

async def search(query: str, limit: int = 5):
    print(f"\n🔎 Searching for: '{query}'")
    embedding = await get_embedding(query)
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Cosine similarity search using pgvector (<=> is cosine distance, so we want smallest distance)
        stmt = text("""
            SELECT name, category, profile_text, 1 - (embedding <=> :embedding) as similarity
            FROM vendor
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :embedding
            LIMIT :limit
        """)
        
        result = await session.execute(stmt, {"embedding": str(embedding), "limit": limit})
        rows = result.fetchall()
        
        print(f"   Found {len(rows)} results:")
        for row in rows:
            print(f"   - [{row[3]:.4f}] {row[0]} ({row[1]})")
            profile_snippet = (row[2] or "")[:100]
            print(f"     {profile_snippet}...")

async def main():
    queries = [
        "luxury watches in new york",
        "private security for events",
        "rare books in london",
        "yacht charter mediterranean"
    ]
    
    for q in queries:
        await search(q)

if __name__ == "__main__":
    asyncio.run(main())
