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
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

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

