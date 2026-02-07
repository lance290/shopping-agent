"""
Seed script to populate the database with early-adopter vendors from vendors.py.

Safe to run repeatedly — uses upsert logic (match by email, update all fields).
Never deletes existing sellers; only creates or updates.
"""
import sys
import os
import asyncio
from sqlmodel import select

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Seller
from services.vendors import VENDORS


async def seed_vendors():
    print("Seeding early-adopter vendors...")

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    created = 0
    updated = 0
    errors = 0

    async with async_session() as session:
        for category, vendors in VENDORS.items():
            print(f"  Category: {category} ({len(vendors)} vendors)")
            for v in vendors:
                try:
                    # Match by email first (most reliable), then by company name
                    query = select(Seller).where(Seller.email == v.email)
                    result = await session.execute(query)
                    existing = result.scalar_one_or_none()

                    if not existing:
                        # Try matching by company name as fallback
                        query = select(Seller).where(Seller.name == v.company)
                        result = await session.execute(query)
                        existing = result.scalar_one_or_none()

                    # Extract domain from website or email
                    domain = None
                    if v.website:
                        domain = v.website.replace("https://", "").replace("http://", "").split("/")[0]
                    elif "@" in v.email:
                        domain = v.email.split("@")[1]

                    if existing:
                        # Update all fields — always bring DB in sync with vendors.py
                        existing.name = v.company
                        existing.contact_name = v.name
                        existing.email = v.email
                        existing.image_url = v.image_url
                        existing.category = category
                        existing.phone = v.phone
                        existing.domain = domain
                        existing.is_verified = True
                        updated += 1
                    else:
                        new_seller = Seller(
                            name=v.company,
                            contact_name=v.name,
                            email=v.email,
                            image_url=v.image_url,
                            category=category,
                            phone=v.phone,
                            is_verified=True,
                            domain=domain,
                        )
                        session.add(new_seller)
                        created += 1
                except Exception as e:
                    print(f"    ⚠️  Error seeding {v.company}: {e}")
                    errors += 1

        await session.commit()

    print(f"\n✓  Vendor seed complete: {created} created, {updated} updated, {errors} errors")
    if errors:
        print(f"   ⚠️  {errors} vendor(s) failed — check logs above.")


if __name__ == "__main__":
    asyncio.run(seed_vendors())
