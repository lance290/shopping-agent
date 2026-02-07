"""
Export seller/vendor data from the database to a JSON file for backup.

Usage:
    python scripts/backup_vendors.py                     # writes to backups/sellers_YYYY-MM-DD.json
    python scripts/backup_vendors.py --out my_backup.json # writes to custom path

Safe to run at any time — read-only, never modifies the database.
"""
import sys
import os
import json
import asyncio
from datetime import datetime

from sqlmodel import select

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Seller


async def backup_vendors(out_path: str):
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        result = await session.execute(select(Seller))
        sellers = result.scalars().all()

        data = []
        for s in sellers:
            data.append({
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "domain": s.domain,
                "is_verified": s.is_verified,
                "image_url": s.image_url,
                "category": s.category,
                "contact_name": s.contact_name,
                "phone": s.phone,
            })

    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    with open(out_path, "w") as f:
        json.dump({
            "exported_at": datetime.utcnow().isoformat(),
            "count": len(data),
            "sellers": data,
        }, f, indent=2)

    print(f"✓  Exported {len(data)} sellers to {out_path}")


if __name__ == "__main__":
    # Default output path
    out = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--out" and i + 1 < len(args):
            out = args[i + 1]

    if not out:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        out = f"backups/sellers_{date_str}.json"

    asyncio.run(backup_vendors(out))
