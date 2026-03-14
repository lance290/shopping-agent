#!/usr/bin/env python3
"""
Upsert enriched CSV vendor/agent data into the vendor table.

Reads CSVs that have been enriched by cpg_outreach_enrich.py (Resolved_* fields)
and writes high-quality vendor records to the database, including:
  - All Resolved_* contact/description/SEO fields
  - Built profile_text for FTS/embedding
  - Built schema_markup JSON-LD
  - Generated slug
  - Embeddings via OpenRouter
  - Lat/lon via Nominatim (free OSM geocoder)

Usage:
    cd apps/backend
    uv run python scripts/upsert_enriched_csv.py --input-csv PATH [--dry-run] [--skip-embed] [--skip-geo]
"""

import asyncio
import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from database import engine
from models.bids import Vendor
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.FileHandler("upsert_enriched.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# --- Config ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
EMBED_SEM = asyncio.Semaphore(10)
GEO_SEM = asyncio.Semaphore(1)  # Nominatim: 1 req/sec

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA = "BuyAnything-VendorEnrich/1.0 (contact: lance@xcor-cto.com)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sanitize(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def extract_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
        host = parsed.netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return None


def favicon_url(website: Optional[str]) -> Optional[str]:
    domain = extract_domain(website)
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=128" if domain else None


def make_slug(name: str) -> str:
    base = (name or "vendor").lower().strip()
    base = re.sub(r"[^a-z0-9\s-]", "", base)
    base = re.sub(r"[\s_-]+", "-", base).strip("-")
    return base or "vendor"


async def ensure_unique_slug(session: AsyncSession, vendor_id: Optional[int], slug: str) -> str:
    """Return a slug that doesn't collide with any existing vendor (excluding vendor_id if set)."""
    candidate = slug
    suffix = 0
    while True:
        if vendor_id:
            result = await session.exec(select(Vendor).where(Vendor.slug == candidate, Vendor.id != vendor_id))
        else:
            result = await session.exec(select(Vendor).where(Vendor.slug == candidate))
        if not result.first():
            return candidate
        suffix += 1
        candidate = f"{slug}-{suffix}"


def normalize_category(raw: str) -> str:
    """Turn raw category into a slug: 'Diamonds & Jewelry — Nashville' -> 'diamonds_jewelry'."""
    base = raw.split("—")[0].strip() if "—" in raw else raw.strip()
    slug = base.lower().replace("&", "and").replace("/", "_")
    slug = "".join(c if c.isalnum() or c in {" ", "_"} else "" for c in slug)
    return "_".join(slug.split())


def unique_preserve_order(values: List[Optional[str]], limit: int = 12) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        cleaned = sanitize(value)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def parse_personal_emails(value: Optional[str]) -> List[str]:
    cleaned = sanitize(value)
    if not cleaned:
        return []
    stripped = cleaned.strip("{}")
    return unique_preserve_order([part.strip() for part in stripped.split(",")])


def parse_experience(row: Dict[str, str]) -> List[Dict[str, Any]]:
    raw = sanitize(row.get("experience"))
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def summarize_experience(row: Dict[str, str]) -> Dict[str, Any]:
    experiences = parse_experience(row)
    current_items = [item for item in experiences if item.get("is_current") or item.get("status") == "ongoing"]
    ordered_items = current_items or experiences

    titles: List[Optional[str]] = []
    companies: List[Optional[str]] = []
    industries: List[Optional[str]] = []
    locations: List[Optional[str]] = []
    descriptions: List[Optional[str]] = []
    websites: List[Optional[str]] = []
    earliest_start: Optional[str] = None

    for item in ordered_items:
        company = item.get("company") or {}
        titles.append(item.get("title"))
        companies.append(company.get("name"))
        websites.append(company.get("website"))
        industries.append(company.get("industry"))
        for industry in company.get("industries") or []:
            industries.append(industry)
        for location in item.get("location") or []:
            locations.append(location)
        for location in company.get("locations") or []:
            if isinstance(location, dict):
                locations.append(location.get("name"))
                city = sanitize(location.get("city"))
                state = sanitize(location.get("state"))
                if city and state:
                    locations.append(f"{city}, {state}")
                elif city:
                    locations.append(city)
                elif state:
                    locations.append(state)
        descriptions.append(item.get("description"))
        start_date = sanitize(item.get("start_date"))
        if start_date and (earliest_start is None or start_date < earliest_start):
            earliest_start = start_date

    return {
        "current_items": current_items,
        "titles": unique_preserve_order(titles),
        "companies": unique_preserve_order(companies),
        "industries": unique_preserve_order(industries),
        "locations": unique_preserve_order(locations),
        "descriptions": unique_preserve_order(descriptions, limit=6),
        "websites": unique_preserve_order(websites),
        "earliest_start": earliest_start,
        "count": len(experiences),
    }


# ---------------------------------------------------------------------------
# CSV row → Vendor field mapping
# ---------------------------------------------------------------------------

def row_name(row: Dict[str, str]) -> Optional[str]:
    """Extract vendor/agent name from CSV row."""
    first_name = sanitize(row.get("first_name"))
    last_name = sanitize(row.get("last_name"))
    if first_name or last_name:
        return " ".join(part for part in [first_name, last_name] if part)
    for key in ["Agent_or_Team", "Vendor", "Brand", "Company"]:
        val = sanitize(row.get(key))
        if val:
            return val
    return None


def row_category(row: Dict[str, str]) -> str:
    """Extract and normalize category."""
    raw = sanitize(row.get("Category")) or ""
    if not raw and (row.get("first_name") or row.get("last_name")):
        raw = "luxury_real_estate"
    if not raw and row.get("Agent_or_Team"):
        raw = "luxury_real_estate"
    return normalize_category(raw) if raw else "uncategorized"


def row_geo(row: Dict[str, str]) -> Optional[str]:
    """Build geo string from City/State columns."""
    city = sanitize(row.get("City")) or ""
    state = sanitize(row.get("State")) or ""
    parts = [p for p in [city, state] if p]
    if parts:
        return ", ".join(parts)
    summary = summarize_experience(row)
    locations = summary["locations"]
    return locations[0] if locations else None


def row_email(row: Dict[str, str]) -> Optional[str]:
    email = sanitize(row.get("Resolved_Contact_Email")) or sanitize(row.get("work_email"))
    if email:
        return email
    personal_emails = parse_personal_emails(row.get("personal_emails"))
    return personal_emails[0] if personal_emails else None


def row_contact_name(row: Dict[str, str], name: str) -> Optional[str]:
    return sanitize(row.get("Resolved_Contact_Name")) or name


def row_website(row: Dict[str, str]) -> Optional[str]:
    website = sanitize(row.get("Resolved_Website")) or sanitize(row.get("current_company_website"))
    if website:
        return website
    summary = summarize_experience(row)
    return summary["websites"][0] if summary["websites"] else None


def row_tagline(row: Dict[str, str]) -> Optional[str]:
    return sanitize(row.get("Resolved_Tagline")) or sanitize(row.get("headline")) or sanitize(row.get("current_title"))


def row_specialties(row: Dict[str, str]) -> Optional[str]:
    """Build specialties from Resolved_Services or brokerage."""
    services = sanitize(row.get("Resolved_Services"))
    if services:
        return services.replace(" | ", ", ")
    summary = summarize_experience(row)
    specialty_parts = unique_preserve_order(
        [
            sanitize(row.get("current_title")),
            sanitize(row.get("current_company_name")),
            *summary["titles"],
            *summary["industries"],
        ],
        limit=12,
    )
    if specialty_parts:
        return ", ".join(specialty_parts)
    brokerage = sanitize(row.get("Brokerage"))
    return brokerage


def row_description(row: Dict[str, str], name: str, category: str) -> Optional[str]:
    description = sanitize(row.get("Resolved_Description"))
    if description:
        return description

    headline = sanitize(row.get("headline"))
    current_title = sanitize(row.get("current_title"))
    current_company = sanitize(row.get("current_company_name"))
    summary = summarize_experience(row)
    desc_parts: List[str] = []

    if headline and headline != "--":
        desc_parts.append(headline)
    elif current_title and current_company:
        desc_parts.append(f"{current_title} at {current_company}.")
    elif current_title:
        desc_parts.append(f"{current_title}.")
    elif current_company:
        desc_parts.append(f"Works with {current_company}.")

    if summary["locations"]:
        desc_parts.append(f"Locations: {', '.join(summary['locations'][:3])}.")
    if summary["titles"]:
        desc_parts.append(f"Roles: {', '.join(summary['titles'][:5])}.")
    if summary["industries"]:
        desc_parts.append(f"Industries: {', '.join(summary['industries'][:5])}.")
    if summary["descriptions"]:
        desc_parts.append(" ".join(summary["descriptions"][:2]))
    if not desc_parts and category != "uncategorized":
        desc_parts.append(f"{name} provides {category.replace('_', ' ')} services.")

    return " ".join(part.strip() for part in desc_parts if sanitize(part)) or None


def build_profile_text(
    name: str,
    description: Optional[str],
    seo_summary: Optional[str],
    category: str,
    specialties: Optional[str],
    geo: Optional[str],
    tagline: Optional[str],
) -> str:
    parts = [f"{name}."]
    if description:
        parts.append(description)
    if seo_summary and seo_summary != description:
        parts.append(seo_summary)
    if category and category != "uncategorized":
        parts.append(f"Category: {category.replace('_', ' ')}.")
    if specialties:
        parts.append(f"Specialties: {specialties}.")
    if geo:
        parts.append(f"Location: {geo}.")
    if tagline:
        parts.append(f'Tagline: "{tagline}".')
    return " ".join(parts)


def build_seo_content(row: Dict[str, str]) -> Dict[str, Any]:
    experience_summary = summarize_experience(row)
    summary = (
        sanitize(row.get("Resolved_SEO_Summary"))
        or sanitize(row.get("Resolved_Description"))
        or sanitize(row.get("headline"))
    )
    services_raw = sanitize(row.get("Resolved_Services")) or ""
    services_list = [s.strip() for s in services_raw.split("|") if s.strip()] if services_raw else []
    if not services_list:
        services_list = unique_preserve_order(
            [
                sanitize(row.get("current_title")),
                *experience_summary["titles"],
                *experience_summary["industries"],
            ],
            limit=10,
        )
    confidence = sanitize(row.get("Resolved_Confidence")) or "medium"
    return {
        "summary": summary,
        "services_list": services_list,
        "features_matrix": [],
        "pricing_model": None,
        "pros": [],
        "cons": [],
        "experience": {
            "company_names": experience_summary["companies"],
            "titles": experience_summary["titles"],
            "industries": experience_summary["industries"],
            "locations": experience_summary["locations"],
            "descriptions": experience_summary["descriptions"],
            "earliest_start": experience_summary["earliest_start"],
            "experience_count": experience_summary["count"],
            "personal_emails": parse_personal_emails(row.get("personal_emails")),
            "linkedin_url": sanitize(row.get("concat")),
        },
        "validation": {
            "contact_confidence": confidence,
            "description_confidence": "high" if sanitize(row.get("Resolved_Description")) or sanitize(row.get("headline")) else "low",
            "seo_confidence": "high" if summary and services_list else "medium" if summary else "low",
        },
    }


def build_schema_markup(
    name: str,
    website: Optional[str],
    description: Optional[str],
    phone: Optional[str],
    email: Optional[str],
    geo: Optional[str],
    contact_link: Optional[str],
) -> Dict[str, Any]:
    markup: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
    }
    if website:
        markup["url"] = website
    if description:
        markup["description"] = description
    if phone:
        markup["telephone"] = phone
    if email:
        markup["email"] = email
    if geo:
        markup["areaServed"] = geo
    same_as = []
    if contact_link:
        same_as.append(contact_link)
    if same_as:
        markup["sameAs"] = same_as
    return markup


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

async def embed_text(text: str) -> Optional[List[float]]:
    if not OPENROUTER_API_KEY or not text:
        return None
    try:
        async with EMBED_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": EMBEDDING_MODEL,
                        "input": [text[:8000]],
                        "dimensions": EMBEDDING_DIM,
                    },
                )
                resp.raise_for_status()
                return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Nominatim geocoding
# ---------------------------------------------------------------------------

async def geocode(location: str) -> Optional[Dict[str, float]]:
    """Geocode a location string via Nominatim. Returns {"lat": ..., "lon": ...} or None."""
    if not location:
        return None
    try:
        async with GEO_SEM:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    NOMINATIM_URL,
                    params={"q": location, "format": "json", "limit": 1},
                    headers={"User-Agent": NOMINATIM_UA},
                )
                resp.raise_for_status()
                results = resp.json()
            await asyncio.sleep(1.1)  # Respect 1 req/sec rate limit
            if results:
                return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
    except Exception as e:
        logger.warning(f"Geocode failed for '{location}': {e}")
    return None


# ---------------------------------------------------------------------------
# Main upsert logic
# ---------------------------------------------------------------------------

async def upsert_csv(csv_path: Path, dry_run: bool, skip_embed: bool, skip_geo: bool):
    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return {"created": 0, "updated": 0, "embedded": 0, "geocoded": 0, "errors": 1, "total": 0}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]

    # Filter to rows that have been enriched
    enriched_rows = [
        r for r in rows
        if row_name(r) and (
            sanitize(r.get("Resolved_Last_Run_UTC"))
            or sanitize(r.get("work_email"))
            or sanitize(r.get("current_company_name"))
            or sanitize(r.get("experience"))
        )
    ]

    total = len(enriched_rows)
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Upserting {total} enriched rows from {csv_path.name} (total in file: {len(rows)})")

    if total == 0:
        logger.info("No enriched rows found. Nothing to do.")
        return {"created": 0, "updated": 0, "embedded": 0, "geocoded": 0, "errors": 0, "total": 0}

    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    updated = 0
    embedded = 0
    geocoded = 0
    errors = 0

    for i, row in enumerate(enriched_rows, 1):
        try:
            name = row_name(row)
            if not name:
                continue

            category = row_category(row)
            website = row_website(row)
            domain = extract_domain(website)
            email = row_email(row)
            phone = sanitize(row.get("Resolved_Contact_Phone"))
            contact_name = row_contact_name(row, name)
            tagline = row_tagline(row)
            description = row_description(row, name, category)
            seo_summary = sanitize(row.get("Resolved_SEO_Summary"))
            contact_link = sanitize(row.get("Resolved_Contact_Link"))
            specialties = row_specialties(row)
            geo = row_geo(row)
            image = favicon_url(website)

            profile_text = build_profile_text(name, description, seo_summary, category, specialties, geo, tagline)
            seo_content = build_seo_content(row)
            schema_markup = build_schema_markup(name, website, description or seo_summary, phone, email, geo, contact_link)
            slug = make_slug(name)

            if dry_run:
                logger.info(f"  [{i}/{total}] [DRY] {name} | {category} | {geo or '-'} | email={email or '-'}")
                continue

            async with async_session_factory() as session:
                existing = None
                if email:
                    email_stmt = select(Vendor).where(Vendor.email == email)
                    email_result = await session.exec(email_stmt)
                    existing = email_result.first()
                if not existing:
                    stmt = select(Vendor).where(Vendor.name == name, Vendor.category == category)
                    result = await session.exec(stmt)
                    existing = result.first()

                if existing:
                    existing.website = website or existing.website
                    existing.domain = domain or existing.domain
                    existing.email = email or existing.email
                    existing.phone = phone or existing.phone
                    existing.contact_name = contact_name or existing.contact_name
                    existing.tagline = tagline or existing.tagline
                    existing.description = description or existing.description
                    existing.specialties = specialties or existing.specialties
                    existing.store_geo_location = geo or existing.store_geo_location
                    existing.image_url = image or existing.image_url
                    existing.profile_text = profile_text
                    existing.seo_content = seo_content
                    existing.schema_markup = schema_markup
                    existing.slug = await ensure_unique_slug(session, existing.id, slug)
                    existing.updated_at = datetime.utcnow()
                    vendor_id = existing.id
                    updated += 1
                else:
                    vendor = Vendor(
                        name=name,
                        email=email,
                        domain=domain,
                        phone=phone,
                        website=website,
                        category=category,
                        specialties=specialties,
                        description=description,
                        tagline=tagline,
                        contact_name=contact_name,
                        store_geo_location=geo,
                        image_url=image,
                        profile_text=profile_text,
                        seo_content=seo_content,
                        schema_markup=schema_markup,
                        slug=slug,
                    )
                    # Ensure slug uniqueness before insert (no vendor_id yet)
                    vendor.slug = await ensure_unique_slug(session, None, slug)
                    session.add(vendor)
                    await session.flush()
                    vendor_id = vendor.id
                    created += 1

                # Embedding
                if not skip_embed and profile_text:
                    emb = await embed_text(profile_text)
                    if emb:
                        vec_str = "[" + ",".join(str(f) for f in emb) + "]"
                        await session.execute(
                            sa.text(
                                "UPDATE vendor SET embedding = CAST(:vec AS vector), "
                                "embedding_model = :model, embedded_at = NOW() WHERE id = :vid"
                            ),
                            {"vec": vec_str, "model": EMBEDDING_MODEL, "vid": vendor_id},
                        )
                        embedded += 1

                # Geocoding
                if not skip_geo and geo:
                    coords = await geocode(geo)
                    if coords:
                        await session.execute(
                            sa.text(
                                "UPDATE vendor SET latitude = :lat, longitude = :lon WHERE id = :vid"
                            ),
                            {"lat": coords["lat"], "lon": coords["lon"], "vid": vendor_id},
                        )
                        geocoded += 1

                await session.commit()

            if i % 25 == 0:
                logger.info(f"  Progress: [{i}/{total}] created={created} updated={updated} embedded={embedded} geocoded={geocoded} errors={errors}")

        except Exception as e:
            logger.error(f"  Error processing row {i} ({row_name(row)}): {e}")
            errors += 1

    logger.info(
        f"DONE {csv_path.name}: created={created} updated={updated} "
        f"embedded={embedded} geocoded={geocoded} errors={errors}"
    )
    return {
        "created": created,
        "updated": updated,
        "embedded": embedded,
        "geocoded": geocoded,
        "errors": errors,
        "total": total,
    }


def main():
    parser = argparse.ArgumentParser(description="Upsert enriched CSV data into vendor table")
    parser.add_argument("--input-csv", required=True, help="Enriched CSV file to upsert")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--skip-embed", action="store_true", help="Skip embedding generation")
    parser.add_argument("--skip-geo", action="store_true", help="Skip Nominatim geocoding")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY and not args.skip_embed:
        logger.error("OPENROUTER_API_KEY not set — use --skip-embed or set the env var")
        sys.exit(1)

    csv_path = Path(args.input_csv)
    if not csv_path.is_absolute():
        csv_path = (Path.cwd() / csv_path).resolve()

    asyncio.run(upsert_csv(csv_path, args.dry_run, args.skip_embed, args.skip_geo))


if __name__ == "__main__":
    main()
