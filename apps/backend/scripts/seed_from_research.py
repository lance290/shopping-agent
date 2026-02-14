"""
Import vendors from docs/vendor-research.md into VendorProfile.

Parses the markdown tables, maps sections → category slugs, and upserts
into the database. Safe to run repeatedly (matches on company + category).
"""
import sys
import os
import re
import asyncio
from datetime import datetime
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from models import VendorProfile

# ── Section heading → category slug mapping ──────────────────────────────────
SECTION_CATEGORIES = {
    "roofing": "roofing",
    "luxury renovation": "luxury_renovation",
    "nashville builders": "luxury_renovation",
    "nashville smart home": "smart_home_av",
    "nashville pools": "pools_outdoor",
    "national specialty": "luxury_renovation",
    "yacht charter": "yacht_charter",
    "custom diamonds": "diamonds_jewelry",
    "online premium": "diamonds_jewelry",
    "luxury villa rentals": "villa_rentals",
    "premium event hospitality": "event_hospitality",
    "nashville venue": "event_hospitality",
    "national hospitality": "event_hospitality",
    "executive protection": "executive_protection",
    "nashville-serving": "executive_protection",
    "exotic": "exotic_automobiles",
    "classic automobiles": "exotic_automobiles",
    "national / auctions": "exotic_automobiles",
    "concierge": "concierge_medicine",
    "longevity medicine": "concierge_medicine",
    "national longevity": "concierge_medicine",
    "fine art": "fine_art",
    "nashville galleries": "fine_art",
    "national galleries": "fine_art",
}


def resolve_category(heading_stack: list[str]) -> str | None:
    """Walk from most-specific heading up to find a category slug.

    Checks the most-specific (deepest) heading first, then walks up
    to parent headings so generic sub-headings like 'Nashville local'
    or 'National' inherit from their parent section.
    """
    for heading in reversed(heading_stack):
        lower = heading.lower().strip()
        for key, cat in SECTION_CATEGORIES.items():
            if key in lower:
                return cat
    return None


def parse_research_md(path: str) -> list[dict]:
    """Parse markdown tables into a list of vendor dicts."""
    text = Path(path).read_text()
    lines = text.split("\n")

    vendors: list[dict] = []
    heading_stack: list[str] = []  # tracks H2 / H3 hierarchy
    current_category: str | None = None
    in_table = False
    col_map: dict[int, str] = {}

    for line in lines:
        stripped = line.strip()

        # Track headings
        if stripped.startswith("## ") and not stripped.startswith("### "):
            heading_stack = [stripped.lstrip("# ").strip()]
            current_category = resolve_category(heading_stack)
            in_table = False
            continue
        if stripped.startswith("### "):
            if len(heading_stack) >= 1:
                heading_stack = [heading_stack[0], stripped.lstrip("# ").strip()]
            else:
                heading_stack = [stripped.lstrip("# ").strip()]
            current_category = resolve_category(heading_stack) or current_category
            in_table = False
            continue

        # Detect table header row
        if stripped.startswith("|") and not in_table:
            cols = [c.strip().lower() for c in stripped.split("|")[1:-1]]
            col_map = {}
            for i, c in enumerate(cols):
                if "company" in c or "venue" in c:
                    col_map[i] = "company"
                elif "website" in c:
                    col_map[i] = "website"
                elif "contact" in c:
                    col_map[i] = "contact"
                elif "note" in c:
                    col_map[i] = "notes"
            in_table = True
            continue

        # Skip separator row
        if in_table and stripped.startswith("|") and set(stripped.replace("|", "").strip()) <= {"-", " "}:
            continue

        # Parse data row
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            row: dict = {}
            for i, cell in enumerate(cells):
                field = col_map.get(i)
                if field and cell:
                    row[field] = cell
            if row.get("company"):
                row["category"] = current_category or "uncategorized"
                vendors.append(row)
            continue

        # Non-table line → end table
        if in_table and not stripped.startswith("|"):
            in_table = False

    return vendors


def clean_contact(raw: str) -> tuple[str | None, str | None]:
    """Extract email and phone from a contact cell."""
    email = None
    phone = None
    # Email
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw)
    if m:
        email = m.group(0)
    # Phone
    m = re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", raw)
    if m:
        phone = m.group(0)
    # URL as contact (skip — it's not an email or phone)
    return email, phone


def clean_url(raw: str | None) -> str | None:
    """Strip markdown links and return plain URL."""
    if not raw:
        return None
    m = re.search(r"https?://[^\s)]+", raw)
    return m.group(0).rstrip("/") if m else raw if raw.startswith("http") else None


async def seed_from_research():
    # Accept path as CLI argument, or walk up to repo root
    if len(sys.argv) > 1:
        research_path = sys.argv[1]
    else:
        # Try: same dir as this script, repo root, /app (Railway container)
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor-research.md"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "docs", "vendor-research.md"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "vendor-research.md"),
            "/app/scripts/vendor-research.md",
            "/app/docs/vendor-research.md",
        ]
        research_path = next((p for p in candidates if os.path.exists(p)), None)
    if not research_path or not os.path.exists(research_path):
        print(f"ERROR: Research file not found. Tried: {candidates if 'candidates' in dir() else research_path}")
        print("Usage: python seed_from_research.py [path/to/vendor-research.md]")
        sys.exit(1)

    vendors_raw = parse_research_md(research_path)
    print(f"Parsed {len(vendors_raw)} vendors from research doc\n")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    updated = 0
    errors = 0
    categories_seen: dict[str, int] = {}

    async with async_session() as session:
        for v in vendors_raw:
            try:
                company = v["company"]
                category = v["category"]
                website = clean_url(v.get("website"))
                contact_raw = v.get("contact", "")
                email, phone = clean_contact(contact_raw)
                notes = v.get("notes")

                categories_seen[category] = categories_seen.get(category, 0) + 1

                # Upsert: match on company + category
                query = select(VendorProfile).where(
                    VendorProfile.company == company,
                    VendorProfile.category == category,
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()

                # Build profile text for embedding
                profile_parts = [company, category, website or "", email or "", phone or "", notes or ""]
                profile_text = " ".join(p for p in profile_parts if p).strip() or None

                if existing:
                    existing.website = website or existing.website
                    existing.contact_email = email or existing.contact_email
                    existing.contact_phone = phone or existing.contact_phone
                    existing.description = notes or existing.description
                    existing.profile_text = profile_text
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    session.add(VendorProfile(
                        category=category,
                        company=company,
                        website=website,
                        contact_email=email,
                        contact_phone=phone,
                        description=notes,
                        profile_text=profile_text,
                    ))
                    created += 1

            except Exception as e:
                company_name = v.get("company", "unknown")
                print(f"  ⚠️  Error: {company_name}: {e}")
                errors += 1

        await session.commit()

    print("Category breakdown:")
    for cat, count in sorted(categories_seen.items()):
        print(f"  {cat}: {count}")
    print(f"\n✓  Import complete: {created} created, {updated} updated, {errors} errors")


if __name__ == "__main__":
    asyncio.run(seed_from_research())
