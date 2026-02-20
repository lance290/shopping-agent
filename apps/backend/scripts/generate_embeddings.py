"""
Generate vector embeddings for VendorProfile records via OpenRouter.

Uses OpenAI text-embedding-3-small (1536 dimensions) routed through OpenRouter.
Safe to run repeatedly — only embeds profiles where embedding is NULL.

Usage:
    python scripts/generate_embeddings.py              # embed all missing
    python scripts/generate_embeddings.py --force      # re-embed everything
"""
import sys
import os
import asyncio
import httpx
import sqlalchemy as sa
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from models import VendorProfile

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/embeddings"

# Process in batches to avoid rate limits / large payloads
BATCH_SIZE = 20


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Call OpenRouter embeddings API for a batch of texts."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
                "dimensions": EMBEDDING_DIMENSIONS,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # Sort by index to preserve order
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]


async def generate_embeddings(force: bool = False):
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY is not set.")
        sys.exit(1)

    print(f"Model:      {EMBEDDING_MODEL}")
    print(f"Dimensions: {EMBEDDING_DIMENSIONS}")
    print(f"Mode:       {'force (re-embed all)' if force else 'incremental (missing only)'}\n")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch vendors needing embeddings
        query = select(VendorProfile)
        if not force:
            query = query.where(VendorProfile.embedding.is_(None))
        result = await session.exec(query)
        vendors = list(result.all())

        if not vendors:
            print("All vendors already have embeddings. Use --force to re-embed.")
            return

        print(f"Generating embeddings for {len(vendors)} vendors...\n")

        embedded = 0
        errors = 0

        for i in range(0, len(vendors), BATCH_SIZE):
            batch = vendors[i : i + BATCH_SIZE]
            texts = []
            for v in batch:
                text = v.profile_text or f"{v.name} {v.category}"
                texts.append(text)

            try:
                embeddings = await get_embeddings(texts)
                now = datetime.utcnow()
                for v, emb in zip(batch, embeddings):
                    # Use raw SQL to write vector — SQLAlchemy ORM can't cast list→vector
                    # Use CAST() not :: because asyncpg treats :: as param syntax
                    vec_str = "[" + ",".join(str(f) for f in emb) + "]"
                    await session.execute(
                        sa.text(
                            "UPDATE vendor SET embedding = CAST(:vec AS vector), "
                            "embedding_model = :model, embedded_at = :ts "
                            "WHERE id = :vid"
                        ),
                        {"vec": vec_str, "model": EMBEDDING_MODEL, "ts": now, "vid": v.id},
                    )
                    embedded += 1

                await session.commit()
                print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} vendors embedded")

            except Exception as e:
                errors += len(batch)
                print(f"  Batch {i // BATCH_SIZE + 1}: ERROR — {e}")

        print(f"\n✓  Embedding complete: {embedded} embedded, {errors} errors")


if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(generate_embeddings(force=force))
