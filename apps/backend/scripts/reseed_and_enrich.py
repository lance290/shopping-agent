#!/usr/bin/env python3
"""
Unified Vendor Re-seed + Enrich + Embed Script

Phase 1: Re-seed missing vendors from vendor-research.md and vendors-export.csv (upsert)
Phase 2: Scrape each vendor's website, LLM-extract structured data, build rich profile_text
Phase 3: Re-embed all vendors that need it

Usage:
    python scripts/reseed_and_enrich.py                    # full run
    python scripts/reseed_and_enrich.py --seed-only        # just re-seed, no enrichment
    python scripts/reseed_and_enrich.py --enrich-only      # skip seeding, just enrich
    python scripts/reseed_and_enrich.py --limit 10         # limit enrichment to N vendors
    python scripts/reseed_and_enrich.py --dry-run          # don't write to DB
"""

import asyncio
import argparse
import csv
import json
import logging
import os
import re
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urlsplit

import aiohttp
from bs4 import BeautifulSoup
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
    format='%(asctime)s %(levelname)-7s %(message)s',
    handlers=[
        logging.FileHandler('reseed_enrich.log'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# --- Config ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
LLM_MODEL = "google/gemini-3-flash-preview"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SCRAPE_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SCRAPE_SEM = asyncio.Semaphore(20)
LLM_SEM = asyncio.Semaphore(10)
EMBED_SEM = asyncio.Semaphore(10)

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent

# ============================================================
# PHASE 1: RE-SEED
# ============================================================

SECTION_CATEGORIES = {
    "roofing": "roofing",
    "luxury renovation": "luxury_renovation",
    "nashville builders": "luxury_renovation",
    "nashville smart home": "smart_home_av",
    "nashville pools": "pools_outdoor_living",
    "national specialty": "national_specialty",
    "yacht charter": "yacht_charter",
    "custom diamonds": "diamonds_and_jewelry",
    "online premium": "diamonds_and_jewelry",
    "luxury villa rentals": "luxury_villa_rentals",
    "premium event hospitality": "event_hospitality",
    "nashville venue": "event_hospitality",
    "national hospitality": "event_hospitality",
    "executive protection": "executive_protection",
    "nashville-serving": "executive_protection",
    "exotic": "exotic_and_classic_automobiles",
    "classic automobiles": "exotic_and_classic_automobiles",
    "national / auctions": "exotic_and_classic_automobiles",
    "concierge": "concierge_medicine",
    "longevity medicine": "concierge_medicine",
    "national longevity": "concierge_medicine",
    "fine art": "fine_art",
    "nashville galleries": "fine_art",
    "national galleries": "fine_art",
    "private aviation": "private_aviation",
}


def resolve_category(heading_stack: list) -> Optional[str]:
    for heading in reversed(heading_stack):
        lower = heading.lower().strip()
        for key, cat in SECTION_CATEGORIES.items():
            if key in lower:
                return cat
    return None


def parse_research_md(path: str) -> list:
    text = Path(path).read_text()
    lines = text.split("\n")
    vendors = []
    heading_stack = []
    current_category = None
    in_table = False
    col_map = {}

    for line in lines:
        stripped = line.strip()
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
        if in_table and stripped.startswith("|") and set(stripped.replace("|", "").strip()) <= {"-", " "}:
            continue
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            row = {}
            for i, cell in enumerate(cells):
                field = col_map.get(i)
                if field and cell:
                    row[field] = cell
            if row.get("company"):
                row["category"] = current_category or "uncategorized"
                vendors.append(row)
            continue
        if in_table and not stripped.startswith("|"):
            in_table = False

    return vendors


def clean_url(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    m = re.search(r"https?://[^\s)]+", raw)
    return m.group(0).rstrip("/") if m else (raw if raw.startswith("http") else None)


def extract_email(raw: str) -> Optional[str]:
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw)
    return m.group(0) if m else None


def extract_phone(raw: str) -> Optional[str]:
    m = re.search(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", raw)
    return m.group(0) if m else None


def extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        d = urlsplit(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return None


def normalize_category(raw: str) -> str:
    base = raw.split("—")[0].strip() if "—" in raw else raw.strip()
    slug = base.lower().replace("&", "and").replace("/", "_")
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    return "_".join(slug.split())


async def reseed(dry_run: bool):
    """Phase 1: Re-seed vendors from research MD and CSV."""
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    updated = 0

    # --- Source 1: vendor-research.md ---
    research_path = SCRIPT_DIR / "vendor-research.md"
    if not research_path.exists():
        research_path = BACKEND_DIR.parent.parent / "docs" / "vendor-research.md"
    if research_path.exists():
        vendors_raw = parse_research_md(str(research_path))
        logger.info(f"[SEED] Parsed {len(vendors_raw)} vendors from vendor-research.md")

        async with async_session_factory() as session:
            for v in vendors_raw:
                company = v["company"]
                category = v["category"]
                website = clean_url(v.get("website"))
                contact_raw = v.get("contact", "")
                email = extract_email(contact_raw) if contact_raw else None
                phone = extract_phone(contact_raw) if contact_raw else None
                notes = v.get("notes")
                domain = extract_domain(website)

                stmt = select(Vendor).where(Vendor.name == company, Vendor.category == category)
                result = await session.exec(stmt)
                existing = result.first()

                if existing:
                    existing.website = website or existing.website
                    existing.email = email or existing.email
                    existing.phone = phone or existing.phone
                    existing.domain = domain or existing.domain
                    existing.description = notes or existing.description
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    if not dry_run:
                        session.add(Vendor(
                            name=company, email=email, domain=domain, phone=phone,
                            website=website, category=category, description=notes,
                            profile_text=f"{company} {category} {notes or ''}".strip(),
                        ))
                    created += 1

            if not dry_run:
                await session.commit()
    else:
        logger.warning("[SEED] vendor-research.md not found")

    # --- Source 2: vendors-export.csv ---
    csv_path = BACKEND_DIR / "data" / "vendors-export.csv"
    if not csv_path.exists():
        csv_path = BACKEND_DIR.parent.parent / "vendors-export.csv"

    if csv_path.exists():
        rows = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Company"):
                    rows.append(row)
        logger.info(f"[SEED] Parsed {len(rows)} vendors from vendors-export.csv")

        async with async_session_factory() as session:
            for row in rows:
                company = row["Company"].strip()
                raw_category = row.get("Category", "").strip()
                category = normalize_category(raw_category)
                website = (row.get("Website") or "").strip() or None
                contact_raw = (row.get("Contact") or "").strip()
                notes = (row.get("Notes") or "").strip() or None
                email = extract_email(contact_raw) if contact_raw else None
                phone = extract_phone(contact_raw) if contact_raw else None
                domain = extract_domain(website) if website else None

                stmt = select(Vendor).where(Vendor.name == company, Vendor.category == category)
                result = await session.exec(stmt)
                existing = result.first()

                if existing:
                    existing.website = website or existing.website
                    existing.email = email or existing.email
                    existing.phone = phone or existing.phone
                    existing.domain = domain or existing.domain
                    existing.description = notes or existing.description
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    if not dry_run:
                        session.add(Vendor(
                            name=company, email=email, domain=domain, phone=phone,
                            website=website, category=category, specialties=raw_category,
                            description=notes,
                            profile_text=f"{company} {raw_category} {notes or ''}".strip(),
                        ))
                    created += 1

            if not dry_run:
                await session.commit()
    else:
        logger.warning("[SEED] vendors-export.csv not found")

    logger.info(f"[SEED] Done: {created} created, {updated} updated" + (" (DRY RUN)" if dry_run else ""))
    return created


# ============================================================
# PHASE 2 + 3: ENRICH + EMBED
# ============================================================

async def fetch_text(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    if not url or url == "#":
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        async with session.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=SCRAPE_TIMEOUT,
            allow_redirects=True, max_redirects=3,
        ) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()
            
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header",
                         "iframe", "svg", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:6000] if text else None
    except Exception:
        return None


async def scrape_vendor_site(website: str) -> str:
    texts = []
    
    # Use a single session for connection pooling
    async with SCRAPE_SEM:
        connector = aiohttp.TCPConnector(ssl=SSL_CTX)
        async with aiohttp.ClientSession(connector=connector) as session:
            # 1. Fetch homepage first
            homepage = await fetch_text(session, website)
            if homepage:
                texts.append(homepage)
            
            # 2. Fetch subpages concurrently
            parsed = urlparse(website if website.startswith("http") else f"https://{website}")
            base = f"{parsed.scheme}://{parsed.netloc}"
            
            tasks = []
            for path in ["/about", "/about-us", "/services", "/contact"]:
                tasks.append(fetch_text(session, base + path))
            
            results = await asyncio.gather(*tasks)
            for res in results:
                if res and len(res) > 200:
                    texts.append(res[:3000])

    combined = "\n\n".join(texts)
    return combined[:10000]


EXTRACT_PROMPT = """You are a data extraction assistant. Given scraped website text for a business called "{name}" (current category: {category}), extract the following structured JSON. Be factual — only include information clearly stated or strongly implied by the text. If something is not available, use null.

Return ONLY valid JSON, no markdown fences:
{{
  "description": "2-3 sentence description of what this business does, their specialty, and value proposition",
  "tagline": "their tagline/slogan if visible, else null",
  "specialties": "comma-separated list of specific services or product specialties",
  "service_areas": "comma-separated list of cities, states, regions, or countries they serve. Include headquarters location if mentioned.",
  "location_hq": "city, state/country of headquarters or primary office",
  "phone": "primary phone number if found, else null",
  "email": "primary contact email if found, else null",
  "contact_name": "name of owner/principal/contact person if found, else null"
}}

Website text:
{text}"""


async def llm_extract(name: str, category: str, text: str) -> Optional[Dict[str, Any]]:
    if not text or len(text) < 50:
        return None
    prompt = EXTRACT_PROMPT.format(name=name, category=category or "Unknown", text=text[:8000])
    try:
        async with LLM_SEM:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 600,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```\w*\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)
                return json.loads(content)
    except Exception as e:
        logger.warning(f"LLM extract failed for {name}: {e}")
        return None


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


def build_profile_text(vendor: Vendor, extracted: Optional[Dict]) -> str:
    parts = []
    parts.append(vendor.name + ".")

    desc = (extracted or {}).get("description") or vendor.description or ""
    if desc and "Real-world professional provider" not in desc:
        parts.append(desc)

    cat = vendor.category
    if cat:
        parts.append(f"Category: {cat}.")

    specs = (extracted or {}).get("specialties") or vendor.specialties
    if specs:
        parts.append(f"Specialties: {specs}.")

    areas = (extracted or {}).get("service_areas")
    if areas:
        parts.append(f"Service areas: {areas}.")

    hq = (extracted or {}).get("location_hq")
    if hq:
        parts.append(f"Headquarters: {hq}.")

    tagline = (extracted or {}).get("tagline") or vendor.tagline
    if tagline:
        parts.append(f'Tagline: "{tagline}".')

    return " ".join(parts)


def needs_enrichment(v: Vendor) -> bool:
    """Return True if this vendor still needs enrichment."""
    has_rich_profile = v.profile_text and len(v.profile_text) > 200
    has_embedding = v.embedding is not None
    return not (has_rich_profile and has_embedding)


async def enrich_and_embed(limit: Optional[int], dry_run: bool):
    """Phase 2+3: Enrich and embed all vendors that need it."""
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        stmt = select(Vendor).where(Vendor.website.isnot(None))
        result = await session.exec(stmt)
        all_vendors = result.all()

    # Filter to only those needing enrichment
    vendors = [v for v in all_vendors if needs_enrichment(v)]
    if limit:
        vendors = vendors[:limit]

    total_with_website = len(all_vendors)
    logger.info(f"[ENRICH] {len(vendors)} vendors need enrichment (out of {total_with_website} with websites)")

    enriched = 0
    embedded = 0
    errors = 0

    for i, vendor in enumerate(vendors, 1):
        try:
            logger.info(f"[{i}/{len(vendors)}] {vendor.name} — {vendor.website}")

            # 1. Scrape
            text = await scrape_vendor_site(vendor.website)
            if not text or len(text) < 100:
                logger.info(f"  Scrape: insufficient text ({len(text) if text else 0} chars)")
                # Still build a basic profile and embed it
                profile = build_profile_text(vendor, None)
                if len(profile) < 50:
                    errors += 1
                    continue
            else:
                # 2. LLM extraction
                extracted = await llm_extract(vendor.name, vendor.category, text)
                profile = build_profile_text(vendor, extracted)

            if dry_run:
                logger.info(f"  [DRY RUN] profile ({len(profile)} chars): {profile[:120]}...")
                enriched += 1
                continue

            # 3. Update DB
            async with async_session_factory() as session:
                db_vendor = (await session.exec(select(Vendor).where(Vendor.id == vendor.id))).one()

                db_vendor.profile_text = profile

                if text and len(text) >= 100:
                    extracted = extracted if 'extracted' in dir() else None
                    if extracted:
                        if extracted.get("description"):
                            if not db_vendor.description or len(db_vendor.description) < 60 or "Real-world professional" in (db_vendor.description or ""):
                                db_vendor.description = extracted["description"]
                        if extracted.get("tagline"):
                            db_vendor.tagline = extracted["tagline"]
                        if extracted.get("specialties"):
                            db_vendor.specialties = extracted["specialties"]
                        if extracted.get("service_areas"):
                            db_vendor.service_areas = extracted["service_areas"]
                        if extracted.get("phone") and not db_vendor.phone:
                            db_vendor.phone = extracted["phone"]
                        if extracted.get("email") and not db_vendor.email:
                            db_vendor.email = extracted["email"]
                        if extracted.get("contact_name") and not db_vendor.contact_name:
                            db_vendor.contact_name = extracted["contact_name"]

                db_vendor.updated_at = datetime.utcnow()

                # 4. Embed
                emb = await embed_text(profile)
                if emb:
                    vec_str = "[" + ",".join(str(f) for f in emb) + "]"
                    await session.execute(
                        sa.text("UPDATE vendor SET embedding = CAST(:vec AS vector), "
                                "embedding_model = :model, embedded_at = NOW() "
                                "WHERE id = :vid"),
                        {"vec": vec_str, "model": EMBEDDING_MODEL, "vid": vendor.id},
                    )
                    embedded += 1

                session.add(db_vendor)
                await session.commit()
                enriched += 1

            if i % 50 == 0:
                logger.info(f"  Progress: {i}/{len(vendors)} | enriched={enriched} embedded={embedded} errors={errors}")

        except Exception as e:
            logger.error(f"  Error processing {vendor.name}: {e}")
            errors += 1

    logger.info(f"[ENRICH] DONE. enriched={enriched} embedded={embedded} errors={errors}")


# ============================================================
# MAIN
# ============================================================

async def run(args):
    if not args.enrich_only:
        await reseed(args.dry_run)

    # Count after seed
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        total = len((await session.exec(select(Vendor))).all())
        with_website = len((await session.exec(select(Vendor).where(Vendor.website.isnot(None)))).all())
    logger.info(f"[STATUS] Total vendors: {total}, with website: {with_website}")

    if not args.seed_only:
        if not OPENROUTER_API_KEY:
            logger.error("OPENROUTER_API_KEY not set — cannot enrich/embed")
            sys.exit(1)
        await enrich_and_embed(args.limit, args.dry_run)

    # Final count
    async with async_session_factory() as session:
        total = len((await session.exec(select(Vendor))).all())
        enriched = sum(1 for v in (await session.exec(select(Vendor))).all()
                       if v.profile_text and len(v.profile_text) > 200)
    logger.info(f"[FINAL] Total vendors: {total}, enriched: {enriched} ({enriched/total*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description="Re-seed + enrich + embed vendors")
    parser.add_argument("--limit", type=int, help="Limit enrichment to N vendors")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--seed-only", action="store_true", help="Only re-seed, skip enrichment")
    parser.add_argument("--enrich-only", action="store_true", help="Skip seeding, only enrich")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
