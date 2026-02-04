"""
Seed script to populate the database with mock vendors from wattdata_mock.py.
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
from services.wattdata_mock import MOCK_VENDORS

async def seed_vendors():
    print("Seeding vendors...")
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        count = 0
        # Iterate over all categories in MOCK_VENDORS
        for category, vendors in MOCK_VENDORS.items():
            print(f"Processing category: {category}")
            for v in vendors:
                # Check if seller exists by email or company name
                query = select(Seller).where(
                    (Seller.email == v.email) | (Seller.name == v.company)
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"Updating vendor: {v.company}")
                    existing.name = v.company
                    existing.contact_name = v.name
                    existing.email = v.email
                    existing.image_url = v.image_url
                    existing.category = category
                    existing.phone = v.phone
                    existing.is_verified = True
                else:
                    print(f"Creating vendor: {v.company}")
                    new_seller = Seller(
                        name=v.company,
                        contact_name=v.name,
                        email=v.email,
                        image_url=v.image_url,
                        category=category,
                        phone=v.phone,
                        is_verified=True,
                        domain=v.email.split('@')[1] if '@' in v.email else None
                    )
                    session.add(new_seller)
                count += 1
        
        await session.commit()
        print(f"Successfully seeded/updated {count} vendors.")

if __name__ == "__main__":
    asyncio.run(seed_vendors())
