"""
Seed script to populate VendorProfile directory from the in-memory vendor registry.

Safe to run repeatedly — uses upsert logic (match by email, then company+category).
Never deletes existing records; only creates or updates.
"""
import sys
import os
import asyncio
from datetime import datetime
from sqlmodel import select

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from models import VendorProfile
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
                    vendor_email = getattr(v, "email", None)
                    vendor_company = getattr(v, "company", None)
                    if not vendor_company:
                        raise ValueError("Missing vendor company")

                    existing = None
                    if vendor_email:
                        query = select(VendorProfile).where(
                            VendorProfile.contact_email == vendor_email
                        )
                        result = await session.execute(query)
                        existing = result.scalar_one_or_none()

                    if not existing:
                        query = select(VendorProfile).where(
                            VendorProfile.company == vendor_company,
                            VendorProfile.category == category,
                        )
                        result = await session.execute(query)
                        existing = result.scalar_one_or_none()

                    website = getattr(v, "website", None)
                    phone = getattr(v, "phone", None)
                    contact_name = getattr(v, "name", None)

                    profile_text_parts = [
                        vendor_company,
                        contact_name or "",
                        vendor_email or "",
                        category,
                        phone or "",
                        website or "",
                        getattr(v, "provider_type", None) or "",
                        getattr(v, "fleet", None) or "",
                        getattr(v, "jet_sizes", None) or "",
                        getattr(v, "wifi", None) or "",
                        getattr(v, "starlink", None) or "",
                        getattr(v, "pricing_info", None) or "",
                        getattr(v, "availability", None) or "",
                        getattr(v, "safety_certs", None) or "",
                        getattr(v, "notes", None) or "",
                    ]
                    profile_text = " ".join(p for p in profile_text_parts if p).strip() or None

                    if existing:
                        existing.category = category
                        existing.company = vendor_company
                        existing.website = website
                        existing.contact_email = vendor_email
                        existing.contact_phone = phone
                        existing.specialties = getattr(v, "provider_type", None)
                        existing.description = getattr(v, "notes", None)
                        existing.image_url = getattr(v, "image_url", None)
                        existing.profile_text = profile_text
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        session.add(
                            VendorProfile(
                                category=category,
                                company=vendor_company,
                                website=website,
                                contact_email=vendor_email,
                                contact_phone=phone,
                                specialties=getattr(v, "provider_type", None),
                                description=getattr(v, "notes", None),
                                image_url=getattr(v, "image_url", None),
                                profile_text=profile_text,
                            )
                        )
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
