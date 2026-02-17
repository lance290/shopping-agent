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
LLM_MODEL = "google/gemini-2.0-flash-001"
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

# ... (rest of phase 1 is fine)

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
