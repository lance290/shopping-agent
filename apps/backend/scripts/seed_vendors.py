"""
Seed script to populate the vendor table from vendors-export.csv.

Safe to run repeatedly — upserts by (name, category).
Never deletes existing records; only creates or updates.

Usage:
    cd apps/backend && uv run python scripts/seed_vendors.py
"""
import csv
import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from sqlmodel import select

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from models.bids import Vendor

# Look for CSV in data/ dir first (Docker), then repo root (local dev)
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
CSV_PATH = _BACKEND_DIR / "data" / "vendors-export.csv"
if not CSV_PATH.exists():
    CSV_PATH = _BACKEND_DIR.parent.parent / "vendors-export.csv"


def _normalize_category(raw: str) -> str:
    """Turn CSV category into a slug: 'Diamonds & Jewelry — Nashville' -> 'diamonds_jewelry'."""
    # Strip location suffix after em-dash
    base = raw.split("—")[0].strip() if "—" in raw else raw.strip()
    slug = base.lower().replace("&", "and").replace("/", "_")
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    return "_".join(slug.split())


def _extract_domain(url: str) -> str | None:
    if not url:
        return None
    try:
        d = urlsplit(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return None


def _extract_email(contact: str) -> str | None:
    if not contact:
        return None
    if "@" in contact:
        return contact.strip()
    return None


def _extract_phone(contact: str) -> str | None:
    if not contact:
        return None
    # If it looks like a phone number (starts with digit or paren)
    stripped = contact.strip()
    if stripped and stripped[0] in "0123456789(+":
        return stripped
    return None


def _favicon_url(website: str) -> str | None:
    domain = _extract_domain(website)
    if domain:
        return f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    return None


async def seed_vendors():
    if not CSV_PATH.exists():
        print(f"❌  CSV not found: {CSV_PATH}")
        sys.exit(1)

    print(f"Reading {CSV_PATH} ...")
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Company"):
                rows.append(row)
    print(f"  Found {len(rows)} vendor rows")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    updated = 0
    errors = 0

    async with async_session() as session:
        for row in rows:
            try:
                company = row["Company"].strip()
                raw_category = row.get("Category", "").strip()
                category = _normalize_category(raw_category)
                website = (row.get("Website") or "").strip() or None
                contact_raw = (row.get("Contact") or "").strip()
                notes = (row.get("Notes") or "").strip() or None
                email = _extract_email(contact_raw)
                phone = _extract_phone(contact_raw)
                domain = _extract_domain(website) if website else None
                image_url = _favicon_url(website)

                # Build searchable profile_text
                parts = [company, raw_category, category.replace("_", " "), notes or ""]
                profile_text = " ".join(p for p in parts if p).strip()

                # Upsert: match by name + category
                stmt = select(Vendor).where(Vendor.name == company, Vendor.category == category)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.website = website or existing.website
                    existing.email = email or existing.email
                    existing.phone = phone or existing.phone
                    existing.domain = domain or existing.domain
                    existing.description = notes or existing.description
                    existing.image_url = image_url or existing.image_url
                    existing.profile_text = profile_text
                    existing.specialties = raw_category
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    session.add(Vendor(
                        name=company,
                        email=email,
                        domain=domain,
                        phone=phone,
                        website=website,
                        category=category,
                        specialties=raw_category,
                        description=notes,
                        image_url=image_url,
                        profile_text=profile_text,
                    ))
                    created += 1
            except Exception as e:
                print(f"  ⚠️  Error: {row.get('Company')}: {e}")
                errors += 1

        await session.commit()

    print(f"\n✓  Vendor seed complete: {created} created, {updated} updated, {errors} errors")


if __name__ == "__main__":
    asyncio.run(seed_vendors())
